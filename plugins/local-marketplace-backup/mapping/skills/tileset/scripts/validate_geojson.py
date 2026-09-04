#!/usr/bin/env python3
"""
GeoJSON Source and Merge Validation Script  (tileset mode: validate-source).

Validates source data feature counts/properties and merged-output property
naming/GEOID formats before tiling.

Ported from validate_geojson.py (KTP-676). Generalized only on the data root:
pass --work-dir (or set TILESET_WORK_DIR). The US+CA assertions are the proven
default; for other regions adapt the expected counts/codes.

Usage:
    python3 validate_geojson.py --work-dir /path/to/geography             # all
    python3 validate_geojson.py --work-dir /path/to/geography --sources   # sources
    python3 validate_geojson.py --work-dir /path/to/geography --merged    # merged
"""

import argparse
import json
import os
import re
import sys

SOURCES_DIR = ""
MERGED_DIR = ""

# Known null-geometry FSAs (geometry-less in some Stats Canada editions)
NULL_GEOMETRY_FSAS = {"E2R", "J5N", "M7A"}

# Valid Canadian province alpha-2 codes
VALID_ALPHA2 = {
    "NL", "PE", "NS", "NB", "QC", "ON",
    "MB", "SK", "AB", "BC", "YT", "NT", "NU",
}


def configure_paths(work_dir):
    global SOURCES_DIR, MERGED_DIR
    work_dir = os.path.abspath(work_dir)
    SOURCES_DIR = os.path.join(work_dir, "sources")
    MERGED_DIR = os.path.join(work_dir, "merged")


################################################################################
# Source Validators
################################################################################

def validate_provinces(path=None):
    """ca_provinces.geojson: 13 features, all with PRUID, valid WGS84 geometry."""
    if path is None:
        path = os.path.join(SOURCES_DIR, "ca_provinces.geojson")

    print(f"  Validating provinces: {os.path.basename(path)}")
    with open(path) as f:
        data = json.load(f)
    features = data["features"]

    assert len(features) == 13, f"Expected 13 province features, got {len(features)}"

    for feat in features:
        props = feat["properties"]
        pruid = props.get("PRUID", "")
        assert pruid and str(pruid).strip(), f"Feature missing or empty PRUID: {props}"
        geom = feat.get("geometry")
        assert geom is not None, f"Null geometry for PRUID={pruid}"
        assert geom["type"] in ("Polygon", "MultiPolygon"), (
            f"Invalid geometry type '{geom['type']}' for PRUID={pruid}"
        )
        _assert_wgs84_bounds(geom, f"PRUID={pruid}")

    print(f"    PASS: {len(features)} provinces, all valid")


def validate_cd(path=None):
    """ca_cd.geojson: 293 features, 4-digit CDUID, valid geometry."""
    if path is None:
        path = os.path.join(SOURCES_DIR, "ca_cd.geojson")

    print(f"  Validating census divisions: {os.path.basename(path)}")
    with open(path) as f:
        data = json.load(f)
    features = data["features"]

    assert len(features) == 293, f"Expected 293 CD features, got {len(features)}"

    for feat in features:
        props = feat["properties"]
        cduid = str(props.get("CDUID", ""))
        assert len(cduid) == 4 and cduid.isdigit(), (
            f"Invalid CDUID '{cduid}': expected 4-digit string"
        )
        geom = feat.get("geometry")
        assert geom is not None, f"Null geometry for CDUID={cduid}"
        assert geom["type"] in ("Polygon", "MultiPolygon"), (
            f"Invalid geometry type '{geom['type']}' for CDUID={cduid}"
        )

    print(f"    PASS: {len(features)} census divisions, all valid")


def validate_fsa(path=None):
    """ca_fsa.geojson: 1,643 features, 3-char CFSAUID, null-geometry handling."""
    if path is None:
        path = os.path.join(SOURCES_DIR, "ca_fsa.geojson")

    print(f"  Validating FSAs: {os.path.basename(path)}")
    with open(path) as f:
        data = json.load(f)
    features = data["features"]

    assert len(features) == 1643, f"Expected 1643 FSA features, got {len(features)}"

    null_geometry_found = set()
    for feat in features:
        props = feat["properties"]
        cfsauid = str(props.get("CFSAUID", ""))
        assert len(cfsauid) == 3, f"Invalid CFSAUID '{cfsauid}': expected 3-char string"
        geom = feat.get("geometry")
        if geom is None:
            null_geometry_found.add(cfsauid)
        else:
            assert geom["type"] in ("Polygon", "MultiPolygon"), (
                f"Invalid geometry type '{geom['type']}' for CFSAUID={cfsauid}"
            )

    if null_geometry_found:
        print(f"    INFO: {len(null_geometry_found)} null-geometry FSAs found: {null_geometry_found}")
    else:
        print(f"    INFO: All {len(features)} FSAs have valid geometry (E2R, J5N, M7A not in census boundary file)")

    print(f"    PASS: {len(features)} FSAs validated")


def validate_us_counties_geoid_format(path=None):
    """
    Regression baseline: verify US county source data has the 0500000US prefix.
    Confirms source format before the merge script strips it. If this fails, the
    source data format changed upstream.
    """
    if path is None:
        path = os.path.join(SOURCES_DIR, "us_county_5m.geojson")

    print(f"  Validating US county GEO_ID format: {os.path.basename(path)}")
    with open(path) as f:
        data = json.load(f)
    features = data["features"]
    prefix_pattern = re.compile(r"^0500000US\d{5}$")

    failures = []
    for feat in features:
        geo_id = feat["properties"].get("GEO_ID", "")
        if not prefix_pattern.match(geo_id):
            name = feat["properties"].get("NAME", "unknown")
            failures.append(f"{name}: GEO_ID='{geo_id}'")

    assert len(failures) == 0, (
        f"{len(failures)} US counties have unexpected GEO_ID format:\n"
        + "\n".join(failures[:20])
    )
    print(f"    PASS: {len(features)} US counties all have 0500000US prefix")


################################################################################
# Merged Output Validators
################################################################################

def validate_merged_state(path=None):
    """Merged state boundaries: STUSPS and COUNTRY on all features."""
    if path is None:
        path = os.path.join(MERGED_DIR, "state_boundaries.geojson")

    print(f"  Validating merged states: {os.path.basename(path)}")
    with open(path) as f:
        data = json.load(f)
    features = data["features"]
    us_count = ca_count = 0

    for feat in features:
        props = feat["properties"]
        country = props.get("COUNTRY", "")
        assert country in ("US", "CA"), f"Missing or invalid COUNTRY: '{country}'"
        stusps = props.get("STUSPS", "")
        assert stusps and len(stusps) == 2, (
            f"Missing or invalid STUSPS: '{stusps}' for COUNTRY={country}"
        )
        if country == "CA":
            assert stusps in VALID_ALPHA2, f"Unknown CA alpha-2 code: '{stusps}'"
            ca_count += 1
        else:
            us_count += 1

    assert us_count == 56, f"Expected 56 US states/territories, got {us_count}"
    assert ca_count == 13, f"Expected 13 CA provinces, got {ca_count}"
    print(f"    PASS: {len(features)} features ({us_count} US, {ca_count} CA)")


def validate_merged_county(path=None):
    """Merged county boundaries: GEO_ID format and COUNTRY."""
    if path is None:
        path = os.path.join(MERGED_DIR, "county_boundaries.geojson")

    print(f"  Validating merged counties: {os.path.basename(path)}")
    with open(path) as f:
        data = json.load(f)
    features = data["features"]
    us_count = ca_count = 0

    for feat in features:
        props = feat["properties"]
        country = props.get("COUNTRY", "")
        assert country in ("US", "CA"), f"Missing or invalid COUNTRY: '{country}'"
        geo_id = props.get("GEO_ID", "")
        if country == "US":
            assert re.match(r"^\d{5}$", geo_id), f"US GEO_ID not 5-digit: '{geo_id}'"
            us_count += 1
        elif country == "CA":
            assert re.match(r"^\d{4}$", geo_id), f"CA GEO_ID not 4-digit: '{geo_id}'"
            ca_count += 1

    assert us_count == 3221, f"Expected 3221 US counties, got {us_count}"
    assert ca_count == 293, f"Expected 293 CA census divisions, got {ca_count}"
    print(f"    PASS: {len(features)} features ({us_count} US, {ca_count} CA)")


def validate_merged_zip(path=None):
    """Merged ZIP boundaries: ZCTA5CE20 format and COUNTRY."""
    if path is None:
        path = os.path.join(MERGED_DIR, "zip_boundaries.geojson")

    print(f"  Validating merged ZIPs: {os.path.basename(path)}")
    with open(path) as f:
        data = json.load(f)
    features = data["features"]
    us_count = ca_count = 0

    for feat in features:
        props = feat["properties"]
        country = props.get("COUNTRY", "")
        assert country in ("US", "CA"), f"Missing or invalid COUNTRY: '{country}'"
        zcta = props.get("ZCTA5CE20", "")
        assert zcta and len(zcta) >= 3, f"Missing or invalid ZCTA5CE20: '{zcta}'"
        if country == "US":
            assert re.match(r"^\d{5}$", zcta), f"US ZCTA5CE20 not 5-digit: '{zcta}'"
            us_count += 1
        elif country == "CA":
            assert re.match(r"^[A-Z]\d[A-Z]$", zcta), (
                f"CA ZCTA5CE20 not valid FSA format: '{zcta}'"
            )
            ca_count += 1

    assert ca_count == 1643, f"Expected 1643 CA FSAs, got {ca_count}"
    print(f"    PASS: {len(features)} features ({us_count} US, {ca_count} CA)")


################################################################################
# Helpers
################################################################################

def _assert_wgs84_bounds(geometry, context):
    """Check that coordinates fall within WGS84 bounds."""
    coords = _extract_coords(geometry)
    for lon, lat in coords[:100]:  # Sample first 100 for performance
        assert -180 <= lon <= 180, f"Longitude {lon} out of WGS84 range for {context}"
        assert -90 <= lat <= 90, f"Latitude {lat} out of WGS84 range for {context}"


def _extract_coords(geometry):
    """Extract (lon, lat) pairs from a geometry object."""
    coords = []
    geom_type = geometry["type"]
    raw = geometry["coordinates"]
    if geom_type == "Polygon":
        for ring in raw:
            coords.extend(ring)
    elif geom_type == "MultiPolygon":
        for polygon in raw:
            for ring in polygon:
                coords.extend(ring)
    elif geom_type == "Point":
        coords.append(raw)
    return coords


################################################################################
# Main
################################################################################

def main():
    parser = argparse.ArgumentParser(description="Validate source/merged GeoJSON.")
    parser.add_argument("--work-dir", default=os.environ.get("TILESET_WORK_DIR"),
                        help="geography data root (or set TILESET_WORK_DIR)")
    parser.add_argument("--sources", action="store_true", help="validate sources only")
    parser.add_argument("--merged", action="store_true", help="validate merged only")
    args = parser.parse_args()

    if not args.work_dir:
        parser.error("--work-dir is required (or set TILESET_WORK_DIR)")

    configure_paths(args.work_dir)

    mode = "all"
    if args.sources:
        mode = "sources"
    elif args.merged:
        mode = "merged"

    source_validators = [
        ("Provinces (CA)", validate_provinces),
        ("Census Divisions (CA)", validate_cd),
        ("FSAs (CA)", validate_fsa),
        ("US County GEO_ID format", validate_us_counties_geoid_format),
    ]
    merged_validators = [
        ("Merged States", validate_merged_state),
        ("Merged Counties", validate_merged_county),
        ("Merged ZIPs", validate_merged_zip),
    ]

    validators = []
    if mode in ("all", "sources"):
        validators.extend(source_validators)
    if mode in ("all", "merged"):
        validators.extend(merged_validators)

    print("================================")
    print("GeoJSON Validation")
    print("================================")

    failures = 0
    total = 0
    for name, validator in validators:
        total += 1
        try:
            validator()
        except FileNotFoundError as e:
            print(f"    SKIP: {name} (file not found: {e})")
        except AssertionError as e:
            print(f"    FAIL: {name}: {e}")
            failures += 1
        except Exception as e:
            print(f"    ERROR: {name}: {e}")
            failures += 1

    print("")
    print(f"Results: {total - failures}/{total} passed")

    if failures > 0:
        print(f"FAILURES: {failures}")
        sys.exit(1)
    else:
        print("All validations passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
