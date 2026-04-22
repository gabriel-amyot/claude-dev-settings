#!/bin/bash
# Poll a Placer async report until COMPLETED
# Usage: bash poll_report.sh <report_id>
# Placer reimburses 202 quota calls hourly — polling is safe.

set -e
REPORT_ID="${1:?Usage: poll_report.sh <report_id>}"
source project-management/.env

DELAY=5
MAX_WAIT=300  # 5 minutes max
ELAPSED=0

echo "Polling report: $REPORT_ID"

while [ $ELAPSED -lt $MAX_WAIT ]; do
  RESPONSE=$(curl -s -H "x-api-key: $PLACER_API_KEY" \
    "https://papi.placer.ai/v1/reports/$REPORT_ID")
  STATUS=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','UNKNOWN'))" 2>/dev/null)

  echo "  [${ELAPSED}s] status: $STATUS"

  if [ "$STATUS" = "COMPLETED" ]; then
    echo "Done."
    echo "$RESPONSE" | python3 -m json.tool
    exit 0
  fi

  sleep $DELAY
  ELAPSED=$((ELAPSED + DELAY))
  # Exponential backoff: 5→15→30→60 cap
  DELAY=$(( DELAY < 60 ? DELAY * 2 : 60 ))
  [ $DELAY -gt 30 ] && DELAY=60
done

echo "Timed out after ${MAX_WAIT}s. Report may still be processing."
exit 1
