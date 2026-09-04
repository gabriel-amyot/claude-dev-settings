#!/usr/bin/env python3
"""
Martin & Tileset Validation Script  (tileset mode: validate-tiles).

Validates produced .mbtiles by serving them with the Martin tile server and
inspecting decoded vector tiles: feature counts, Canadian feature properties
(COUNTRY/STUSPS/GEO_ID/ZCTA5CE20), and boundary/center correspondence.

Ported from validate_tilesets.py (KTP-676). Generalized only on the data root:
pass --work-dir (or set TILESET_WORK_DIR). The US+CA expectations are the proven
default.

Prerequisites:
    pip install requests mapbox-vector-tile
    martin (tile server) on PATH:  cargo install martin

Usage:
    python3 validate_tilesets.py --work-dir /path/to/geography
    python3 validate_tilesets.py --work-dir /path/to/geography --yes   # non-interactive
"""

import argparse
import gzip
import json
import math
import os
import re
import signal
import subprocess
import sys
import time

import requests
import mapbox_vector_tile

# --- Configuration (resolved at runtime) ---
MARTIN_URL = "http://127.0.0.1:3001"
WORK_DIR = ""
TILES_PATH = ""
ASSUME_YES = False

# --- Geo Definitions ---
LOCATIONS = {
    "usa_center": {"lat": 39.8, "lon": -98.6},
    "wa_state": {"lat": 47.7, "lon": -120.7},
    "seattle": {"lat": 47.6, "lon": -122.3},
    "toronto": {"lat": 43.7, "lon": -79.4},
    "montreal": {"lat": 45.5, "lon": -73.6},
}

VALID_CA_ALPHA2 = {
    "NL", "PE", "NS", "NB", "QC", "ON",
    "MB", "SK", "AB", "BC", "YT", "NT", "NU",
}

# FSAs that may have no geometry in some Stats Canada editions. The 2021
# cartographic boundary file includes geometry for all 1,643 FSAs, so this set
# may be empty in practice. Kept for forward compatibility.
KNOWN_NULL_GEOMETRY_FSAS = {"E2R", "J5N", "M7A"}


def configure_paths(work_dir):
    global WORK_DIR, TILES_PATH
    WORK_DIR = os.path.abspath(work_dir)
    TILES_PATH = os.path.join(WORK_DIR, "tiles")


def _src(name):
    return os.path.join(WORK_DIR, "sources", name)


def _ctr(name):
    return os.path.join(WORK_DIR, "centers", name)


# --- Helper Functions ---

def validate_boundaries_have_centers():
    """Validate that every boundary polygon has a corresponding center point."""
    print("\n" + "=" * 80)
    print("VALIDATING BOUNDARIES vs CENTERS MATCH")
    print("=" * 80)

    validation_configs = [
        {'name': 'US States', 'boundary_file': _src('us_state.geojson'),
         'centers_file': _ctr('us_state_centers.geojson'), 'id_field': 'STUSPS'},
        {'name': 'US Counties', 'boundary_file': _src('us_county_5m.geojson'),
         'centers_file': _ctr('us_county_centers.geojson'), 'id_field': 'GEO_ID'},
        {'name': 'ZIP Codes', 'boundary_file': _src('us_zip.geojson'),
         'centers_file': _ctr('us_zip_centers.geojson'), 'id_field': 'ZCTA5CE20'},
        {'name': 'CA Provinces', 'boundary_file': _src('ca_provinces.geojson'),
         'centers_file': _ctr('ca_province_centers.geojson'), 'id_field': 'PRUID'},
        {'name': 'CA Census Divisions', 'boundary_file': _src('ca_cd.geojson'),
         'centers_file': _ctr('ca_cd_centers.geojson'), 'id_field': 'CDUID'},
        {'name': 'CA FSAs', 'boundary_file': _src('ca_fsa.geojson'),
         'centers_file': _ctr('ca_fsa_centers.geojson'), 'id_field': 'CFSAUID'},
    ]

    all_passed = True

    for config in validation_configs:
        print(f"\n--- {config['name']} ---")
        try:
            with open(config['boundary_file'], 'r') as f:
                boundary_data = json.load(f)
            boundary_ids = set()
            geometry_issues = []

            for feature in boundary_data['features']:
                feature_id = feature['properties'].get(config['id_field'])
                if feature_id:
                    boundary_ids.add(str(feature_id))
                    geom = feature.get('geometry')
                    if geom is not None and geom['type'] == 'GeometryCollection':
                        geometry_issues.append({
                            'id': feature_id,
                            'name': feature['properties'].get('NAME', 'Unknown'),
                            'type': geom['type'],
                        })

            with open(config['centers_file'], 'r') as f:
                centers_data = json.load(f)
            center_ids = set()
            for feature in centers_data['features']:
                feature_id = feature['properties'].get(config['id_field'])
                if feature_id:
                    center_ids.add(str(feature_id))

            missing_centers = boundary_ids - center_ids
            extra_centers = center_ids - boundary_ids

            if config['name'] == 'CA FSAs':
                expected_missing = missing_centers & KNOWN_NULL_GEOMETRY_FSAS
                if expected_missing:
                    print(f"NOTE: {len(expected_missing)} null-geometry FSAs correctly excluded from centers: {sorted(expected_missing)}")
                    missing_centers = missing_centers - KNOWN_NULL_GEOMETRY_FSAS

            print(f"Boundaries: {len(boundary_ids)} features")
            print(f"Centers: {len(center_ids)} features")

            if missing_centers:
                all_passed = False
                print(f"\nFAIL: {len(missing_centers)} boundaries are MISSING center points:")
                for missing_id in sorted(missing_centers):
                    name = "Unknown"
                    for feature in boundary_data['features']:
                        if str(feature['properties'].get(config['id_field'])) == missing_id:
                            name = feature['properties'].get('NAME', 'Unknown')
                            break
                    print(f"   - {config['id_field']}={missing_id} ({name})")
            else:
                print("PASS: All boundaries have corresponding center points")

            if extra_centers:
                print(f"\nWARNING: {len(extra_centers)} centers have no corresponding boundary:")
                for extra_id in sorted(extra_centers)[:10]:
                    print(f"   - {config['id_field']}={extra_id}")
                if len(extra_centers) > 10:
                    print(f"   ... and {len(extra_centers) - 10} more")

            if geometry_issues:
                print(f"\nGEOMETRY ISSUES: {len(geometry_issues)} features have GeometryCollection type:")
                print("   (mapshaper -points inner may fail on these)")
                for issue in geometry_issues:
                    print(f"   - {config['id_field']}={issue['id']} ({issue['name']}) - Type: {issue['type']}")
                print("\n   FIX: Use mapshaper -explode before -points inner")

        except FileNotFoundError as e:
            print(f"ERROR: File not found - {e}")
            all_passed = False
        except Exception as e:
            print(f"ERROR: {e}")
            all_passed = False

    print("\n" + "=" * 80)
    return all_passed


def deg2num(lat_deg, lon_deg, zoom):
    """Convert lat/lon to tile coordinates."""
    lat_rad = math.radians(lat_deg)
    if zoom is None:
        raise ValueError("zoom value is None")
    try:
        n = 2.0 ** float(zoom)
    except Exception:
        raise ValueError(f"invalid zoom value: {zoom}")
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def inspect_tile(tileset, z, x, y, description):
    """Fetch, decode, and print features from a single tile."""
    tile_url = f"{MARTIN_URL}/{tileset}/{z}/{x}/{y}"
    print(f"      - Fetching {description} tile: {tile_url}")
    try:
        response = requests.get(tile_url)
        if response.status_code == 404:
            print("        - Tile not found (404). Might be expected for areas with no data.")
            return 0
        response.raise_for_status()
        if response.status_code == 204:
            print("        - Success (204 No Content): Tile is empty.")
            return 0

        tile_data = response.content
        try:
            tile_data = gzip.decompress(tile_data)
        except Exception:
            pass

        decoded_tile = mapbox_vector_tile.decode(tile_data)
        total_features = 0
        for layer_name, layer in decoded_tile.items():
            num_features = len(layer["features"])
            total_features += num_features
            print(f"        - Layer '{layer_name}' | {num_features} features found:")
            for feature in layer["features"]:
                props = feature.get("properties", {})
                print(f"          - Feature | ID: {feature.get('id', 'N/A')} | Properties: {props}")

        if total_features == 0:
            print("        - Success: Tile received but contained no features.")
        return total_features

    except requests.exceptions.RequestException as e:
        print(f"        - Failure: Could not fetch tile. {e}")
    except Exception as e:
        print(f"        - Failure: Could not decode tile. {e}")
    return 0


def validate_canadian_features(tileset_name, zoom, location_key="toronto"):
    """Validate that Canadian features have correct properties at a location."""
    print(f"\n   -> Canadian feature validation at {location_key} (zoom {zoom})...")
    loc = LOCATIONS[location_key]
    x, y = deg2num(loc["lat"], loc["lon"], zoom)
    tile_url = f"{MARTIN_URL}/{tileset_name}/{zoom}/{x}/{y}"

    try:
        response = requests.get(tile_url)
        if response.status_code != 200:
            print(f"      FAIL: Got status {response.status_code} for {tile_url}")
            return False

        tile_data = response.content
        try:
            tile_data = gzip.decompress(tile_data)
        except Exception:
            pass

        decoded_tile = mapbox_vector_tile.decode(tile_data)
        ca_features = []
        for layer_name, layer in decoded_tile.items():
            for feature in layer["features"]:
                props = feature.get("properties", {})
                if props.get("COUNTRY") == "CA":
                    ca_features.append(props)

        if not ca_features:
            print(f"      FAIL: No CA features found at {location_key}")
            return False

        print(f"      Found {len(ca_features)} CA feature(s)")

        passed = True
        for props in ca_features:
            if props.get("COUNTRY") != "CA":
                print(f"      FAIL: COUNTRY != 'CA': {props}")
                passed = False

            if "state" in tileset_name:
                stusps = props.get("STUSPS", "")
                if stusps not in VALID_CA_ALPHA2:
                    print(f"      FAIL: Invalid STUSPS '{stusps}' for CA feature")
                    passed = False
                else:
                    print(f"      PASS: Province STUSPS={stusps}")
            elif "county" in tileset_name:
                geo_id = str(props.get("GEO_ID", ""))
                if not re.match(r'^\d{4}$', geo_id):
                    print(f"      FAIL: CA GEO_ID not 4-digit: '{geo_id}'")
                    passed = False
                else:
                    print(f"      PASS: CD GEO_ID={geo_id}")
            elif "zip" in tileset_name:
                zcta = str(props.get("ZCTA5CE20", ""))
                if not re.match(r'^[A-Z]\d[A-Z]$', zcta):
                    print(f"      FAIL: CA ZCTA5CE20 not FSA format: '{zcta}'")
                    passed = False
                else:
                    print(f"      PASS: FSA ZCTA5CE20={zcta}")

        return passed

    except Exception as e:
        print(f"      ERROR: {e}")
        return False


def main():
    print("=================================")
    print("Martin & Tileset Validation Script")
    print("  (US + Canada Merged Tilesets)")
    print("=================================")

    print("\n0. Validating GeoJSON source files (boundaries vs centers)...")
    boundaries_valid = validate_boundaries_have_centers()

    if not boundaries_valid:
        print("\nWARNING: Boundary/Center mismatches detected!")
        print("The tileset validation will continue, but you should fix the source data first.")
        if ASSUME_YES:
            print("--yes set: continuing.")
        else:
            response = input("\nContinue with tileset validation anyway? (y/n): ")
            if response.lower() != 'y':
                print("Validation aborted by user.")
                return

    validation_results = []
    martin_process = None
    try:
        print(f"\n1. Starting Martin server for path: {TILES_PATH}...")
        command = ["martin", TILES_PATH, "--listen-addresses", "0.0.0.0:3001"]
        martin_process = subprocess.Popen(command, preexec_fn=os.setsid)

        print("\n2. Waiting for Martin server to respond...")
        for i in range(20):
            try:
                resp = requests.get(f"{MARTIN_URL}/catalog")
                if resp.status_code == 200:
                    print("   Martin is running.")
                    break
            except requests.ConnectionError:
                pass
            time.sleep(0.5)
        else:
            print("   Martin server did not start in time. Aborting.")
            sys.exit(1)

        print("\n3. Fetching available tilesets...")
        tilesets = requests.get(f"{MARTIN_URL}/catalog").json()["tiles"]
        print(f"   Found {len(tilesets)} tilesets.")

        print("\n4. Running specific validation tests...")
        for tileset, meta in tilesets.items():
            print(f"   ---------------------------------")
            print(f"   Validating tileset: {tileset}")

            if tileset.startswith("state_"):
                print("   -> State/Province test (centered on USA)")
                x, y = deg2num(LOCATIONS["usa_center"]["lat"], LOCATIONS["usa_center"]["lon"], 2)
                inspect_tile(tileset, 2, x, y, "zoom 2")
                x, y = deg2num(LOCATIONS["usa_center"]["lat"], LOCATIONS["usa_center"]["lon"], 5)
                inspect_tile(tileset, 5, x, y, "zoom 5")
                if "boundaries" in tileset:
                    validate_canadian_features(tileset, 3, "toronto")
            elif tileset.startswith("county_"):
                print("   -> County/CD test (centered on USA)")
                x, y = deg2num(LOCATIONS["usa_center"]["lat"], LOCATIONS["usa_center"]["lon"], 4)
                inspect_tile(tileset, 4, x, y, "zoom 4")
                x, y = deg2num(LOCATIONS["usa_center"]["lat"], LOCATIONS["usa_center"]["lon"], 6)
                inspect_tile(tileset, 6, x, y, "zoom 6")
                if "boundaries" in tileset:
                    validate_canadian_features(tileset, 5, "toronto")
            elif tileset.startswith("zip_"):
                print("   -> ZIP/FSA test (centered on Seattle)")
                x, y = deg2num(LOCATIONS["seattle"]["lat"], LOCATIONS["seattle"]["lon"], 6)
                inspect_tile(tileset, 6, x, y, "zoom 6 (min zoom)")
                x, y = deg2num(LOCATIONS["seattle"]["lat"], LOCATIONS["seattle"]["lon"], 8)
                inspect_tile(tileset, 8, x, y, "zoom 8 (max zoom)")
                if "boundaries" in tileset:
                    validate_canadian_features(tileset, 7, "montreal")
            elif "us_dma_" in tileset:
                print("   -> DMA test (legacy, unchanged)")
                x, y = deg2num(LOCATIONS["usa_center"]["lat"], LOCATIONS["usa_center"]["lon"], 4)
                inspect_tile(tileset, 4, x, y, "zoom 4")
            else:
                print("   -> No specific test defined for this tileset type.")

        print("\n5. CRITICAL VALIDATION: Checking ALL center points are available at min zoom...")
        print("   (This validates the tippecanoe --no-feature-limit setting)")

        center_tilesets = {
            "state_centers": {"min_zoom": 2, "expected_features": 69, "name": "States + Provinces"},
            "county_centers": {"min_zoom": 4, "expected_features": 3514, "name": "Counties + CDs"},
            "zip_centers": {"min_zoom": 6, "expected_features": 43000, "name": "ZIPs + FSAs"},
        }

        for tileset_name, config in center_tilesets.items():
            if tileset_name not in tilesets:
                print(f"\n   Skipping '{tileset_name}' - not found in catalog")
                continue

            print(f"\n   ---------------------------------")
            print(f"   Validating: {tileset_name} ({config['name']})")
            print(f"   Min zoom: {config['min_zoom']} | Expected features: ~{config['expected_features']}")

            min_zoom = config['min_zoom']
            total_features = 0
            non_empty_tiles = 0
            tiles_at_zoom = 2 ** min_zoom

            print(f"   Scanning all {tiles_at_zoom * tiles_at_zoom} tiles at zoom {min_zoom}...")
            for x in range(tiles_at_zoom):
                for y in range(tiles_at_zoom):
                    features_in_tile = inspect_tile(tileset_name, min_zoom, x, y, f"tile {min_zoom}/{x}/{y}")
                    if features_in_tile > 0:
                        total_features += features_in_tile
                        non_empty_tiles += 1

            print(f"\n   RESULTS for '{tileset_name}':")
            print(f"   - Total features found: {total_features}")
            print(f"   - Non-empty tiles: {non_empty_tiles}/{tiles_at_zoom * tiles_at_zoom}")

            expected = config['expected_features']
            passed = False
            if tileset_name == "zip_centers":
                if total_features > 40000:
                    print(f"   - PASS: Feature count is in expected range (40k+)")
                    passed = True
                else:
                    print(f"   - FAIL: Only {total_features} features found, expected ~{expected}")
                    print(f"   - ACTION NEEDED: Regenerate with proper tippecanoe flags")
            else:
                tolerance = expected * 0.1
                if abs(total_features - expected) <= tolerance:
                    print(f"   - PASS: Feature count matches expected range")
                    passed = True
                else:
                    print(f"   - FAIL: Expected ~{expected}, found {total_features}")
                    print(f"   - ACTION NEEDED: Regenerate with proper tippecanoe flags")

            validation_results.append({
                'tileset': tileset_name, 'name': config['name'], 'min_zoom': min_zoom,
                'expected': expected, 'found': total_features, 'passed': passed,
                'tiles_checked': tiles_at_zoom * tiles_at_zoom, 'non_empty_tiles': non_empty_tiles,
            })

    finally:
        if martin_process:
            print("\n6. Shutting down Martin server...")
            os.killpg(os.getpgid(martin_process.pid), signal.SIGTERM)
            martin_process.wait()
            print("   Server shut down.")

        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        if validation_results:
            passed_count = sum(1 for r in validation_results if r['passed'])
            failed_count = len(validation_results) - passed_count
            print(f"\nOverall Results: {passed_count} PASSED, {failed_count} FAILED\n")

            for result in validation_results:
                status = "PASS" if result['passed'] else "FAIL"
                print(f"{status} | {result['tileset']}")
                print(f"   Name: {result['name']}")
                print(f"   Min Zoom: {result['min_zoom']}")
                print(f"   Expected Features: ~{result['expected']:,}")
                print(f"   Found Features: {result['found']:,}")
                print(f"   Tiles Scanned: {result['tiles_checked']} ({result['non_empty_tiles']} non-empty)")
                if not result['passed']:
                    percentage = (result['found'] / result['expected']) * 100 if result['expected'] > 0 else 0
                    print(f"   Only {percentage:.1f}% of expected features found!")
                    print(f"   ACTION: Regenerate tiles with --drop-rate=0 flag")
                print()

            print("=" * 80)
            if failed_count > 0:
                print("FAILURES DETECTED - Tiles need regeneration with correct flags")
            else:
                print("All validations passed! Tiles are correctly configured.")
            print("=" * 80)
        else:
            print("No validation results to display.")

        print("\nValidation complete.")
        print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate produced .mbtiles via Martin.")
    parser.add_argument("--work-dir", default=os.environ.get("TILESET_WORK_DIR"),
                        help="geography data root (or set TILESET_WORK_DIR)")
    parser.add_argument("--yes", action="store_true",
                        help="non-interactive: continue past boundary/center mismatches")
    args = parser.parse_args()
    if not args.work_dir:
        parser.error("--work-dir is required (or set TILESET_WORK_DIR)")
    configure_paths(args.work_dir)
    ASSUME_YES = args.yes

    try:
        main()
    except ImportError as e:
        print(f"\nError: Missing required Python library. ({e})")
        print("Install dependencies: pip install requests mapbox-vector-tile")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: 'martin' command not found.")
        print("Ensure the Martin tile server is installed and on PATH (cargo install martin).")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
