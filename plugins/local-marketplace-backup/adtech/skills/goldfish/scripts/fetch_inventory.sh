#!/bin/bash
# Fetch Goldfish DOOH screen inventory for a viewport/radius → JSON on disk.
# Usage: bash fetch_inventory.sh <latitude> <longitude> <radius_miles> [output_file]
# Example: bash fetch_inventory.sh 43.6532 -79.3832 1 /tmp/goldfish-inventory.json
#
# Credentials come from 1Password at point of use (item "Goldfish DOOH"). The key is NOT
# in project-management/.env — that file holds only PLACER_API_KEY. Set GOLDFISH_API_KEY
# in the environment to override the 1Password read.
# Response wraps the array: {"inventory":[...]}. /v2/inventory does NOT paginate —
# the full result set returns in one payload, so keep the radius small for viewports.

set -e

LAT="${1:?Usage: fetch_inventory.sh <latitude> <longitude> <radius_miles> [output_file]}"
LNG="${2:?longitude required}"
RADIUS="${3:?radius (miles) required}"
OUTPUT="${4:-/tmp/goldfish-inventory.json}"

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

HTTP=$(curl -s -o "$OUTPUT" -w "%{http_code}" \
  -H "x-api-key: $GOLDFISH_API_KEY" -H "uid: $GFUID" \
  "$BASE/v2/inventory?latitude=$LAT&longitude=$LNG&radius=$RADIUS")

if [ "$HTTP" != "200" ]; then
  echo "ERROR: HTTP $HTTP from /v2/inventory (401 = bad key/uid). Body:"
  head -c 300 "$OUTPUT"; echo
  exit 1
fi

python3 -c "
import json
d = json.load(open('$OUTPUT'))
inv = d.get('inventory', d if isinstance(d, list) else [])
print('Fetched %d screens (lat=$LAT lng=$LNG radius=${RADIUS}mi) -> $OUTPUT' % len(inv))
if inv:
    import collections
    mt = collections.Counter(r.get('mediaTypeId') for r in inv)
    print('  distinct mediaTypeId:', len(mt))
    print('  distinct publisherId:', len(set(r.get('publisherId') for r in inv)))
"
echo "Resolve FK ids to names with: bash scripts/fetch_lookups.sh"
