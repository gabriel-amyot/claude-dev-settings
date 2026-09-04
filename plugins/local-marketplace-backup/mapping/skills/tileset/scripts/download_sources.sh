#!/bin/bash

################################################################################
# Boundary Source Download and Reprojection  (tileset mode: download-sources)
################################################################################
# Downloads census cartographic boundary shapefiles (zipped) and reprojects them
# to WGS84 (EPSG:4326) for Mapbox/tippecanoe compatibility.
#
# Ported from download_canada_sources.sh (KTP-676), generalized:
#   - --work-dir   : geography data root (sources/ written under it). REQUIRED.
#   - --base-url   : base URL the zip files are downloaded from.
#   - --dataset    : "province:lpr_000b21a_e.zip:ca_provinces.geojson:13 provinces"
#                    (repeatable) — colon-delimited zip:output:description triples.
#
# DEFAULT dataset = Statistics Canada 2021 Census Cartographic Boundary Files
# (the proven, working set):
#   - Province/Territory boundaries (lpr_000b21a_e)  -> ca_provinces.geojson (13)
#   - Census Division boundaries    (lcd_000b21a_e)  -> ca_cd.geojson        (293)
#   - Forward Sortation Area bounds (lfsa000b21a_e)  -> ca_fsa.geojson       (1643)
#
# For other regions, pass --base-url and one or more --dataset flags. Source
# URLs for non-Canada regions are intentionally NOT hardcoded: supply them
# explicitly (do not fabricate authoritative download URLs).
#
# Prerequisites:
#   - gdal (provides ogr2ogr): brew install gdal
#   - curl, unzip
#
# Usage (Canada default):
#   ./download_sources.sh --work-dir /path/to/geography
#
# Usage (custom region):
#   ./download_sources.sh --work-dir /path/to/geography \
#     --base-url https://example.gov/boundaries \
#     --dataset state:states.zip:xx_states.geojson:"State boundaries"
################################################################################

set -e
set -u

WORK_DIR=""
BASE_URL="https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers"
DATASETS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --work-dir) WORK_DIR="$2"; shift 2 ;;
        --base-url) BASE_URL="$2"; shift 2 ;;
        --dataset)  DATASETS+=("$2"); shift 2 ;;
        *) echo "ERROR: unknown argument: $1"; exit 1 ;;
    esac
done

if [ -z "${WORK_DIR}" ]; then
    echo "ERROR: --work-dir is required (geography data root; sources/ is written under it)."
    exit 1
fi

# Default to the proven Statistics Canada dataset when none supplied.
if [ ${#DATASETS[@]} -eq 0 ]; then
    DATASETS=(
        "lpr_000b21a_e.zip:ca_provinces.geojson:Province/Territory Boundaries (13 features)"
        "lcd_000b21a_e.zip:ca_cd.geojson:Census Division Boundaries (293 features)"
        "lfsa000b21a_e.zip:ca_fsa.geojson:Forward Sortation Area Boundaries (1,643 features)"
    )
fi

SOURCES_DIR="${WORK_DIR}/sources"
TEMP_DIR="${WORK_DIR}/.tmp_source_download"

echo "=================================="
echo "Boundary Source Download"
echo "=================================="

if ! command -v ogr2ogr &> /dev/null; then
    echo "ERROR: ogr2ogr not found. Install GDAL: brew install gdal"
    exit 1
fi
if ! command -v curl &> /dev/null; then
    echo "ERROR: curl not found."
    exit 1
fi

mkdir -p "${SOURCES_DIR}"
mkdir -p "${TEMP_DIR}"

download_and_reproject() {
    local zip_file="$1"
    local output_file="$2"
    local description="$3"

    echo ""
    echo "--- ${description} ---"

    # Skip download if output already exists and is non-empty (idempotent).
    if [ -s "${SOURCES_DIR}/${output_file}" ]; then
        echo "  Output ${output_file} already exists. Skipping download."
        echo "  Delete ${SOURCES_DIR}/${output_file} to force re-download."
        return 0
    fi

    local zip_path="${TEMP_DIR}/${zip_file}"
    local extract_dir="${TEMP_DIR}/${zip_file%.zip}"

    echo "  Downloading ${zip_file}..."
    curl -sfL -o "${zip_path}" "${BASE_URL}/${zip_file}"

    if [ ! -f "${zip_path}" ] || [ ! -s "${zip_path}" ]; then
        echo "  ERROR: Download failed for ${zip_file}"
        exit 1
    fi

    echo "  Extracting..."
    mkdir -p "${extract_dir}"
    unzip -oq "${zip_path}" -d "${extract_dir}"

    local shp_file
    shp_file=$(find "${extract_dir}" -name "*.shp" -type f | head -1)

    if [ -z "${shp_file}" ]; then
        echo "  ERROR: No .shp file found in ${zip_file}"
        exit 1
    fi

    # Reproject to WGS84 (EPSG:4326). StatsCan shapefiles use Lambert Conformal
    # Conic (NAD83); ogr2ogr handles the transform from the source .prj.
    echo "  Reprojecting to WGS84 (EPSG:4326)..."
    ogr2ogr -f GeoJSON -t_srs EPSG:4326 "${SOURCES_DIR}/${output_file}" "${shp_file}"

    echo "  Output: ${SOURCES_DIR}/${output_file}"
}

for entry in "${DATASETS[@]}"; do
    zip_file="${entry%%:*}"
    rest="${entry#*:}"
    output_file="${rest%%:*}"
    description="${rest#*:}"
    download_and_reproject "${zip_file}" "${output_file}" "${description}"
done

echo ""
echo "--- SHA256 Hashes (record for reproducibility) ---"
for entry in "${DATASETS[@]}"; do
    rest="${entry#*:}"
    output_file="${rest%%:*}"
    if [ -f "${SOURCES_DIR}/${output_file}" ]; then
        shasum -a 256 "${SOURCES_DIR}/${output_file}"
    fi
done

echo ""
echo "Cleaning up temporary files..."
rm -rf "${TEMP_DIR}"

echo ""
echo "=================================="
echo "Source Download Complete"
echo "=================================="
echo ""
echo "Next step: validate-source (validate_geojson.py --sources)"
