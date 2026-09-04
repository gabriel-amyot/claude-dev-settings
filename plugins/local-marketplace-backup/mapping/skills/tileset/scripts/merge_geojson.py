#!/usr/bin/env python3
"""
US + Canada GeoJSON Merge Script  (tileset mode: merge).

Merges US and Canadian geographic data into unified GeoJSON files with
standardized property naming. Adds a COUNTRY discriminator to all features.

Ported from merge_geojson.py (KTP-676). The only generalization is the data
root: pass --work-dir (or set TILESET_WORK_DIR) to point at the geography data
folder. sources/, merged/, centers/ and pruid_to_alpha2.json are resolved
relative to that root. The US+CA merge logic is the proven default and is kept
intact.

Property rename conventions (Canadian to US):
  - Province PRUID -> STUSPS (alpha-2 code via pruid_to_alpha2.json)
  - CD CDUID -> GEO_ID (clean 4-digit)
  - FSA CFSAUID -> ZCTA5CE20 (3-char code)

US county GEO_ID prefix stripping:
  - 0500000US36061 -> 36061 (clean 5-digit FIPS)

Usage:
    python3 merge_geojson.py --work-dir /path/to/geography                 # boundaries
    python3 merge_geojson.py --work-dir /path/to/geography merge-centers   # centers
"""

import argparse
import copy
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Google Drive URL for us_zip.geojson (too large for git)
US_ZIP_DOWNLOAD_URL = "https://drive.google.com/drive/folders/1WUNZyG5Ti2yddItWcocyci7yFBZjfYe2?usp=drive_link"

# Resolved at runtime from --work-dir / TILESET_WORK_DIR.
SOURCES_DIR = ""
MERGED_DIR = ""
CENTERS_DIR = ""
PRUID_LOOKUP_PATH = ""


def configure_paths(work_dir):
    """Resolve all data directories relative to the geography data root."""
    global SOURCES_DIR, MERGED_DIR, CENTERS_DIR, PRUID_LOOKUP_PATH
    work_dir = os.path.abspath(work_dir)
    SOURCES_DIR = os.path.join(work_dir, "sources")
    MERGED_DIR = os.path.join(work_dir, "merged")
    CENTERS_DIR = os.path.join(work_dir, "centers")
    # Prefer a lookup in the work dir; fall back to the one bundled with the skill.
    candidate = os.path.join(work_dir, "pruid_to_alpha2.json")
    PRUID_LOOKUP_PATH = candidate if os.path.exists(candidate) else os.path.join(
        SCRIPT_DIR, "pruid_to_alpha2.json"
    )


def load_pruid_lookup(path=None):
    """Load PRUID-to-alpha-2 mapping from JSON file."""
    if path is None:
        path = PRUID_LOOKUP_PATH
    with open(path) as f:
        return json.load(f)


def strip_us_county_geoid_prefix(geoid):
    """
    Strip '0500000US' prefix from US county GEO_ID.

    Input:  '0500000US36061'  Output: '36061'

    The regex is intentionally narrow: the ^ anchor ensures it only matches at
    the start, and the literal '0500000US' matches only the Census Bureau county
    prefix format. It will not match state-level (0400000US) or tract-level
    (1400000US) prefixes.
    """
    return re.sub(r'^0500000US', '', geoid)


def add_country_property(feature, country):
    """Add COUNTRY property to a feature. Returns a new feature (no mutation)."""
    new_feat = copy.deepcopy(feature)
    new_feat["properties"]["COUNTRY"] = country
    return new_feat


def _load_geojson(path, description=""):
    """Load a GeoJSON file with clear error messaging."""
    if not os.path.exists(path):
        filename = os.path.basename(path)
        if filename == "us_zip.geojson":
            print(f"ERROR: {filename} not found at {path}")
            print(f"This file is too large for git and must be downloaded manually.")
            print(f"Download from: {US_ZIP_DOWNLOAD_URL}")
            print(f"Place in: {SOURCES_DIR}/")
            sys.exit(1)
        raise FileNotFoundError(f"{description} not found: {path}")

    with open(path) as f:
        return json.load(f)


def _write_geojson(data, path):
    """Write GeoJSON to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
    feature_count = len(data.get("features", []))
    print(f"    Wrote {feature_count} features to {os.path.basename(path)}")


def merge_states(us_path=None, ca_path=None, pruid_lookup=None, output_path=None):
    """
    Merge US states + CA provinces.

    US features: add COUNTRY='US', keep all existing properties.
    CA features: add COUNTRY='CA', add STUSPS from PRUID lookup.

    Output: merged GeoJSON with 56 US + 13 CA = 69 features.
    """
    if us_path is None:
        us_path = os.path.join(SOURCES_DIR, "us_state.geojson")
    if ca_path is None:
        ca_path = os.path.join(SOURCES_DIR, "ca_provinces.geojson")
    if pruid_lookup is None:
        pruid_lookup = load_pruid_lookup()
    if output_path is None:
        output_path = os.path.join(MERGED_DIR, "state_boundaries.geojson")

    print("  Merging states (US + CA provinces)...")

    us_data = _load_geojson(us_path, "US states")
    ca_data = _load_geojson(ca_path, "CA provinces")

    merged_features = []

    for feat in us_data["features"]:
        merged_features.append(add_country_property(feat, "US"))

    for feat in ca_data["features"]:
        new_feat = add_country_property(feat, "CA")
        pruid = str(new_feat["properties"].get("PRUID", ""))
        alpha2 = pruid_lookup.get(pruid)
        if alpha2 is None:
            print(f"    WARNING: No alpha-2 code for PRUID={pruid}")
            alpha2 = pruid
        new_feat["properties"]["STUSPS"] = alpha2
        merged_features.append(new_feat)

    merged = {"type": "FeatureCollection", "features": merged_features}
    _write_geojson(merged, output_path)
    return merged


def merge_counties(us_path=None, ca_path=None, output_path=None):
    """
    Merge US counties + CA census divisions.

    US features: add COUNTRY='US', STRIP GEO_ID prefix (0500000US36061 -> 36061).
    CA features: add COUNTRY='CA', rename CDUID -> GEO_ID.

    Output: merged GeoJSON with 3221 US + 293 CA = 3514 features.
    """
    if us_path is None:
        us_path = os.path.join(SOURCES_DIR, "us_county_5m.geojson")
    if ca_path is None:
        ca_path = os.path.join(SOURCES_DIR, "ca_cd.geojson")
    if output_path is None:
        output_path = os.path.join(MERGED_DIR, "county_boundaries.geojson")

    print("  Merging counties (US + CA census divisions)...")

    us_data = _load_geojson(us_path, "US counties")
    ca_data = _load_geojson(ca_path, "CA census divisions")

    merged_features = []

    for feat in us_data["features"]:
        new_feat = add_country_property(feat, "US")
        raw_geoid = new_feat["properties"].get("GEO_ID", "")
        new_feat["properties"]["GEO_ID"] = strip_us_county_geoid_prefix(raw_geoid)
        merged_features.append(new_feat)

    for feat in ca_data["features"]:
        new_feat = add_country_property(feat, "CA")
        cduid = str(new_feat["properties"].get("CDUID", ""))
        new_feat["properties"]["GEO_ID"] = cduid
        merged_features.append(new_feat)

    merged = {"type": "FeatureCollection", "features": merged_features}
    _write_geojson(merged, output_path)
    return merged


def merge_zips(us_path=None, ca_path=None, output_path=None):
    """
    Merge US ZCTAs + CA FSAs.

    US features: add COUNTRY='US', keep ZCTA5CE20 as-is.
    CA features: add COUNTRY='CA', rename CFSAUID -> ZCTA5CE20.

    Output: merged GeoJSON with ~42000 US + 1643 CA features.
    """
    if us_path is None:
        us_path = os.path.join(SOURCES_DIR, "us_zip.geojson")
    if ca_path is None:
        ca_path = os.path.join(SOURCES_DIR, "ca_fsa.geojson")
    if output_path is None:
        output_path = os.path.join(MERGED_DIR, "zip_boundaries.geojson")

    print("  Merging ZIPs (US ZCTAs + CA FSAs)...")

    us_data = _load_geojson(us_path, "US ZCTAs")
    ca_data = _load_geojson(ca_path, "CA FSAs")

    merged_features = []

    for feat in us_data["features"]:
        merged_features.append(add_country_property(feat, "US"))

    for feat in ca_data["features"]:
        new_feat = add_country_property(feat, "CA")
        cfsauid = str(new_feat["properties"].get("CFSAUID", ""))
        new_feat["properties"]["ZCTA5CE20"] = cfsauid
        merged_features.append(new_feat)

    merged = {"type": "FeatureCollection", "features": merged_features}
    _write_geojson(merged, output_path)
    return merged


def merge_all():
    """Orchestrator: run all three boundary merges."""
    print("================================")
    print("Merging US + CA Boundaries")
    print("================================")

    pruid_lookup = load_pruid_lookup()
    merge_states(pruid_lookup=pruid_lookup)
    merge_counties()
    merge_zips()

    print("")
    print("Boundary merge complete.")
    print(f"Output in: {MERGED_DIR}/")


def merge_centers_pair(us_centers_path, ca_centers_path, output_path,
                       layer_name, property_transform=None):
    """
    Merge a US + CA center point GeoJSON pair.

    property_transform: optional function(feature, country) -> feature applying
    the same property renames as the boundary merge.
    """
    print(f"  Merging centers: {layer_name}...")

    us_data = _load_geojson(us_centers_path, f"US {layer_name} centers")
    ca_data = _load_geojson(ca_centers_path, f"CA {layer_name} centers")

    merged_features = []

    for feat in us_data["features"]:
        new_feat = add_country_property(feat, "US")
        if property_transform:
            new_feat = property_transform(new_feat, "US")
        merged_features.append(new_feat)

    for feat in ca_data["features"]:
        new_feat = add_country_property(feat, "CA")
        if property_transform:
            new_feat = property_transform(new_feat, "CA")
        merged_features.append(new_feat)

    merged = {"type": "FeatureCollection", "features": merged_features}
    _write_geojson(merged, output_path)
    return merged


def _transform_state_centers(feature, country):
    """Apply state/province property transforms to center points."""
    if country == "CA":
        if not hasattr(_transform_state_centers, '_cache'):
            _transform_state_centers._cache = load_pruid_lookup()
        pruid_lookup = _transform_state_centers._cache
        pruid = str(feature["properties"].get("PRUID", ""))
        alpha2 = pruid_lookup.get(pruid, pruid)
        feature["properties"]["STUSPS"] = alpha2
    return feature


def _transform_county_centers(feature, country):
    """Apply county/CD property transforms to center points."""
    if country == "US":
        raw_geoid = feature["properties"].get("GEO_ID", "")
        feature["properties"]["GEO_ID"] = strip_us_county_geoid_prefix(raw_geoid)
    elif country == "CA":
        cduid = str(feature["properties"].get("CDUID", ""))
        feature["properties"]["GEO_ID"] = cduid
    return feature


def _transform_zip_centers(feature, country):
    """Apply ZIP/FSA property transforms to center points."""
    if country == "CA":
        cfsauid = str(feature["properties"].get("CFSAUID", ""))
        feature["properties"]["ZCTA5CE20"] = cfsauid
    return feature


def merge_all_centers():
    """Merge all center point pairs."""
    print("")
    print("================================")
    print("Merging US + CA Center Points")
    print("================================")

    merge_centers_pair(
        os.path.join(CENTERS_DIR, "us_state_centers.geojson"),
        os.path.join(CENTERS_DIR, "ca_province_centers.geojson"),
        os.path.join(MERGED_DIR, "state_centers.geojson"),
        "state",
        property_transform=_transform_state_centers,
    )
    merge_centers_pair(
        os.path.join(CENTERS_DIR, "us_county_centers.geojson"),
        os.path.join(CENTERS_DIR, "ca_cd_centers.geojson"),
        os.path.join(MERGED_DIR, "county_centers.geojson"),
        "county",
        property_transform=_transform_county_centers,
    )
    merge_centers_pair(
        os.path.join(CENTERS_DIR, "us_zip_centers.geojson"),
        os.path.join(CENTERS_DIR, "ca_fsa_centers.geojson"),
        os.path.join(MERGED_DIR, "zip_centers.geojson"),
        "zip",
        property_transform=_transform_zip_centers,
    )

    print("")
    print("Center merge complete.")
    print(f"Output in: {MERGED_DIR}/")


def main():
    parser = argparse.ArgumentParser(description="Merge US + CA GeoJSON sources.")
    parser.add_argument("subcommand", nargs="?", default="merge",
                        choices=["merge", "merge-centers"],
                        help="merge boundaries (default) or merge-centers")
    parser.add_argument("--work-dir", default=os.environ.get("TILESET_WORK_DIR"),
                        help="geography data root (or set TILESET_WORK_DIR)")
    args = parser.parse_args()

    if not args.work_dir:
        parser.error("--work-dir is required (or set TILESET_WORK_DIR)")

    configure_paths(args.work_dir)

    if args.subcommand == "merge-centers":
        merge_all_centers()
    else:
        merge_all()


if __name__ == "__main__":
    main()
