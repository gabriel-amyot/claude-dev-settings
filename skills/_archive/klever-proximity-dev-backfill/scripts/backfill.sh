#!/usr/bin/env bash
# klever-proximity-dev-backfill
# Copy proximity geo-performance rows for one or more advertisers from PROD BQ
# into DEV BQ, so the Measurement Map renders for them on portal.dev.
# STOPGAP — not a pipeline fix. See SKILL.md for the root cause + caveats.
#
# Modes (default is the SAFE read-only verify):
#   backfill.sh 326 27 407            # VERIFY only (read-only) — shows dev counts
#   backfill.sh --verify 326 27       # same, explicit
#   backfill.sh --apply 326 27 407    # WRITE: replace these advertisers' rows in dev
#   backfill.sh --reverse 326 27 407  # WRITE: delete these advertisers from dev (undo)
#
# Safety properties:
#   - Default mode does NOT write. You must pass --apply to mutate dev.
#   - --apply is IDEMPOTENT: it DELETEs the advertiser's rows in dev, then inserts,
#     so re-running never duplicates (and self-heals a prior double-run).
#   - Column-name-matched INSERT (not SELECT *): aborts on prod/dev schema drift
#     instead of silently shifting data into the wrong columns.
#   - Advertiser IDs are validated as integers (no SQL injection / accidental dump-all).
#   - --apply writes a pre-state backup file before touching anything.
#
# Requires: bq CLI authenticated with read on PROD and dataEditor on DEV.
set -euo pipefail

PROD=${PROXIMITY_PROD_PROJECT:-prj-p-biz-report-fo53kywlio}
DEV=${PROXIMITY_DEV_PROJECT:-prj-d-biz-report-im9q1fvvc7}
DS=klever_proximity_data
BACKUP_DIR=${BACKFILL_BACKUP_DIR:-$PWD}
TABLES=(proximity_daily_geo_zip_performance \
        proximity_daily_geo_country_performance \
        proximity_daily_geo_conversions)

MODE=verify
case "${1:-}" in
  --verify)  MODE=verify;  shift ;;
  --apply)   MODE=apply;   shift ;;
  --reverse) MODE=reverse; shift ;;
  --*) echo "error: unknown flag '$1'" >&2; exit 2 ;;
esac

[ "$#" -ge 1 ] || { echo "error: pass one or more KLEVER_ADVERTISER_IDs (integers)" >&2; exit 2; }
for id in "$@"; do
  [[ "$id" =~ ^[0-9]+$ ]] || { echo "error: '$id' is not a valid integer advertiser id" >&2; exit 2; }
done
ADV=$(IFS=,; echo "$*")   # "326 27 407" -> "326,27,407"

bq_q() { bq query --use_legacy_sql=false --project_id="$DEV" "$@"; }

# Ordered, pipe-joined column names for a table (pipe avoids CSV comma-quoting).
col_list() {  # $1=project $2=table -> "COL_A|COL_B|..."
  bq_q --format=csv \
    "SELECT STRING_AGG(column_name, '|' ORDER BY ordinal_position)
     FROM \`$1.$DS.INFORMATION_SCHEMA.COLUMNS\` WHERE table_name='$2'" | tail -1
}

counts() {  # $1=project
  for T in "${TABLES[@]}"; do
    echo "--- $1.$DS.$T ---"
    bq_q --format=csv \
      "SELECT KLEVER_ADVERTISER_ID, COUNT(*) c FROM \`$1.$DS.$T\`
       WHERE KLEVER_ADVERTISER_ID IN (${ADV}) GROUP BY 1 ORDER BY 1"
  done
}

if [ "$MODE" = verify ]; then
  echo "=== VERIFY (read-only): DEV counts for ${ADV} ==="; counts "$DEV"
  echo "(no changes made — pass --apply to write)"; exit 0
fi

if [ "$MODE" = reverse ]; then
  echo "=== REVERSE: deleting ${ADV} from DEV ==="
  for T in "${TABLES[@]}"; do
    echo "--- $T ---"
    bq_q "DELETE FROM \`$DEV.$DS.$T\` WHERE KLEVER_ADVERTISER_ID IN (${ADV})"
  done
  echo "=== post-reverse DEV counts (expect empty) ==="; counts "$DEV"; exit 0
fi

# ---- apply ----
TS=$(date +%Y%m%d-%H%M%S)
BACKUP="$BACKUP_DIR/proximity-dev-backfill-pre-$TS.txt"
echo "=== BACKUP pre-state -> $BACKUP ==="
{
  echo "pre-state DEV counts for advertisers ${ADV} (project $DEV) @ $TS"
  counts "$DEV"
  echo ""
  echo "REVERSAL: $(basename "$0") --reverse ${*}"
} | tee "$BACKUP"
echo

for T in "${TABLES[@]}"; do
  echo "=== $T ==="
  PCOLS=$(col_list "$PROD" "$T"); DCOLS=$(col_list "$DEV" "$T")
  if [ -z "$PCOLS" ] || [ "$PCOLS" != "$DCOLS" ]; then
    echo "ABORT: schema mismatch on $T — prod and dev columns differ (or table missing)." >&2
    echo "  prod: $PCOLS" >&2
    echo "  dev : $DCOLS" >&2
    exit 1
  fi
  COLS=${PCOLS//|/,}   # explicit, name-matched column list
  echo "-- replace (delete then insert), columns: $COLS"
  bq_q "DELETE FROM \`$DEV.$DS.$T\` WHERE KLEVER_ADVERTISER_ID IN (${ADV})"
  bq_q "INSERT INTO \`$DEV.$DS.$T\` ($COLS)
        SELECT $COLS FROM \`$PROD.$DS.$T\`
        WHERE KLEVER_ADVERTISER_ID IN (${ADV})"
done

echo
echo "=== POST-STATE: DEV counts for ${ADV} (should match prod) ==="; counts "$DEV"
echo
echo "Done. Backup: $BACKUP   Undo: $(basename "$0") --reverse ${*}"
