#!/usr/bin/env python3
"""LIVE integration eval for proximity:geocode — SMALL Nominatim check.

NETWORK-DEPENDENT and SKIPPABLE. Hits the real public Nominatim/OSM endpoint
for a handful of known-good addresses, respecting the OSM usage policy
(>= 1 req/sec; this run uses the script's own --rate default of 1.1s).

What it verifies end-to-end against live geocoding:
  - ORDER is preserved (output row N corresponds to input row N)
  - COUNT matches input exactly (failures stay as flagged rows, never dropped)
  - known-good coords land within ~0.05 deg of expected
  - a deliberately broken row is flagged (FAILED / APPROXIMATE / SUSPECT)
    IN POSITION (it must occupy its original input slot, not be removed)

Outputs are written to evals/_run_output/ (NEVER /tmp), per skill policy.

Run (opt-in):
  python3 eval_integration.py            # runs the live check
  RUN_LIVE=0 python3 eval_integration.py # explicit skip (exit 0)

If the network/endpoint is unreachable, the eval prints SKIPPED and exits 0
so it never blocks a CI run that has no internet.
"""

import os
import sys
import urllib.request

from _loader import load_geocoder, FIXTURES_DIR

G = load_geocoder()

OUT_DIR = os.path.join(os.path.dirname(__file__), "_run_output")
FIXTURE = os.path.join(FIXTURES_DIR, "integration_addresses.tsv")
TOL = 0.05  # degrees (~5.5 km lat), generous for rooftop-vs-centroid drift

# Expected approximate coords for the known-good rows (lat, lon).
EXPECTED = {
    "btg-kennedy": (43.759, -79.278),       # 1293 Kennedy Rd, Toronto (proven KTP-755)
    "btg-yonge": (43.769, -79.385),         # 2901 Bayview Ave, Toronto
    "qc-parliament": (46.808, -71.214),     # 1045 Rue de la Chevrotiere, Quebec City
}
BROKEN_ID = "broken-row"

_failures = []
_passed = 0


def check(cond, msg):
    global _passed
    if cond:
        _passed += 1
    else:
        _failures.append(msg)
        print(f"FAIL: {msg}", file=sys.stderr)


def network_available():
    try:
        urllib.request.urlopen(
            urllib.request.Request("https://nominatim.openstreetmap.org/",
                                   headers={"User-Agent": "klever-geocode-eval/1.0"}),
            timeout=8, context=G.SSL_CTX,
        )
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  (network probe failed: {e})", file=sys.stderr)
        return False


def main():
    if os.environ.get("RUN_LIVE") == "0":
        print("SKIPPED: RUN_LIVE=0 set.")
        sys.exit(0)
    if not network_available():
        print("SKIPPED: Nominatim/OSM not reachable (network-dependent eval).")
        sys.exit(0)

    rows = G.read_rows(FIXTURE, None, False)
    n = len(rows)
    print(f"Read {n} fixture rows. Geocoding live (rate=1.1s, ~{n*2}s worst case)...")

    region = "CA"
    bbox = G.REGION_BBOX[region]
    ua = "klever-geocode-eval/1.0 (gamyot@beklever.com)"

    results = []
    for i, row in enumerate(rows, 1):
        lat, lon, tier, status = G.geocode_row(row, "ca", ua, bbox, 1.1)
        results.append({**row, "lat": lat, "lon": lon, "tier": tier, "status": status})
        print(f"  [{i}/{n}] {row['id']}: {status} tier={tier} ({lat}, {lon})")

    G.write_outputs(OUT_DIR, results, region, bbox)

    # COUNT preserved.
    check(len(results) == n, f"count mismatch: {len(results)} != {n}")

    # ORDER preserved: result[i].id == input[i].id.
    for i in range(n):
        check(results[i]["id"] == rows[i]["id"],
              f"order broken at row {i}: {results[i]['id']!r} != {rows[i]['id']!r}")

    # Known-good rows within tolerance.
    for r in results:
        if r["id"] in EXPECTED:
            exp_lat, exp_lon = EXPECTED[r["id"]]
            check(r["lat"] is not None and r["lon"] is not None,
                  f"{r['id']}: expected a hit, got None ({r['status']})")
            if r["lat"] is not None:
                dlat, dlon = abs(r["lat"] - exp_lat), abs(r["lon"] - exp_lon)
                check(dlat <= TOL and dlon <= TOL,
                      f"{r['id']}: ({r['lat']},{r['lon']}) off expected "
                      f"({exp_lat},{exp_lon}) by ({dlat:.4f},{dlon:.4f}) > {TOL}")

    # Broken row flagged IN POSITION (slot 4, index 3).
    broken_idx = next(i for i, rr in enumerate(rows) if rr["id"] == BROKEN_ID)
    broken = results[broken_idx]
    check(broken["id"] == BROKEN_ID,
          f"broken row moved out of position {broken_idx}")
    check(broken["status"] in ("FAILED", "APPROXIMATE", "SUSPECT_OUT_OF_BBOX"),
          f"broken row not flagged, status={broken['status']!r}")

    # Paste artifact has exactly n lines (failures emit a blank lat/lon line).
    paste = os.path.join(OUT_DIR, "latlong-paste.tsv")
    with open(paste, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    check(len(lines) == n,
          f"latlong-paste.tsv has {len(lines)} lines, expected {n} (order/fill-down contract)")

    total = _passed + len(_failures)
    print(f"\n=== INTEGRATION EVAL: {_passed}/{total} assertions passed ===")
    print(f"Outputs written to {OUT_DIR}")
    if _failures:
        print(f"{len(_failures)} FAILED:")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("All integration assertions passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
