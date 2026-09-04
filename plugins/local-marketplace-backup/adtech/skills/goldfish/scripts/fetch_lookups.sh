#!/bin/bash
# Cache the six Goldfish DOOH lookup tables to /tmp/goldfish-lookups/.
# FK ids on screen records (publisherId, locationTypeId, mediaTypeId, slotDimensionId,
# programmaticPlatformId, organizationId) resolve against these. Refresh daily.
# Usage: bash fetch_lookups.sh [output_dir]
#
# Credentials come from 1Password at point of use (item "Goldfish DOOH"). The key is NOT
# in project-management/.env — that file holds only PLACER_API_KEY. Set GOLDFISH_API_KEY
# in the environment to override the 1Password read.
# Each response wraps its array in a singular camelCase key (see table below).

set -e

OUTDIR="${1:-/tmp/goldfish-lookups}"
mkdir -p "$OUTDIR"

GF_OP_ITEM="${GOLDFISH_OP_ITEM:-lptegkil5tsm5uqa6pzw7pdaue}"
if [ -z "${GOLDFISH_API_KEY:-}" ]; then
  GOLDFISH_API_KEY=$(op item get "$GF_OP_ITEM" --fields credential --reveal 2>/dev/null) || {
    echo "ERROR: could not read the Goldfish key from 1Password (item $GF_OP_ITEM)."
    echo "  Check 'op' is signed in, or set GOLDFISH_API_KEY yourself."
    exit 1
  }
fi
GFUID="${GOLDFISH_UID:-$(op item get "$GF_OP_ITEM" --fields username --reveal 2>/dev/null || echo app-goldfish@beklever.com)}"
BASE="https://api.goldfishads.com"

# endpoint:wrapper-key
LOOKUPS=(
  "location-types:locationType"
  "publishers:publisher"
  "media-types:mediaType"
  "slot-dimensions:slotDimension"
  "programmatic-platforms:programmaticPlatform"
  "organizations:organization"
)

for entry in "${LOOKUPS[@]}"; do
  ep="${entry%%:*}"; key="${entry##*:}"
  out="$OUTDIR/${ep}.json"
  HTTP=$(curl -s -o "$out" -w "%{http_code}" \
    -H "x-api-key: $GOLDFISH_API_KEY" -H "uid: $GFUID" "$BASE/v2/$ep")
  if [ "$HTTP" != "200" ]; then
    echo "ERROR: HTTP $HTTP from /v2/$ep"; head -c 200 "$out"; echo; exit 1
  fi
  count=$(python3 -c "import json; d=json.load(open('$out')); print(len(d.get('$key', [])))")
  echo "  /v2/$ep -> $out  (\"$key\": $count rows)"
done

echo "Cached 6 lookup tables to $OUTDIR"
