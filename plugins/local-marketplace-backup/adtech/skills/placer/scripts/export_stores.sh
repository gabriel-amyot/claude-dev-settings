#!/bin/bash
# Export store locations for a Klever advertiser from BQ → CSV
# Usage: bash export_stores.sh <dsp_advertiser_id> [output_file]
# Example: bash export_stores.sh la8clii /tmp/shrimp-basket-locations.csv
#
# IMPORTANT: ADVERTISER_ID in BQ is a DSP string (e.g. la8clii), NOT a Klever integer.
# To resolve Klever integer ID → DSP string:
#   bq query ... "SELECT DISTINCT DSP_ADVERTISER_ID FROM
#   portal_dashboards_data.advertisers_daily_performance WHERE KLEVER_ADVERTISER_ID = <int>"

set -e

DSP_ID="${1:?Usage: export_stores.sh <dsp_advertiser_id> [output_file]}"
OUTPUT="${2:-/tmp/placer-store-export-$(date +%Y%m%d).csv}"
PROJECT="prj-p-biz-report-fo53kywlio"

echo "Querying BQ for advertiser DSP ID: $DSP_ID"

bq query --project_id="$PROJECT" --nouse_legacy_sql --format=csv \
"SELECT
  KLEVER_LOCATION_ID,
  LOCATION_NAME,
  ADDRESS,
  CITY,
  STATE,
  ZIP_CODE,
  INACTIVE,
  LATITUDE,
  LONGITUDE
FROM \`$PROJECT.klever_external_data.normalized_klever_stores_mapping\`
WHERE ADVERTISER_ID = '$DSP_ID'
  AND INACTIVE = 'FALSE'
ORDER BY STATE, CITY" > "$OUTPUT"

COUNT=$(tail -n +2 "$OUTPUT" | wc -l | tr -d ' ')
echo "Exported $COUNT active locations → $OUTPUT"
echo ""
echo "QA checks:"
echo "  States present: $(tail -n +2 "$OUTPUT" | cut -d, -f5 | sort -u | tr '\n' ' ')"
echo "  Any missing addresses: $(tail -n +2 "$OUTPUT" | awk -F, '$3==""' | wc -l | tr -d ' ') rows"
echo ""
echo "Next: submit to Nick Christensen (Placer AM) for custom POI build (~1 week SLA)"
echo "Ask for: Placer entity IDs mapped back to KLEVER_LOCATION_ID column"
