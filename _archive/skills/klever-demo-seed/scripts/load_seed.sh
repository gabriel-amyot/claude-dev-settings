#!/usr/bin/env bash
# Load a STAGED Canadian demo seed into the dev BigQuery consumption tables.
# Backup-first, advertiser-scoped, idempotent, confirm-gated. Run MANUALLY.
#
# Usage:
#   ./load_seed.sh --advertiser-id 842 [--staged-dir .] [--dry-run] [--yes]
#
# Safety brakes:
#   - refuses unless the matching staged ndjson files exist (you can only load
#     data you generated -> can't fat-finger a random advertiser id)
#   - backs up BOTH tables for that advertiser id BEFORE any delete (aborts if backup fails)
#   - DELETE is scoped to that advertiser id only, then load (idempotent re-run)
#   - prints pre-delete row counts and waits for you to type 'yes' (unless --yes)
#   - --dry-run prints every command, runs nothing
set -euo pipefail

PROJECT="prj-d-biz-report-im9q1fvvc7"
DATASET="klever_proximity_data"
ZIP_TABLE="proximity_daily_geo_zip_performance"
COUNTRY_TABLE="proximity_daily_geo_country_performance"
CONVERSION_TABLE="proximity_daily_geo_conversions"

ADV=""; STAGED="."; DRY=0; YES=0
while [ $# -gt 0 ]; do
  case "$1" in
    --advertiser-id) ADV="$2"; shift 2;;
    --staged-dir) STAGED="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    --yes) YES=1; shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

[ -n "$ADV" ] || { echo "ERROR: --advertiser-id required" >&2; exit 2; }
case "$ADV" in (*[!0-9]*) echo "ERROR: advertiser-id must be numeric" >&2; exit 2;; esac

ZIP_FILE="$STAGED/zip_performance_${ADV}.ndjson"
COUNTRY_FILE="$STAGED/country_performance_${ADV}.ndjson"
CONV_FILE="$STAGED/conversions_${ADV}.ndjson"
[ -f "$ZIP_FILE" ] || { echo "ERROR: missing $ZIP_FILE (generate the seed first)" >&2; exit 1; }
[ -f "$COUNTRY_FILE" ] || { echo "ERROR: missing $COUNTRY_FILE (generate the seed first)" >&2; exit 1; }
[ -f "$CONV_FILE" ] || { echo "ERROR: missing $CONV_FILE (regenerate the seed — conversions added)" >&2; exit 1; }

FQ_ZIP="${PROJECT}.${DATASET}.${ZIP_TABLE}"
FQ_COUNTRY="${PROJECT}.${DATASET}.${COUNTRY_TABLE}"
FQ_CONV="${PROJECT}.${DATASET}.${CONVERSION_TABLE}"
TS="$(date +%Y%m%d-%H%M%S)"
BK="$STAGED/backups"

run() { if [ "$DRY" = 1 ]; then echo "DRY  > $*"; else echo "RUN  > $*"; eval "$*"; fi; }

echo "== KTP-728 demo seed load =="
echo "advertiser=$ADV  project=$PROJECT  dataset=$DATASET  staged=$STAGED  dry_run=$DRY"

# 1. show what is there now (read-only)
echo "-- current rows for advertiser $ADV --"
run "bq query --use_legacy_sql=false --format=pretty \
  'SELECT \"zip\" t, COUNT(*) n FROM \`$FQ_ZIP\` WHERE KLEVER_ADVERTISER_ID=$ADV
   UNION ALL SELECT \"country\", COUNT(*) FROM \`$FQ_COUNTRY\` WHERE KLEVER_ADVERTISER_ID=$ADV'"

# 2. confirm gate
if [ "$YES" != 1 ] && [ "$DRY" != 1 ]; then
  printf "Proceed to BACKUP + DELETE + LOAD advertiser %s? type 'yes': " "$ADV"
  read -r ans; [ "$ans" = "yes" ] || { echo "aborted."; exit 0; }
fi

# 3. backup BOTH tables for this advertiser (abort if backup fails)
run "mkdir -p '$BK'"
run "bq query --use_legacy_sql=false --format=prettyjson \
  'SELECT * FROM \`$FQ_ZIP\` WHERE KLEVER_ADVERTISER_ID=$ADV' > '$BK/zip_${ADV}_${TS}.json'"
run "bq query --use_legacy_sql=false --format=prettyjson \
  'SELECT * FROM \`$FQ_COUNTRY\` WHERE KLEVER_ADVERTISER_ID=$ADV' > '$BK/country_${ADV}_${TS}.json'"
run "bq query --use_legacy_sql=false --format=prettyjson \
  'SELECT * FROM \`$FQ_CONV\` WHERE KLEVER_ADVERTISER_ID=$ADV' > '$BK/conversions_${ADV}_${TS}.json'"
echo "backups -> $BK (timestamp $TS)"

# 4. scoped delete (idempotent)
run "bq query --use_legacy_sql=false 'DELETE FROM \`$FQ_ZIP\` WHERE KLEVER_ADVERTISER_ID=$ADV'"
run "bq query --use_legacy_sql=false 'DELETE FROM \`$FQ_COUNTRY\` WHERE KLEVER_ADVERTISER_ID=$ADV'"
run "bq query --use_legacy_sql=false 'DELETE FROM \`$FQ_CONV\` WHERE KLEVER_ADVERTISER_ID=$ADV'"

# 5. load
run "bq load --source_format=NEWLINE_DELIMITED_JSON '${PROJECT}:${DATASET}.${ZIP_TABLE}' '$ZIP_FILE'"
run "bq load --source_format=NEWLINE_DELIMITED_JSON '${PROJECT}:${DATASET}.${COUNTRY_TABLE}' '$COUNTRY_FILE'"
run "bq load --source_format=NEWLINE_DELIMITED_JSON '${PROJECT}:${DATASET}.${CONVERSION_TABLE}' '$CONV_FILE'"

# 6. verify (province gate >= 5, + conversions present)
echo "-- verify --"
run "bq query --use_legacy_sql=false --format=pretty \
  'SELECT COUNT(DISTINCT STATE) provinces, COUNT(*) zip_rows FROM \`$FQ_ZIP\`
   WHERE KLEVER_ADVERTISER_ID=$ADV AND COUNTRY=\"CA\"'"
run "bq query --use_legacy_sql=false --format=pretty \
  'SELECT COUNT(*) conversion_rows, ROUND(SUM(CONVERSION_VALUE),2) conv_value FROM \`$FQ_CONV\`
   WHERE KLEVER_ADVERTISER_ID=$ADV AND COUNTRY=\"CA\"'"
echo "== done. expect provinces >= 5. if not, restore from $BK =="
