#!/bin/bash

################################################################################
# Tileset Preparation Script  (tileset mode: prepare)
################################################################################
# Prepares geographic data (states/provinces, counties/CDs, ZIP/FSA codes) into
# .mbtiles for the front-end map by:
#   0.   Downloading source data (if missing) via download_sources.sh
#   0.5. Merging sources into unified GeoJSON (merge_geojson.py)
#   1.   Generating center points for US and CA polygons separately (mapshaper)
#   1.5. Merging center points with property renames (merge_geojson.py merge-centers)
#   2.   Simplifying merged polygon boundaries (mapshaper)
#   3.   Creating MBTiles tilesets for center points (tippecanoe)
#   4.   Creating MBTiles tilesets for polygon boundaries (tippecanoe)
#
# Ported from prepare_tilesets.sh (KTP-676). Generalized only on --work-dir
# (the geography data root). All outputs go under that committed folder — never
# /tmp. The US+CA pipeline is the proven default.
#
# Prerequisites:
#   - mapshaper:  npm install -g mapshaper
#   - tippecanoe: brew install tippecanoe (macOS) or build from source
#   - gdal (ogr2ogr): brew install gdal (for source download/reprojection)
#   - python3:    for merge/validation scripts
#
# Input files (under <work-dir>/sources/):
#   - us_state.geojson, us_county_5m.geojson
#   - us_zip.geojson (download manually; too large for git)
#   - ca_provinces.geojson, ca_cd.geojson, ca_fsa.geojson (download_sources.sh)
#
# Usage:
#   ./prepare_tilesets.sh --work-dir /path/to/geography
################################################################################

set -e
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --work-dir) WORK_DIR="$2"; shift 2 ;;
        *) echo "ERROR: unknown argument: $1"; exit 1 ;;
    esac
done

if [ -z "${WORK_DIR}" ]; then
    echo "ERROR: --work-dir is required (geography data root)."
    exit 1
fi

WORK_DIR="$(cd "${WORK_DIR}" && pwd)"
export TILESET_WORK_DIR="${WORK_DIR}"

echo "=================================="
echo "Starting Tileset Preparation"
echo "  (US + Canada Merged Pipeline)"
echo "  work-dir: ${WORK_DIR}"
echo "=================================="

################################################################################
# STEP 0: Download Source Data (if missing) — idempotent
################################################################################
echo ""
echo "Step 0: Checking source data..."
echo "-----------------------------------------"

if [ ! -s "${WORK_DIR}/sources/ca_provinces.geojson" ] \
   || [ ! -s "${WORK_DIR}/sources/ca_cd.geojson" ] \
   || [ ! -s "${WORK_DIR}/sources/ca_fsa.geojson" ]; then
    echo "  Canadian source data missing. Running download script..."
    bash "${SCRIPT_DIR}/download_sources.sh" --work-dir "${WORK_DIR}"
else
    echo "  Canadian source data found. Skipping download."
fi

if [ ! -s "${WORK_DIR}/sources/us_zip.geojson" ]; then
    echo ""
    echo "ERROR: sources/us_zip.geojson not found."
    echo "This file is too large for git and must be downloaded manually."
    echo "Download from: https://drive.google.com/drive/folders/1WUNZyG5Ti2yddItWcocyci7yFBZjfYe2?usp=drive_link"
    echo "Place in: ${WORK_DIR}/sources/"
    exit 1
fi

################################################################################
# STEP 0.5: Merge Sources
################################################################################
echo ""
echo "Step 0.5: Merging sources..."
echo "-------------------------------------"
mkdir -p "${WORK_DIR}/merged"
python3 "${SCRIPT_DIR}/merge_geojson.py" --work-dir "${WORK_DIR}"
echo "Done: Merged GeoJSON files in merged/"

################################################################################
# STEP 1: Generate Center Points (US and CA separately)
################################################################################
# Inner points are guaranteed inside the polygon (unlike centroids). The 3
# null-geometry CA FSAs (E2R, J5N, M7A) will not produce centers.
################################################################################
echo ""
echo "Step 1: Generating center points..."
echo "------------------------------------"
mkdir -p "${WORK_DIR}/centers"

echo "  - Generating US state centers..."
mapshaper "${WORK_DIR}/sources/us_state.geojson" -points inner -o "${WORK_DIR}/centers/us_state_centers.geojson"
echo "  - Generating US county centers..."
mapshaper "${WORK_DIR}/sources/us_county_5m.geojson" -points inner -o "${WORK_DIR}/centers/us_county_centers.geojson"
echo "  - Generating US ZIP code centers..."
mapshaper "${WORK_DIR}/sources/us_zip.geojson" -points inner -o "${WORK_DIR}/centers/us_zip_centers.geojson"

echo "  - Generating CA province centers..."
mapshaper "${WORK_DIR}/sources/ca_provinces.geojson" -points inner -o "${WORK_DIR}/centers/ca_province_centers.geojson"
echo "  - Generating CA census division centers..."
mapshaper "${WORK_DIR}/sources/ca_cd.geojson" -points inner -o "${WORK_DIR}/centers/ca_cd_centers.geojson"
echo "  - Generating CA FSA centers (3 null-geometry FSAs will be skipped)..."
mapshaper "${WORK_DIR}/sources/ca_fsa.geojson" -points inner -o "${WORK_DIR}/centers/ca_fsa_centers.geojson" 2>&1 | grep -v "Warning" || true

echo "Done: Center points generated"

################################################################################
# STEP 1.5: Merge Center Points
################################################################################
echo ""
echo "Step 1.5: Merging center points..."
echo "------------------------------------"
python3 "${SCRIPT_DIR}/merge_geojson.py" --work-dir "${WORK_DIR}" merge-centers
echo "Done: Merged center points in merged/"

################################################################################
# STEP 2: Simplify Merged Polygon Boundaries
################################################################################
# Simplification percentages (GAP-5 grill decision):
#   - States: 10% (69 features, trivial)
#   - Counties: 7% (reduced from 10% for Arctic polygon vertex density)
#   - ZIPs: 5% (more detail needed for smaller features)
################################################################################
echo ""
echo "Step 2: Simplifying merged polygon boundaries..."
echo "--------------------------------------------------"
mkdir -p "${WORK_DIR}/boundaries"

echo "  - Simplifying states/provinces (10%)..."
mapshaper "${WORK_DIR}/merged/state_boundaries.geojson" -simplify 10% -o "${WORK_DIR}/boundaries/state_boundaries_simplified.geojson"
echo "  - Simplifying counties/CDs (7%)..."
mapshaper "${WORK_DIR}/merged/county_boundaries.geojson" -simplify 7% -o "${WORK_DIR}/boundaries/county_boundaries_simplified.geojson"
echo "  - Simplifying ZIPs/FSAs (5%)..."
mapshaper "${WORK_DIR}/merged/zip_boundaries.geojson" -simplify 5% -o "${WORK_DIR}/boundaries/zip_boundaries_simplified.geojson"
echo "Done: Merged boundaries simplified"

################################################################################
# STEP 3: Generate MBTiles for Center Points
################################################################################
# Key parameters (CRITICAL for center points — guarantee ALL features at min zoom):
#   --drop-rate=0  --no-feature-limit  --no-tile-size-limit  --force
# Zoom strategy: states Z2-5, counties Z4-6, ZIPs Z6-8.
################################################################################
mkdir -p "${WORK_DIR}/tiles"
echo ""
echo "Step 3: Generating MBTiles for merged center points..."
echo "-------------------------------------------------------"

echo "  - Generating state centers tileset (Z2-5)..."
tippecanoe -o "${WORK_DIR}/tiles/state_centers.mbtiles" -l state_centers_layer -Z2 -z5 \
  --drop-rate=0 --no-feature-limit --no-tile-size-limit --force \
  "${WORK_DIR}/merged/state_centers.geojson"

echo "  - Generating county centers tileset (Z4-6)..."
tippecanoe -o "${WORK_DIR}/tiles/county_centers.mbtiles" -l county_centers_layer -Z4 -z6 \
  --drop-rate=0 --no-feature-limit --no-tile-size-limit --force \
  "${WORK_DIR}/merged/county_centers.geojson"

echo "  - Generating ZIP centers tileset (Z6-8)..."
tippecanoe -o "${WORK_DIR}/tiles/zip_centers.mbtiles" -l zip_centers_layer -Z6 -z8 \
  --drop-rate=0 --no-feature-limit --no-tile-size-limit --force \
  "${WORK_DIR}/merged/zip_centers.geojson"

echo "Done: Center point tilesets generated"

################################################################################
# STEP 4: Generate MBTiles for Polygon Boundaries
################################################################################
# --no-feature-limit guarantees 100% feature completeness at all zoom levels,
# eliminating the "label with no boundary" sync issue. --drop-densest-as-needed
# is kept for documentation intent (no-op under --no-feature-limit).
# Feature IDs: states STATEFP, counties GEO_ID, ZIPs ZCTA5CE20.
################################################################################
echo ""
echo "Step 4: Generating MBTiles for merged polygon boundaries..."
echo "------------------------------------------------------------"

echo "  - Generating state boundaries tileset (Z2-5)..."
tippecanoe -o "${WORK_DIR}/tiles/state_boundaries.mbtiles" -l state_boundaries \
  --use-attribute-for-id=STATEFP -Z2 -z5 \
  --drop-densest-as-needed --no-feature-limit --force \
  "${WORK_DIR}/boundaries/state_boundaries_simplified.geojson"

echo "  - Generating county boundaries tileset (Z4-6)..."
tippecanoe -o "${WORK_DIR}/tiles/county_boundaries.mbtiles" -l county_boundaries \
  --use-attribute-for-id=GEO_ID -Z4 -z6 \
  --drop-densest-as-needed --no-feature-limit --force \
  "${WORK_DIR}/boundaries/county_boundaries_simplified.geojson"

echo "  - Generating ZIP boundaries tileset (Z6-8)..."
tippecanoe -o "${WORK_DIR}/tiles/zip_boundaries.mbtiles" -l zip_boundaries \
  --use-attribute-for-id=ZCTA5CE20 -Z6 -z8 \
  --drop-densest-as-needed --no-feature-limit --force \
  "${WORK_DIR}/boundaries/zip_boundaries_simplified.geojson"

echo "Done: Polygon boundary tilesets generated"

################################################################################
# Completion
################################################################################
echo ""
echo "=================================="
echo "Tileset Preparation Complete!"
echo "=================================="
echo ""
echo "Output: ${WORK_DIR}/tiles/*.mbtiles"
echo ""
echo "Next Steps:"
echo "  1. Validate tiles:   validate_tilesets.py --work-dir ${WORK_DIR}"
echo "  2. GEOID regression: test_geoid_regression.py --work-dir ${WORK_DIR}"
echo "  3. Publish:          hand .mbtiles to mapping:mapbox (mode: upload)"
echo ""
echo "Expected Feature Counts (merged US+CA):"
echo "  - States/Provinces: 69 features (56 US + 13 CA)"
echo "  - Counties/CDs:     3,514 features (3,221 US + 293 CA)"
echo "  - ZIPs/FSAs:        ~43,640 features (~42,000 US + 1,643 CA)"
echo ""
