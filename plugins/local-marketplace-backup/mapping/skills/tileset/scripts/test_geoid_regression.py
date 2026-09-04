#!/usr/bin/env python3
"""
Regression test: US county GEO_ID prefix stripping  (tileset mode: geoid-regression).

Verifies that the merge step's prefix stripping (0500000US36061 -> 36061)
produces clean 5-digit FIPS codes that match what the frontend data processor
expects, that CA CDs are clean 4-digit, that no prefix remnants survive, and
that feature counts are preserved.

Ported from test_geoid_regression.py (KTP-676). Generalized only on the data
root: pass --work-dir (or set TILESET_WORK_DIR). The GEOID normalization rule
itself is owned by mapping:crosswalk; this mode regression-checks the merged
output against it.

Usage:
    python3 test_geoid_regression.py --work-dir /path/to/geography
"""

import argparse
import json
import os
import re
import sys

MERGED_COUNTY_PATH = ""
US_SOURCE_PATH = ""


def configure_paths(work_dir):
    global MERGED_COUNTY_PATH, US_SOURCE_PATH
    work_dir = os.path.abspath(work_dir)
    MERGED_COUNTY_PATH = os.path.join(work_dir, "merged", "county_boundaries.geojson")
    US_SOURCE_PATH = os.path.join(work_dir, "sources", "us_county_5m.geojson")


def test_all_us_counties_have_clean_fips():
    """Every US county GEO_ID must be exactly 5 digits, no prefix."""
    with open(MERGED_COUNTY_PATH) as f:
        data = json.load(f)
    us_features = [f for f in data["features"] if f["properties"].get("COUNTRY") == "US"]

    failures = []
    for feat in us_features:
        geo_id = feat["properties"].get("GEO_ID", "")
        if not re.match(r"^\d{5}$", geo_id):
            name = feat["properties"].get("NAME", "unknown")
            failures.append(f"{name}: GEO_ID='{geo_id}'")

    assert len(failures) == 0, (
        f"{len(failures)} US counties have non-5-digit GEO_ID:\n" + "\n".join(failures[:20])
    )
    print(f"PASS: {len(us_features)} US counties all have clean 5-digit FIPS")


def test_no_prefix_remnants():
    """No GEO_ID in merged output should contain '0500000US'."""
    with open(MERGED_COUNTY_PATH) as f:
        data = json.load(f)
    for feat in data["features"]:
        geo_id = feat["properties"].get("GEO_ID", "")
        assert "0500000US" not in geo_id, f"Prefix remnant found: {geo_id}"
    print(f"PASS: No prefix remnants in {len(data['features'])} features")


def test_ca_counties_have_4_digit_cduid():
    """Every CA county GEO_ID must be exactly 4 digits."""
    with open(MERGED_COUNTY_PATH) as f:
        data = json.load(f)
    ca_features = [f for f in data["features"] if f["properties"].get("COUNTRY") == "CA"]

    failures = []
    for feat in ca_features:
        geo_id = feat["properties"].get("GEO_ID", "")
        if not re.match(r"^\d{4}$", geo_id):
            name = feat["properties"].get("NAME", "unknown")
            failures.append(f"{name}: GEO_ID='{geo_id}'")

    assert len(failures) == 0, (
        f"{len(failures)} CA CDs have non-4-digit GEO_ID:\n" + "\n".join(failures[:20])
    )
    print(f"PASS: {len(ca_features)} CA CDs all have clean 4-digit CDUID")


def test_geoid_round_trip_with_normalize_function():
    """
    Simulate the frontend normalizeCountyGeoid function against merged output.

        normalizeCountyGeoid: geoid.includes("US") ? geoid.split("US")[1] : geoid

    After prefix stripping, US GEO_IDs are '36061' (no 'US' substring) and CA
    GEO_IDs are '3506' (no 'US' substring); both return unchanged. Catches a
    partial-strip regression (e.g. '0US36061') by asserting exact format.
    """
    with open(MERGED_COUNTY_PATH) as f:
        data = json.load(f)

    def normalize_county_geoid(geoid):
        if "US" in geoid:
            return geoid.split("US")[1]
        return geoid

    for feat in data["features"]:
        geo_id = feat["properties"].get("GEO_ID", "")
        country = feat["properties"].get("COUNTRY", "")
        normalized = normalize_county_geoid(geo_id)
        if country == "US":
            assert normalized == geo_id, f"US normalization changed value: {geo_id} -> {normalized}"
            assert re.match(r"^\d{5}$", normalized), f"US normalized GEO_ID not 5-digit: {normalized}"
        elif country == "CA":
            assert normalized == geo_id, f"CA normalization changed value: {geo_id} -> {normalized}"
            assert re.match(r"^\d{4}$", normalized), f"CA normalized GEO_ID not 4-digit: {normalized}"

    print("PASS: normalizeCountyGeoid produces correct results for all features")


def test_source_to_merged_feature_count():
    """US source feature count must survive the merge intact."""
    with open(US_SOURCE_PATH) as f:
        source_data = json.load(f)
    with open(MERGED_COUNTY_PATH) as f:
        merged_data = json.load(f)

    source_count = len(source_data["features"])
    merged_us_count = len([f for f in merged_data["features"] if f["properties"].get("COUNTRY") == "US"])

    assert source_count == merged_us_count, (
        f"US county count mismatch: source={source_count}, merged={merged_us_count}"
    )
    print(f"PASS: US county count preserved: {source_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GEOID regression checks on merged output.")
    parser.add_argument("--work-dir", default=os.environ.get("TILESET_WORK_DIR"),
                        help="geography data root (or set TILESET_WORK_DIR)")
    args = parser.parse_args()
    if not args.work_dir:
        parser.error("--work-dir is required (or set TILESET_WORK_DIR)")
    configure_paths(args.work_dir)

    tests = [
        test_all_us_counties_have_clean_fips,
        test_no_prefix_remnants,
        test_ca_counties_have_4_digit_cduid,
        test_geoid_round_trip_with_normalize_function,
        test_source_to_merged_feature_count,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failures += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}: {e}")
            failures += 1

    if failures > 0:
        print(f"\n{failures} test(s) FAILED")
    else:
        print(f"\nAll {len(tests)} tests PASSED")

    sys.exit(1 if failures > 0 else 0)
