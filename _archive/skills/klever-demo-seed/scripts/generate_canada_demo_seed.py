#!/usr/bin/env python3
"""Generate a STAGED Canadian demo seed for the Measurement Map.

Deliverable (side-effect): this script's value is its OUTPUT. It writes staged
BigQuery seed artifacts for a fabricated Canadian demo advertiser. The script DOES
NOT write to BigQuery. The load is performed MANUALLY after a data-mutation backup
step (see the generated staged/README.md).

Row shapes mirror the live dev schema and the live-proof advertiser 835
(verified 2026-06-02):
  * proximity_daily_geo_zip_performance     -> STATE=full province name, ZIP=FSA,
    COUNTRY="CA"; feeds BOTH the province (state-zoom) and FSA layers.
  * proximity_daily_geo_country_performance -> CDUID + PRUID populated,
    COUNTY_FIPS/COUNTY_NAME/STATE_FIPS NULL (no US FIPS collision); feeds the
    census-division layer.
  * proximity_advertiser_locations          -> emitted as a CSV for the Google-Sheet
    import path (that table is Dataform-rebuilt and cannot be written directly).

Usage:
    python generate_canada_demo_seed.py --advertiser-id 828 --brand "Lumberjack Pastries" \\
        --seed 42 --start-date 2026-05-06 --end-date 2026-06-01 --out-dir staged
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

import geography

DSP = "DEMO"
COUNTRY = "CA"
CHANNEL = "Display"  # matches the Taco Chain (826) demo pattern.

# Live schema column order (verified via `bq show --schema` on 2026-06-02).
ZIP_COLUMNS = [
    "DATE", "KLEVER_ADVERTISER_ID", "DSP", "DSP_ADVERTISER_ID", "ZIP", "STATE",
    "CITY", "IMPRESSIONS", "CLICKS", "SPEND", "DISTRIBUTED_VISITS", "VISITS",
    "CHANNEL", "LOCATION_ID", "LATITUDE", "LONGITUDE", "COUNTRY",
]
COUNTRY_COLUMNS = [
    "DATE", "KLEVER_ADVERTISER_ID", "DSP", "DSP_ADVERTISER_ID", "STATE", "COUNTRY",
    "STATE_FIPS", "COUNTY_FIPS", "COUNTY_NAME", "PRUID", "CDUID", "IMPRESSIONS",
    "CLICKS", "SPEND", "DISTRIBUTED_VISITS", "VISITS", "CHANNEL", "LOCATION_ID",
    "LATITUDE", "LONGITUDE",
]
LOCATION_COLUMNS = [
    "KLEVER_ADVERTISER_ID", "DSP_ADVERTISER_ID", "KLEVER_LOCATION_ID", "ADDRESS",
    "LATITUDE", "LONGITUDE", "LOCATION_NAME", "STATE", "COUNTRY", "CITY", "ZIP_CODE",
]

DEFAULT_ADVERTISER_ID = 828
DEFAULT_BRAND = "Lumberjack Pastries"
DEFAULT_START = "2026-05-06"
DEFAULT_END = "2026-06-01"

ZIP_TABLE = "proximity_daily_geo_zip_performance"
COUNTRY_TABLE = "proximity_daily_geo_country_performance"
CONVERSION_TABLE = "proximity_daily_geo_conversions"
BQ_DATASET = "prj-d-biz-report-im9q1fvvc7.klever_proximity_data"

# Conversion types mirror the working demo advertiser 826 (VIEW_THROUGH heavier than CLICK).
CONVERSION_TYPES = ("VIEW_THROUGH", "CLICK")


def brand_slug(brand: str) -> str:
    """Filesystem/id-safe slug for a brand name (e.g. 'Lumberjack Pastries' -> 'lumberjack-pastries')."""
    return re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-") or "demo"


def dsp_advertiser_id(advertiser_id: int) -> str:
    """Stable per-advertiser DEMO literal, mirroring the 826 'demo<id>' pattern."""
    return f"demo{advertiser_id}"


def date_window(start: str, end: str) -> list[str]:
    """Inclusive list of ISO dates from start to end."""
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    if d1 < d0:
        raise ValueError(f"end-date {end} precedes start-date {start}")
    days = (d1 - d0).days
    return [(d0 + timedelta(days=i)).isoformat() for i in range(days + 1)]


def _metrics(rng: random.Random) -> dict:
    """Realistic, non-negative demo metrics."""
    impressions = rng.randint(500, 25000)
    clicks = rng.randint(0, max(1, impressions // 200))
    visits = rng.randint(0, 50)
    distributed = rng.randint(0, visits) if visits else 0
    spend = round(rng.uniform(5.0, 750.0), 2)
    return {
        "IMPRESSIONS": impressions,
        "CLICKS": clicks,
        "SPEND": spend,
        "DISTRIBUTED_VISITS": distributed,
        "VISITS": visits,
    }


def build_zip_rows(advertiser_id: int, footprint, dates, seed: int = 42) -> list[dict]:
    """One zip-table row per (FSA x date). STATE=full province name, ZIP=FSA."""
    rng = random.Random(seed)
    rows: list[dict] = []
    daid = dsp_advertiser_id(advertiser_id)
    for d in dates:
        for fr in footprint:
            m = _metrics(rng)
            rows.append({
                "DATE": d,
                "KLEVER_ADVERTISER_ID": advertiser_id,
                "DSP": DSP,
                "DSP_ADVERTISER_ID": daid,
                "ZIP": fr.fsa,
                "STATE": fr.province_full_name,
                "CITY": fr.city,
                "IMPRESSIONS": m["IMPRESSIONS"],
                "CLICKS": m["CLICKS"],
                "SPEND": m["SPEND"],
                "DISTRIBUTED_VISITS": m["DISTRIBUTED_VISITS"],
                "VISITS": m["VISITS"],
                "CHANNEL": CHANNEL,
                "LOCATION_ID": None,
                "LATITUDE": None,
                "LONGITUDE": None,
                "COUNTRY": COUNTRY,
            })
    return rows


def build_country_rows(advertiser_id: int, footprint, dates, seed: int = 42) -> list[dict]:
    """One country-table row per (CDUID x date). CDUID+PRUID set, FIPS columns NULL."""
    rng = random.Random(seed + 1)
    daid = dsp_advertiser_id(advertiser_id)
    # Collapse the footprint to distinct (province, CDUID) pairs (one CD can hold many FSAs).
    seen: dict[tuple[str, str], geography.FootprintRow] = {}
    for fr in footprint:
        seen.setdefault((fr.pruid, fr.cduid), fr)
    rows: list[dict] = []
    for d in dates:
        for (pruid, cduid), fr in seen.items():
            m = _metrics(rng)
            rows.append({
                "DATE": d,
                "KLEVER_ADVERTISER_ID": advertiser_id,
                "DSP": DSP,
                "DSP_ADVERTISER_ID": daid,
                "STATE": fr.province_full_name,
                "COUNTRY": COUNTRY,
                "STATE_FIPS": None,
                "COUNTY_FIPS": None,
                "COUNTY_NAME": None,
                "PRUID": pruid,
                "CDUID": cduid,
                "IMPRESSIONS": m["IMPRESSIONS"],
                "CLICKS": m["CLICKS"],
                "SPEND": m["SPEND"],
                "DISTRIBUTED_VISITS": m["DISTRIBUTED_VISITS"],
                "VISITS": m["VISITS"],
                "CHANNEL": CHANNEL,
                "LOCATION_ID": None,
                "LATITUDE": None,
                "LONGITUDE": None,
            })
    return rows


def build_conversion_rows(advertiser_id: int, footprint, dates, seed: int = 42) -> list[dict]:
    """Conversion rows per (FSA x date x type) for the conversion-circle layer.
    CA shape: STATE=full province name, ZIP=FSA, COUNTRY=CA, PRUID+CDUID set, FIPS NULL.
    Mirrors advertiser 826's proximity_daily_geo_conversions rows (VIEW_THROUGH + CLICK)."""
    rng = random.Random(seed + 2)
    daid = dsp_advertiser_id(advertiser_id)
    tag = f"demo{advertiser_id}tag"
    rows: list[dict] = []
    for d in dates:
        for fr in footprint:
            for ctype in CONVERSION_TYPES:
                count = rng.randint(3, 40) if ctype == "VIEW_THROUGH" else rng.randint(0, 6)
                if count == 0:
                    continue  # not every FSA/day has a click conversion
                rows.append({
                    "DATE": d,
                    "KLEVER_ADVERTISER_ID": advertiser_id,
                    "DSP": DSP,
                    "DSP_ADVERTISER_ID": daid,
                    "CONVERSION_TAG_ID": tag,
                    "STATE": fr.province_full_name,
                    "ZIP": fr.fsa,
                    "COUNTRY": COUNTRY,
                    "STATE_FIPS": None,
                    "COUNTY_FIPS": None,
                    "COUNTY_NAME": None,
                    "PRUID": fr.pruid,
                    "CDUID": fr.cduid,
                    "CONVERSION_TYPE": ctype,
                    "METRIC_TYPE": "CONVERSION",
                    "CONVERSION_NAME": "demo_signup",
                    "CONVERSION_ID": 9000000 + advertiser_id,
                    "CONVERSION_VALUE": round(rng.uniform(5.0, 60.0) * count, 2),
                    "IS_OFFLINE": False,
                })
    return rows


def build_location_rows(advertiser_id: int, footprint, brand: str) -> list[dict]:
    """One store location per footprint unit (for the Google-Sheet import CSV)."""
    daid = dsp_advertiser_id(advertiser_id)
    slug = brand_slug(brand)
    rows: list[dict] = []
    for i, fr in enumerate(footprint, start=1):
        rows.append({
            "KLEVER_ADVERTISER_ID": advertiser_id,
            "DSP_ADVERTISER_ID": daid,
            "KLEVER_LOCATION_ID": f"{slug}-{advertiser_id}-{i:03d}",
            "ADDRESS": f"{100 + i} Maple St, {fr.city}, {fr.province_full_name}, {COUNTRY}",
            "LATITUDE": fr.latitude,
            "LONGITUDE": fr.longitude,
            "LOCATION_NAME": f"{brand} #{i}",
            "STATE": fr.province_full_name,
            "COUNTRY": COUNTRY,
            "CITY": fr.city,
            "ZIP_CODE": fr.fsa,
        })
    return rows


def to_ndjson(rows: list[dict]) -> str:
    """Newline-delimited JSON, key order preserved, deterministic."""
    return "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=False) for r in rows) + ("\n" if rows else "")


def to_locations_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=LOCATION_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def to_load_sql(advertiser_id: int) -> str:
    """Idempotent, advertiser-scoped DELETE + LOAD runbook SQL (run manually)."""
    return f"""-- Staged load for the Canadian demo advertiser {advertiser_id}.
-- Run MANUALLY AFTER backing up the target advertiser's existing rows.
-- Idempotent: re-running deletes the advertiser's rows first, then re-inserts.

-- 1. Province + FSA layer (zip-performance table).
DELETE FROM `{BQ_DATASET}.{ZIP_TABLE}`
WHERE KLEVER_ADVERTISER_ID = {advertiser_id};

-- bq load --source_format=NEWLINE_DELIMITED_JSON \\
--   {BQ_DATASET}.{ZIP_TABLE} zip_performance_{advertiser_id}.ndjson

-- 2. Census-division layer (country-performance table).
DELETE FROM `{BQ_DATASET}.{COUNTRY_TABLE}`
WHERE KLEVER_ADVERTISER_ID = {advertiser_id};

-- bq load --source_format=NEWLINE_DELIMITED_JSON \\
--   {BQ_DATASET}.{COUNTRY_TABLE} country_performance_{advertiser_id}.ndjson

-- 3. Conversions layer (conversion circles).
DELETE FROM `{BQ_DATASET}.{CONVERSION_TABLE}`
WHERE KLEVER_ADVERTISER_ID = {advertiser_id};

-- bq load --source_format=NEWLINE_DELIMITED_JSON \\
--   {BQ_DATASET}.{CONVERSION_TABLE} conversions_{advertiser_id}.ndjson

-- 4. Verify (province choropleth gate): expect >= 5 distinct provinces.
SELECT COUNT(DISTINCT STATE) AS provinces
FROM `{BQ_DATASET}.{ZIP_TABLE}`
WHERE KLEVER_ADVERTISER_ID = {advertiser_id} AND COUNTRY = 'CA';
"""


def _readme(advertiser_id: int, start: str, end: str, brand: str) -> str:
    return f"""# {brand} Canadian demo seed (staged) — advertiser {advertiser_id}

Generated by `generate_canada_demo_seed.py` (advertiser {advertiser_id}, brand "{brand}",
window {start} .. {end}). The script performs NO BigQuery write. Load is manual.

## Artifacts
- `zip_performance_{advertiser_id}.ndjson` — rows for `{ZIP_TABLE}` (province + FSA layers)
- `country_performance_{advertiser_id}.ndjson` — rows for `{COUNTRY_TABLE}` (census-division layer)
- `conversions_{advertiser_id}.ndjson` — rows for `{CONVERSION_TABLE}` (conversion circles)
- `locations_{advertiser_id}.csv` — store locations for the Google-Sheet import path
  (do NOT load directly: `proximity_advertiser_locations` is Dataform-rebuilt from a Sheet)
- `load_{advertiser_id}.sql` — DELETE + load runbook + verify query

## Manual load runbook
1. **Back up first** (data-mutation rule). Snapshot the target advertiser's existing rows
   to a local backups/ dir:
   ```
   bq query --use_legacy_sql=false --format=prettyjson \\
     'SELECT * FROM `{BQ_DATASET}.{ZIP_TABLE}` WHERE KLEVER_ADVERTISER_ID={advertiser_id}' \\
     > backups/zip_{advertiser_id}_before.json
   bq query --use_legacy_sql=false --format=prettyjson \\
     'SELECT * FROM `{BQ_DATASET}.{COUNTRY_TABLE}` WHERE KLEVER_ADVERTISER_ID={advertiser_id}' \\
     > backups/country_{advertiser_id}_before.json
   ```
2. Run the DELETE statements in `load_{advertiser_id}.sql`.
3. `bq load` the two ndjson files (commands are in the SQL file comments).
4. Run the verify query (expect >= 5 distinct provinces).
5. Confirm rendering with CA-only `/api/v1/map/data/state|zip` calls (mixed US/CA is a
   separate, deferred ticket — do not mix region codes in one request).
6. Onboard the store locations via the Google Sheet using `locations_{advertiser_id}.csv`.
"""


def write_staged(advertiser_id, footprint, dates, out_dir, seed, brand) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    zip_rows = build_zip_rows(advertiser_id, footprint, dates, seed=seed)
    country_rows = build_country_rows(advertiser_id, footprint, dates, seed=seed)
    conversion_rows = build_conversion_rows(advertiser_id, footprint, dates, seed=seed)
    location_rows = build_location_rows(advertiser_id, footprint, brand)

    (out / f"zip_performance_{advertiser_id}.ndjson").write_text(to_ndjson(zip_rows))
    (out / f"country_performance_{advertiser_id}.ndjson").write_text(to_ndjson(country_rows))
    (out / f"conversions_{advertiser_id}.ndjson").write_text(to_ndjson(conversion_rows))
    (out / f"locations_{advertiser_id}.csv").write_text(to_locations_csv(location_rows))
    (out / f"load_{advertiser_id}.sql").write_text(to_load_sql(advertiser_id))
    (out / "README.md").write_text(_readme(advertiser_id, dates[0], dates[-1], brand))

    return {
        "zip_rows": len(zip_rows),
        "country_rows": len(country_rows),
        "conversion_rows": len(conversion_rows),
        "location_rows": len(location_rows),
        "distinct_provinces": len({r["STATE"] for r in zip_rows}),
    }


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Generate a staged Canadian demo seed for the Measurement Map.")
    p.add_argument("--advertiser-id", type=int, default=DEFAULT_ADVERTISER_ID,
                   help="Klever advertiser ID (must exist in user-management to be portal-selectable).")
    p.add_argument("--brand", default=DEFAULT_BRAND, help="Demo brand / advertiser display name.")
    p.add_argument("--out-dir", default="staged", help="Output directory for staged artifacts.")
    p.add_argument("--start-date", default=DEFAULT_START, help="ISO start date (inclusive).")
    p.add_argument("--end-date", default=DEFAULT_END, help="ISO end date (inclusive).")
    p.add_argument("--seed", type=int, default=42, help="RNG seed for deterministic metrics.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    dates = date_window(args.start_date, args.end_date)
    summary = write_staged(
        args.advertiser_id, geography.FOOTPRINT, dates, args.out_dir, args.seed, args.brand,
    )
    print(
        f"Staged seed for advertiser {args.advertiser_id} ('{args.brand}') -> {args.out_dir}: "
        f"{summary['zip_rows']} zip rows, {summary['country_rows']} country rows, "
        f"{summary['conversion_rows']} conversion rows, {summary['location_rows']} locations, "
        f"{summary['distinct_provinces']} distinct provinces."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
