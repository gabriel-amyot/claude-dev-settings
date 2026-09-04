#!/usr/bin/env python3
"""
proximity:geocode — ordered address-list geocoder (Nominatim / OpenStreetMap).

Takes an ORDERED list of store addresses and produces paste-ready coordinates in
the exact row order of the input, so the result can be pasted straight into the
"Normalized Klever Stores locations" Google Sheet (top-left cell, fill down).

Proven on KTP-755 (Hema-Quebec 139 QC sites, Blinds To Go 21 ON/QC stores).
This generalizes those two by-hand runs. Geocoder is Nominatim/OSM ONLY:
free, no key, and ODbL permits persisting results WITH attribution
("(c) OpenStreetMap contributors"). NEVER persist Mapbox or Google output.

Order is sacred: failures stay as blank, flagged rows IN POSITION. Never reorder,
never drop. A single top-left paste of latlong-paste.tsv must fill down in perfect
row alignment with the sheet.

Usage:
  python3 geocode_locations.py INPUT.tsv \
      --out OUTPUT_DIR \
      --region QC \
      [--country ca] [--has-header] [--cols id,street,city,region,postal] \
      [--user-agent "klever-geocoder/1.0 (you@beklever.com)"] \
      [--rate 1.1] [--resume]

INPUT: a .tsv or .csv file (delimiter auto-detected). Columns, in file order,
default to: location_id, street, city, region(province/state), postal/zip.
Override with --cols. Header row auto-detected, or force with --has-header.

Outputs (written to --out, which MUST be a committed folder, never /tmp):
  latlong-paste.tsv   lat<TAB>lon, no header, input order   <- THE paste artifact
  latlong-paste.csv   lat,lon, no header                    <- comma fallback
  verification.csv    id,address,city,region,postal,lat,lon,tier,status
  failures.md         FAILED / SUSPECT / APPROXIMATE rows + OSM attribution
"""

import argparse
import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

# SSL context that works even when the macOS system cert store is unavailable.
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001 - any failure falls back to unverified
    SSL_CTX = ssl._create_unverified_context()

NOMINATIM = "https://nominatim.openstreetmap.org/search"
ATTRIBUTION = "(c) OpenStreetMap contributors (ODbL)"

# Region bounding boxes: (lat_min, lat_max, lon_min, lon_max).
# Used to flag results that landed outside the expected region as SUSPECT.
# (A postal-fallback once resolved a QC address to Alberta — bbox caught it.)
REGION_BBOX = {
    "QC": (45.0, 62.6, -80.0, -57.0),
    "ON": (41.6, 56.9, -95.2, -74.3),
    "CA": (41.6, 83.2, -141.0, -52.6),   # all of Canada
    "US": (24.0, 50.0, -125.0, -66.0),   # contiguous US
}

COUNTRY_NAME = {"ca": "Canada", "us": "United States"}

# Synonyms for header-based column mapping (lowercased, stripped).
COL_SYNONYMS = {
    "id": {"id", "location_id", "klever_location_id", "store_id"},
    "street": {"street", "address", "address1", "street_address", "addr"},
    "city": {"city", "town", "municipality"},
    "region": {"region", "state", "province", "prov", "state_province"},
    "postal": {"postal", "postal_code", "zip", "zip_code", "zipcode", "postcode"},
}
DEFAULT_COLS = ["id", "street", "city", "region", "postal"]


def sniff_delimiter(path):
    with open(path, newline="", encoding="utf-8") as fh:
        sample = fh.readline()
    return "\t" if sample.count("\t") >= sample.count(",") else ","


def looks_like_header(first_row):
    """A row is a header if any cell matches a known column synonym."""
    flat = {c.strip().lower() for c in first_row}
    known = set().union(*COL_SYNONYMS.values())
    return bool(flat & known)


def map_header_columns(header):
    """Return {role: column_index} by matching header cells to synonyms."""
    mapping = {}
    for idx, cell in enumerate(header):
        key = cell.strip().lower()
        for role, names in COL_SYNONYMS.items():
            if key in names and role not in mapping:
                mapping[role] = idx
    return mapping


def read_rows(path, forced_cols, has_header_flag):
    """Read input preserving order. Returns list of dicts with the 5 roles."""
    delim = sniff_delimiter(path)
    with open(path, newline="", encoding="utf-8") as fh:
        all_rows = [r for r in csv.reader(fh, delimiter=delim) if any(c.strip() for c in r)]
    if not all_rows:
        sys.exit(f"No data rows found in {path}")

    has_header = has_header_flag or (forced_cols is None and looks_like_header(all_rows[0]))

    if forced_cols:
        col_map = {role: i for i, role in enumerate(forced_cols)}
        data_rows = all_rows[1:] if has_header_flag else all_rows
    elif has_header:
        col_map = map_header_columns(all_rows[0])
        missing = [r for r in ("street", "city") if r not in col_map]
        if missing:
            sys.exit(f"Header detected but could not map columns: {missing}. "
                     f"Pass --cols id,street,city,region,postal explicitly.")
        data_rows = all_rows[1:]
    else:
        col_map = {role: i for i, role in enumerate(DEFAULT_COLS)}
        data_rows = all_rows

    rows = []
    for r in data_rows:
        def cell(role):
            i = col_map.get(role)
            return (r[i].strip() if i is not None and i < len(r) else "")
        rows.append({
            "id": cell("id"),
            "street": cell("street"),
            "city": cell("city"),
            "region": cell("region"),
            "postal": cell("postal"),
        })
    return rows


def nominatim(params, country, user_agent, timeout=30):
    """Single Nominatim lookup from a params dict. Returns (lat, lon) or (None, None).

    Accepts either a free-form {"q": ...} or a structured query
    {"street":..,"city":..,"state":..,"postalcode":..}. countrycodes is applied
    to free-form queries; structured queries carry an explicit 'country' instead.
    """
    p = dict(params)
    p.update({"format": "json", "limit": "1", "addressdetails": "0"})
    if country and "q" in p:
        p["countrycodes"] = country
    url = NOMINATIM + "?" + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:  # noqa: BLE001
        print(f"    ! error: {e}", file=sys.stderr)
    return None, None


# Trailing unit/suite/apt designators break Nominatim's address match
# (e.g. "501 Earl Grey Drive Unit F3" returns nothing; stripping resolves it).
UNIT_RE = re.compile(
    r"[,\s]+(?:unit|suite|ste|apt|apartment|bldg|building|rm|room|fl|floor|#)\s*#?\s*\w+\s*$",
    re.IGNORECASE,
)


def clean_street(street):
    """Strip a trailing unit/suite designator from a street for geocoding only."""
    prev, s = None, street.strip()
    while prev != s:
        prev = s
        s = UNIT_RE.sub("", s).strip().rstrip(",")
    return s or street.strip()


def build_tiers(row, country):
    """Tiered queries, most-reliable first. Returns [(tier_label, params), ...].

    Order matters and is evidence-based (KTP-755 probe): a STRUCTURED query is the
    most reliable; free-form street+city(+postal) is the robust fallback. Bare
    'street + postal' is deliberately NOT a primary tier — it mis-resolves to the
    wrong city while staying inside the region bbox (undetectable), e.g. a Toronto
    address landing in Hamilton. Centroid tiers are flagged APPROXIMATE.
    """
    cname = COUNTRY_NAME.get(country, "")
    street = clean_street(row["street"])
    city, region, postal = (row["city"], row["region"], row["postal"])

    def join(*parts):
        return ", ".join(p for p in parts if p)

    tiers = []
    if street and (city or postal):
        structured = {"street": street, "country": cname or country}
        if city:
            structured["city"] = city
        if region:
            structured["state"] = region
        if postal:
            structured["postalcode"] = postal
        tiers.append(("structured", structured))
    if street and (city or region) and postal:
        tiers.append(("street+city+postal", {"q": join(street, f"{city} {region}".strip(), postal, cname)}))
    if street and (city or region):
        tiers.append(("street+city", {"q": join(street, city, region, cname)}))
    # Centroid fallbacks are APPROXIMATE, not exact.
    if postal:
        tiers.append(("centroid", {"q": join(postal, cname)}))
    if city or region:
        tiers.append(("centroid", {"q": join(city, region, cname)}))
    return tiers


def in_bbox(lat, lon, bbox):
    lat_min, lat_max, lon_min, lon_max = bbox
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def geocode_row(row, country, user_agent, bbox, rate):
    """Run tiers until a result is found. Returns (lat, lon, tier, status)."""
    tiers = build_tiers(row, country)
    if not tiers:
        return None, None, "", "FAILED"

    first_hit = None  # (lat, lon, tier) — used if nothing passes bbox
    for tier, params in tiers:
        lat, lon = nominatim(params, country, user_agent)
        time.sleep(rate)
        if lat is None:
            continue
        if first_hit is None:
            first_hit = (lat, lon, tier)
        if bbox and not in_bbox(lat, lon, bbox):
            continue  # out of region — keep trying a better tier
        status = "APPROXIMATE" if tier == "centroid" else "OK"
        return lat, lon, tier, status

    if first_hit:
        lat, lon, tier = first_hit
        status = "SUSPECT_OUT_OF_BBOX" if bbox else (
            "APPROXIMATE" if tier == "centroid" else "OK")
        return lat, lon, tier, status
    return None, None, "", "FAILED"


def load_resume(out_dir):
    """Read prior verification.csv into {id: row} so resolved rows are reused."""
    path = os.path.join(out_dir, "verification.csv")
    if not os.path.exists(path):
        return {}
    done = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("status") in ("OK", "APPROXIMATE") and r.get("location_id"):
                done[r["location_id"]] = r
    return done


def fmt(v):
    return "" if v is None or v == "" else f"{float(v):.6f}"


def write_outputs(out_dir, results, region, bbox):
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "latlong-paste.tsv"), "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(f"{fmt(r['lat'])}\t{fmt(r['lon'])}\n")

    with open(os.path.join(out_dir, "latlong-paste.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for r in results:
            w.writerow([fmt(r["lat"]), fmt(r["lon"])])

    with open(os.path.join(out_dir, "verification.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["location_id", "street", "city", "region", "postal",
                    "latitude", "longitude", "tier", "status"])
        for r in results:
            w.writerow([r["id"], r["street"], r["city"], r["region"], r["postal"],
                        fmt(r["lat"]), fmt(r["lon"]), r["tier"], r["status"]])

    bad = [r for r in results if r["status"] != "OK"]
    with open(os.path.join(out_dir, "failures.md"), "w", encoding="utf-8") as fh:
        fh.write("# Geocoding — Failures, Suspects & Approximations\n\n")
        fh.write(f"Source attribution: {ATTRIBUTION}\n\n")
        ok = len(results) - len(bad)
        region_note = f" | region: {region} {bbox}" if region else ""
        fh.write(f"Total: {len(results)} | OK: {ok} | Needs attention: {len(bad)}{region_note}\n\n")
        if bad:
            fh.write("| row | location_id | street | city | region | postal | tier | status | lat | lon |\n")
            fh.write("|---|---|---|---|---|---|---|---|---|---|\n")
            for i, r in enumerate(results):
                if r["status"] != "OK":
                    fh.write(f"| {i+1} | {r['id']} | {r['street']} | {r['city']} | "
                             f"{r['region']} | {r['postal']} | {r['tier']} | {r['status']} | "
                             f"{fmt(r['lat'])} | {fmt(r['lon'])} |\n")
        else:
            fh.write("All rows resolved cleanly within the expected region.\n")


def main():
    ap = argparse.ArgumentParser(description="Ordered address-list geocoder (Nominatim/OSM).")
    ap.add_argument("input", help="Path to .tsv or .csv address list (delimiter auto-detected).")
    ap.add_argument("--out", required=True,
                    help="Output directory (MUST be a committed folder, never /tmp).")
    ap.add_argument("--region", default="", help="Region bbox preset: QC, ON, CA, US, or empty.")
    ap.add_argument("--bbox", default="",
                    help="Custom bbox 'latmin,latmax,lonmin,lonmax' (overrides --region).")
    ap.add_argument("--country", default="ca", help="ISO2 country code for Nominatim filter (default ca).")
    ap.add_argument("--has-header", action="store_true", help="Force-treat first row as header.")
    ap.add_argument("--cols", default="",
                    help="Comma list naming the 5 roles in file column order, "
                         "e.g. id,street,city,region,postal.")
    ap.add_argument("--user-agent", default="klever-proximity-geocoder/1.0 (gamyot@beklever.com)",
                    help="Descriptive Nominatim User-Agent (required by OSM policy).")
    ap.add_argument("--rate", type=float, default=1.1, help="Seconds between requests (>=1.0).")
    ap.add_argument("--resume", action="store_true",
                    help="Reuse already-resolved rows from an existing verification.csv in --out.")
    args = ap.parse_args()

    if "/tmp/" in args.out or args.out.rstrip("/").endswith("/tmp"):
        sys.exit("Refusing to write to /tmp. Outputs must go to a committed folder.")
    if args.rate < 1.0:
        sys.exit("--rate must be >= 1.0 (Nominatim usage policy: max 1 req/sec).")

    bbox = None
    if args.bbox:
        try:
            bbox = tuple(float(x) for x in args.bbox.split(","))
            assert len(bbox) == 4
        except Exception:
            sys.exit("--bbox must be 'latmin,latmax,lonmin,lonmax'")
    elif args.region:
        bbox = REGION_BBOX.get(args.region.upper())
        if bbox is None:
            sys.exit(f"Unknown --region '{args.region}'. Known: {', '.join(REGION_BBOX)}")

    forced_cols = [c.strip() for c in args.cols.split(",")] if args.cols else None
    if forced_cols:
        unknown = [c for c in forced_cols if c not in DEFAULT_COLS]
        if unknown:
            sys.exit(f"--cols has unknown roles {unknown}. Allowed: {DEFAULT_COLS}")

    rows = read_rows(args.input, forced_cols, args.has_header)
    print(f"Read {len(rows)} rows from {args.input}")
    print(f"Country: {args.country} | Region: {args.region or 'none'} | bbox: {bbox}")

    # --- identity / footprint sanity summary (helps catch a mislabeled brand) ---
    region_counts = {}
    for r in rows:
        region_counts[r["region"] or "?"] = region_counts.get(r["region"] or "?", 0) + 1
    print("Footprint by region:", dict(sorted(region_counts.items())))
    if rows:
        print(f"First: {rows[0]['id']} | {rows[0]['street']}, {rows[0]['city']}")
        print(f"Last:  {rows[-1]['id']} | {rows[-1]['street']}, {rows[-1]['city']}")
    print("--> Confirm this footprint matches the advertiser/brand you expect "
          "before trusting the output.\n")

    resume = load_resume(args.out) if args.resume else {}
    if resume:
        print(f"Resume: {len(resume)} rows already resolved, will be reused.\n")

    results = []
    for i, row in enumerate(rows, 1):
        prior = resume.get(row["id"]) if row["id"] else None
        if prior:
            results.append({**row, "lat": prior["latitude"], "lon": prior["longitude"],
                            "tier": prior.get("tier", ""), "status": prior["status"]})
            continue
        print(f"[{i:4}/{len(rows)}] {row['id']}: {row['street'][:50]}, {row['city']}")
        lat, lon, tier, status = geocode_row(row, args.country, args.user_agent, bbox, args.rate)
        results.append({**row, "lat": lat, "lon": lon, "tier": tier, "status": status})

    write_outputs(args.out, results, args.region.upper() if args.region else "", bbox)

    bad = [r for r in results if r["status"] != "OK"]
    print("\n=== SUMMARY ===")
    print(f"Total: {len(results)} | OK: {len(results)-len(bad)} | Needs attention: {len(bad)}")
    if results:
        print(f"First row -> {fmt(results[0]['lat'])}, {fmt(results[0]['lon'])}")
        print(f"Last row  -> {fmt(results[-1]['lat'])}, {fmt(results[-1]['lon'])}")
    print(f"\nOutputs in {args.out}:")
    print("  latlong-paste.tsv   <- paste into the sheet (top-left, fill down)")
    print("  latlong-paste.csv   <- CSV fallback")
    print("  verification.csv    <- eyeball first/last/middle vs the sheet BEFORE trusting")
    print("  failures.md         <- manual fixes")
    print(f"\nAttribution required when persisting: {ATTRIBUTION}")


if __name__ == "__main__":
    main()
