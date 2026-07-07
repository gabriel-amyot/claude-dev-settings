#!/usr/bin/env python3
"""Generate DURABLE Bronze demo-dsp CSVs for a Canadian Measurement-Map demo advertiser.

Why this exists (vs. generate_canada_demo_seed.py):
  The older script writes Gold-table NDJSON loaded directly into klever_proximity_data.*.
  Dataform rebuilds those Gold tables on a rolling 30-day window every run, so a direct
  Gold seed is WIPED within ~24h. This script instead produces the upstream **Bronze**
  demo-dsp CSVs that the cloud-storage-to-bigquery Cloud Function ingests; Dataform then
  copies Bronze -> generic_dsp -> Gold on every run. As long as the Bronze rows stay in
  the last-30-day window, the Gold layer is rebuilt from them and the demo persists.

  Drop these CSVs in the daily-import bucket (dev: bkt-daily-import-im9q1fvvc7). The Cloud
  Function loads them into klever_daily_data_import.demo_dsp_*; the next Dataform `daily`
  run lights up the Measurement Map.

Verified contract (read-proven 2026-06-16 against origin/dev klever-data-workflow +
app-cloud-storage-to-bigquery + live dev BQ):
  * The Cloud Function loads CSVs by POSITIONAL column order against the live BQ schema
    (skipLeadingRows=1, autodetect off). The header row is required but ignored; column
    ORDER must match the BQ table exactly. Schemas below are the live ordinal order.
  * COUNTRY is derived downstream purely from a ZIP regex: a 3-char FSA ^[A-Za-z]\\d[A-Za-z]$
    -> 'CA'. No COUNTRY column exists in the Bronze geo tables.
  * CDUID/PRUID are derived via LEFT JOIN third_party_data.fsa_to_cd_crosswalk ON ZIP=CFSAUID.
    Pick FSAs present in that crosswalk (the default FOOTPRINT's 14 FSAs all are).
  * KLEVER_ADVERTISER_ID is resolved via INNER JOIN dsp_account.DSP_PROVIDER_ID = DSP_ADVERTISER_ID.
    The advertiser MUST exist in dsp_account (842 -> 'demo842' already registered).
  * VISITS/DISTRIBUTED_VISITS join foot_traffic on (DATE, ZIP, DSP_ADVERTISER_ID);
    VISITS = COUNT(1) of foot_traffic rows, DISTRIBUTED_VISITS = SUM(DEVICE_COUNT).
  * REPORT files delete-before-append scoped by (date range in filename) AND entity-id AND
    DSP='DEMO'. Use entity type ADVERTISER + the DSP_ADVERTISER_ID so an upload only ever
    rewrites THIS advertiser's window -- never another demo advertiser's rows. Locations is
    STRUCTURE/OVERRIDE: it truncates the WHOLE table, so the file MUST contain every
    advertiser. Pass --preserve-locations-csv with the current table dump.
  * Dataform normalizes only the last NUMBER_OF_DAYS_TO_NORMALIZE=30 days. Keep the window
    recent (default mirrors the live Taco Chain demo window 2026-03-01..2026-06-30).

Bronze table schemas (live ordinal order, klever_daily_data_import):
  demo_dsp_advertiser_locations : DSP, DSP_PARTNER_ID, DSP_ADVERTISER_ID, KLEVER_LOCATION_ID,
      ADDRESS, LATITUDE, LONGITUDE, LOCATION_NAME, STATE, COUNTRY, CITY, ZIP_CODE
  demo_dsp_daily_geo_performance: DATE, DSP, DSP_PARTNER_ID, DSP_ADVERTISER_ID, CHANNEL,
      STATE, CITY, ZIP, IMPRESSIONS, CLICKS, SPEND_USD
  demo_dsp_daily_geo_conversions: DATE, DSP, DSP_PARTNER_ID, DSP_ADVERTISER_ID,
      CONVERSION_TAG_ID, STATE, ZIP, CONVERSION_TYPE, METRIC_TYPE, CONVERSION_NAME,
      CONVERSION_ID, CONVERSION_VALUE, IS_OFFLINE
  demo_dsp_foot_traffic         : VISIT_DATE, DSP, DSP_PARTNER_ID, DSP_ADVERTISER_ID, ZIP,
      STATE, CITY, DEVICE_COUNT

Usage:
    python generate_bronze_csv.py \\
        --advertiser-id 842 --brand "Lumberjack Pastries" \\
        --dsp-advertiser-id demo842 --dsp-partner-id demo371fdcf \\
        --start-date 2026-03-01 --end-date 2026-06-30 \\
        --preserve-locations-csv current_locations.csv \\
        --location-id-base 1000842001 \\
        --out-dir bronze
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import re
from datetime import date, timedelta
from pathlib import Path

import geography

DSP = "DEMO"
CHANNEL = "Display"  # matches the live Taco Chain (826) demo pattern.
CONVERSION_TYPES = ("VIEW_THROUGH", "CLICK")

# Live Bronze schemas (positional order is load-critical -- see module docstring).
LOCATION_COLUMNS = [
    "DSP", "DSP_PARTNER_ID", "DSP_ADVERTISER_ID", "KLEVER_LOCATION_ID", "ADDRESS",
    "LATITUDE", "LONGITUDE", "LOCATION_NAME", "STATE", "COUNTRY", "CITY", "ZIP_CODE",
]
GEO_PERF_COLUMNS = [
    "DATE", "DSP", "DSP_PARTNER_ID", "DSP_ADVERTISER_ID", "CHANNEL", "STATE", "CITY",
    "ZIP", "IMPRESSIONS", "CLICKS", "SPEND_USD",
]
CONVERSION_COLUMNS = [
    "DATE", "DSP", "DSP_PARTNER_ID", "DSP_ADVERTISER_ID", "CONVERSION_TAG_ID", "STATE",
    "ZIP", "CONVERSION_TYPE", "METRIC_TYPE", "CONVERSION_NAME", "CONVERSION_ID",
    "CONVERSION_VALUE", "IS_OFFLINE",
]
FOOT_TRAFFIC_COLUMNS = [
    "VISIT_DATE", "DSP", "DSP_PARTNER_ID", "DSP_ADVERTISER_ID", "ZIP", "STATE", "CITY",
    "DEVICE_COUNT",
]

# 2-letter province codes for the locations STATE column (mirrors the US locations rows,
# which use 2-letter state codes). The geo/conversion tables use the FULL province name.
PROVINCE_ABBR = {
    "Ontario": "ON", "Quebec": "QC", "British Columbia": "BC",
    "Alberta": "AB", "Manitoba": "MB",
}

KEY_LOCATIONS = "demo-dsp-advertiser-locations"
KEY_GEO_PERF = "demo-dsp-daily-geo-performance"
KEY_CONVERSIONS = "demo-dsp-daily-geo-conversions"
KEY_FOOT_TRAFFIC = "demo-dsp-foot-traffic"


def _dt(s: str) -> str:
    """ISO date (YYYY-MM-DD) -> filename date token (YYYY.MM.DD) per FileDefinitionConfigService."""
    return s.replace("-", ".")


def report_filename(key: str, start: str, end: str, dsp_advertiser_id: str) -> str:
    """REPORT filename: {key}_report_{YYYY.MM.DD}-{YYYY.MM.DD}_advertiser_{dspAdvertiserId}.csv.
    entity=ADVERTISER scopes the delete-before-append to THIS advertiser only."""
    return f"{key}_report_{_dt(start)}-{_dt(end)}_advertiser_{dsp_advertiser_id}.csv"


def date_window(start: str, end: str) -> list[str]:
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    if d1 < d0:
        raise ValueError(f"end-date {end} precedes start-date {start}")
    return [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


def _metrics(rng: random.Random) -> dict:
    impressions = rng.randint(500, 25000)
    clicks = rng.randint(0, max(1, impressions // 200))
    spend = round(rng.uniform(5.0, 750.0), 2)
    return {"IMPRESSIONS": impressions, "CLICKS": clicks, "SPEND_USD": spend}


def build_geo_perf_rows(footprint, dates, dsp_aid, dsp_pid, seed=42) -> list[dict]:
    """One geo-performance row per (FSA x date). STATE=full province name, ZIP=FSA."""
    rng = random.Random(seed)
    rows = []
    for d in dates:
        for fr in footprint:
            m = _metrics(rng)
            rows.append({
                "DATE": d, "DSP": DSP, "DSP_PARTNER_ID": dsp_pid, "DSP_ADVERTISER_ID": dsp_aid,
                "CHANNEL": CHANNEL, "STATE": fr.province_full_name, "CITY": fr.city, "ZIP": fr.fsa,
                "IMPRESSIONS": m["IMPRESSIONS"], "CLICKS": m["CLICKS"], "SPEND_USD": m["SPEND_USD"],
            })
    return rows


def build_conversion_rows(footprint, dates, dsp_aid, dsp_pid, advertiser_id, seed=42) -> list[dict]:
    """Conversion rows per (FSA x date x type). STATE=full province name, ZIP=FSA."""
    rng = random.Random(seed + 2)
    tag = f"demo{advertiser_id}tag"
    rows = []
    for d in dates:
        for fr in footprint:
            for ctype in CONVERSION_TYPES:
                count = rng.randint(3, 40) if ctype == "VIEW_THROUGH" else rng.randint(0, 6)
                if count == 0:
                    continue  # not every FSA/day has a click conversion
                rows.append({
                    "DATE": d, "DSP": DSP, "DSP_PARTNER_ID": dsp_pid, "DSP_ADVERTISER_ID": dsp_aid,
                    "CONVERSION_TAG_ID": tag, "STATE": fr.province_full_name, "ZIP": fr.fsa,
                    "CONVERSION_TYPE": ctype, "METRIC_TYPE": "CONVERSION", "CONVERSION_NAME": "demo_signup",
                    "CONVERSION_ID": 9000000 + advertiser_id,
                    "CONVERSION_VALUE": round(rng.uniform(5.0, 60.0) * count, 2), "IS_OFFLINE": "false",
                })
    return rows


def build_foot_traffic_rows(footprint, dates, dsp_aid, dsp_pid, seed=42) -> list[dict]:
    """One foot-traffic row per (FSA x date). DEVICE_COUNT -> DISTRIBUTED_VISITS downstream."""
    rng = random.Random(seed + 3)
    rows = []
    for d in dates:
        for fr in footprint:
            rows.append({
                "VISIT_DATE": d, "DSP": DSP, "DSP_PARTNER_ID": dsp_pid, "DSP_ADVERTISER_ID": dsp_aid,
                "ZIP": fr.fsa, "STATE": fr.province_full_name, "CITY": fr.city,
                "DEVICE_COUNT": rng.randint(10, 200),
            })
    return rows


def build_location_rows(footprint, dsp_aid, dsp_pid, brand, id_base) -> list[dict]:
    """One store location per footprint unit. STATE=2-letter province code (mirrors US rows)."""
    rows = []
    for i, fr in enumerate(footprint):
        rows.append({
            "DSP": DSP, "DSP_PARTNER_ID": dsp_pid, "DSP_ADVERTISER_ID": dsp_aid,
            "KLEVER_LOCATION_ID": str(id_base + i),
            "ADDRESS": f"{100 + i} Maple St, {fr.city}, {PROVINCE_ABBR.get(fr.province_full_name, fr.province_full_name)}",
            "LATITUDE": fr.latitude, "LONGITUDE": fr.longitude,
            "LOCATION_NAME": f"{brand} #{i + 1}",
            "STATE": PROVINCE_ABBR.get(fr.province_full_name, fr.province_full_name),
            "COUNTRY": "CA", "CITY": fr.city, "ZIP_CODE": fr.fsa,
        })
    return rows


def read_preserve_locations(path: str | None) -> list[dict]:
    """Read the current demo_dsp_advertiser_locations dump (CSV w/ header) to preserve in OVERRIDE.
    OVERRIDE truncates the whole table, so every other advertiser's rows must be re-included."""
    if not path:
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in LOCATION_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"--preserve-locations-csv missing columns {missing}; "
                             f"dump with: SELECT {','.join(LOCATION_COLUMNS)} FROM ...demo_dsp_advertiser_locations")
        for r in reader:
            rows.append({c: r[c] for c in LOCATION_COLUMNS})
    return rows


def to_csv(rows: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def write_bronze(args) -> dict:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fp = geography.FOOTPRINT
    dates = date_window(args.start_date, args.end_date)
    dsp_aid, dsp_pid = args.dsp_advertiser_id, args.dsp_partner_id

    geo = build_geo_perf_rows(fp, dates, dsp_aid, dsp_pid, args.seed)
    conv = build_conversion_rows(fp, dates, dsp_aid, dsp_pid, args.advertiser_id, args.seed)
    foot = build_foot_traffic_rows(fp, dates, dsp_aid, dsp_pid, args.seed)
    new_locs = build_location_rows(fp, dsp_aid, dsp_pid, args.brand, args.location_id_base)

    preserved = read_preserve_locations(args.preserve_locations_csv)
    # Drop any pre-existing rows for THIS advertiser, then re-add (idempotent re-run).
    preserved = [r for r in preserved if r["DSP_ADVERTISER_ID"] != dsp_aid]
    all_locs = preserved + new_locs

    geo_fn = report_filename(KEY_GEO_PERF, args.start_date, args.end_date, dsp_aid)
    conv_fn = report_filename(KEY_CONVERSIONS, args.start_date, args.end_date, dsp_aid)
    foot_fn = report_filename(KEY_FOOT_TRAFFIC, args.start_date, args.end_date, dsp_aid)
    loc_fn = f"{KEY_LOCATIONS}.csv"  # STRUCTURE: no date/entity suffix.

    (out / geo_fn).write_text(to_csv(geo, GEO_PERF_COLUMNS))
    (out / conv_fn).write_text(to_csv(conv, CONVERSION_COLUMNS))
    (out / foot_fn).write_text(to_csv(foot, FOOT_TRAFFIC_COLUMNS))
    (out / loc_fn).write_text(to_csv(all_locs, LOCATION_COLUMNS))

    return {
        "geo_rows": len(geo), "conversion_rows": len(conv), "foot_rows": len(foot),
        "new_location_rows": len(new_locs), "preserved_location_rows": len(preserved),
        "total_location_rows": len(all_locs),
        "distinct_provinces": len({r["STATE"] for r in geo}),
        "distinct_fsas": len({r["ZIP"] for r in geo}),
        "files": {"geo_performance": geo_fn, "conversions": conv_fn,
                  "foot_traffic": foot_fn, "locations": loc_fn},
    }


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Generate durable Bronze demo-dsp CSVs for a Canadian demo advertiser.")
    p.add_argument("--advertiser-id", type=int, default=842, help="KLEVER advertiser ID (must exist in dsp_account).")
    p.add_argument("--brand", default="Lumberjack Pastries", help="Demo brand / location display name.")
    p.add_argument("--dsp-advertiser-id", default=None,
                   help="Bronze DSP_ADVERTISER_ID; must equal dsp_account.DSP_PROVIDER_ID. Default demo<id>.")
    p.add_argument("--dsp-partner-id", default="demo371fdcf", help="Bronze DSP_PARTNER_ID (shared demo partner).")
    p.add_argument("--start-date", default="2026-03-01", help="ISO start date (inclusive).")
    p.add_argument("--end-date", default="2026-06-30", help="ISO end date (inclusive).")
    p.add_argument("--preserve-locations-csv", default=None,
                   help="CSV dump of the CURRENT demo_dsp_advertiser_locations table (required for the OVERRIDE-all locations file).")
    p.add_argument("--location-id-base", type=int, default=1000842001,
                   help="First KLEVER_LOCATION_ID for this advertiser's stores (sequential).")
    p.add_argument("--out-dir", default="bronze", help="Output directory for Bronze CSVs.")
    p.add_argument("--seed", type=int, default=42, help="RNG seed for deterministic metrics.")
    a = p.parse_args(argv)
    if a.dsp_advertiser_id is None:
        a.dsp_advertiser_id = f"demo{a.advertiser_id}"
    return a


def main(argv=None) -> int:
    args = parse_args(argv)
    s = write_bronze(args)
    print(
        f"Bronze CSVs for advertiser {args.advertiser_id} ('{args.brand}', DSP_ADVERTISER_ID={args.dsp_advertiser_id}) "
        f"-> {args.out_dir}:\n"
        f"  {s['files']['geo_performance']}: {s['geo_rows']} rows\n"
        f"  {s['files']['conversions']}: {s['conversion_rows']} rows\n"
        f"  {s['files']['foot_traffic']}: {s['foot_rows']} rows\n"
        f"  {s['files']['locations']}: {s['total_location_rows']} rows "
        f"({s['preserved_location_rows']} preserved + {s['new_location_rows']} new)\n"
        f"  coverage: {s['distinct_provinces']} provinces, {s['distinct_fsas']} FSAs"
    )
    if not args.preserve_locations_csv:
        print("  WARNING: no --preserve-locations-csv given; locations file contains ONLY this "
              "advertiser. The OVERRIDE upload would DELETE all other advertisers' pins. "
              "Dump the current table first and pass it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
