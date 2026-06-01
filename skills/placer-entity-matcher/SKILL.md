---
name: placer-entity-matcher
description: "Match Klever store locations to Placer.ai entities. Supports venue and complex entity types with per-advertiser preference. Queries BQ for stores, searches Placer API by brand name variants, matches by address/city/ZIP similarity. Trigger: 'match Placer entities', 'map stores to Placer', 'entity matching', 'onboard advertiser to Placer'. Klever org. Input: advertiser name or ID. Returns: bridge CSV + unmatched report."
nav:
  bay: build
  when: "Match Klever store locations to Placer.ai entities by address/city/ZIP similarity."
  when_not: "Full advertiser onboarding (use /placer-onboarding). API exploration (use /klever-placer-api)."
  org: [klever]
---

# Placer Entity Matcher

Matches Klever advertiser store locations (from BQ) to Placer.ai entities for Measurement Map integration.

## Prerequisites

- Placer API key (source from `project-management/.env` or 1Password: `op item get "placer API key" --vault grp-client-portal-ui --fields credential --reveal`)
- BQ access via `gamyot@beklever.com`
- Advertiser must have stores in BQ `normalized_klever_stores_mapping`
- Auth header: `x-api-key: $PLACER_API_KEY` (not Bearer, not Basic)

## Advertiser Profiles

Read this table before starting a matching run. It determines search strategy and entity type preference.

| Advertiser | Klever ID | DSP ID | Brand Name Variants | Entity Type Preference | Notes |
|---|---|---|---|---|---|
| Shrimp Basket | 51 | `la8clii` | Shrimp Basket | `venue` (default) | Restaurants. Single-tenant. Original benchmark. |
| Chevron ExtraMile | TBD | TBD | ExtraMile, Extra Mile, Extra Mile Full Site, Chevron ExtraMile | `complex` | Gas stations. Multi-tenant (gas + store + car wash). |

**If the advertiser is not in this table:** Ask the user for brand name variants and entity type preference before proceeding.

## Steps

### 1. Get Klever Store Locations

Use `/klever-bq-store-lookup` skill or run directly:

```bash
bq query --use_legacy_sql=false --format=csv \
  "SELECT KLEVER_LOCATION_ID, LOCATION_NAME, ADDRESS, CITY, STATE, ZIP_CODE, LATITUDE, LONGITUDE
   FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
   WHERE ADVERTISER_ID = '<dsp_string_id>' AND INACTIVE = FALSE
   ORDER BY STATE, CITY" \
  > /tmp/klever-stores.csv
```

### 2. Search Placer Per Store (Address-Based)

**DO NOT use lat/lng/radius params.** The Placer POI search ignores coordinates (returns 0 results). State/city params are also ignored. Search is text-only.

**DO NOT build a global catalog.** The POI search returns max 100 per query, but brands like ExtraMile have 968+ locations. A global catalog hits a 20.7% coverage ceiling. Instead, search per store.

For each Klever store from Step 1, search Placer by address or brand+city:

```bash
source project-management/.env

# Strategy A (preferred): Search by address + city
# Most precise, returns both venue and complex at exact address
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi?query=$(echo "$ADDRESS $CITY" | sed 's/ /+/g')&limit=10"

# Strategy B (fallback): Search by brand + city
# Broader results, good when address format differs
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi?query=$(echo "$BRAND $CITY" | sed 's/ /+/g')&limit=10"

sleep 1  # rate limit: 1 req/sec per call
```

**Rate budget:** 1 API call per store. 100 stores = ~2 min. 500 stores = ~9 min. Well within 5,000/hour limit.

**Scale ceiling:** This approach supports up to ~2,000 stores per run (34 min, within 5,000/hour rate limit). For advertisers with 5,000+ stores, the weekly 10,000-request cap becomes the constraint. Fallback for large advertisers: batch the run across multiple days, or use the chain sub-entity endpoint to pre-filter by known entity IDs.

**MANDATORY: Chain validation cross-reference (for complex-type advertisers).** After matching, verify every matched entity ID exists in the brand's chain. Without this, you can silently match to a Subway complex next door to an ExtraMile.

```bash
# Get all ExtraMile complexes (IDs only, no addresses)
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi/chain:6649b70716e815d6fb3dede8/entities?limit=1000"
```

For each matched entity: confirm apiId appears in the chain entity list. If it does NOT, flag the match as "UNVERIFIED: not in chain" and demote confidence to LOW regardless of address match quality.

### 3. Match Klever Stores to Placer Entities

For each Klever store from Step 1, find matches in the Placer catalog from Step 2:

**3a. Candidate selection (any of these criteria):**
- City matches (normalized, case-insensitive, handle abbreviations)
- State matches AND ZIP matches (first 5 digits)
- Street number from address matches

**3b. Confidence scoring:**
- **HIGH**: address + city + ZIP all match
- **MEDIUM**: 2 of 3 match, or same city + similar street name
- **LOW**: only 1 dimension matches
- **NONE**: no plausible match found

**3c. Entity type preference (new):**
If `entity_type_preference` is set in the advertiser profile:

1. Among candidates, find all matches of the preferred type
2. If a HIGH or MEDIUM match of preferred type exists → **select it**
3. If only LOW matches of preferred type exist → select best overall match, flag in notes
4. If NO match of preferred type exists → **fall back** to best match of any type, add note: "No {preferred_type} match found, using {actual_type} instead"
5. Log ALL alternative matches (other entity IDs at the same address) in the `alternative_entity_ids` column

If NO preference is set (e.g., Shrimp Basket): select highest confidence match regardless of entity type.

### 4. Flag Known Data Bugs

Check for and flag:
- Wrong STATE in BQ data (e.g., store in Alabama listed as Georgia)
- Invalid ZIP codes
- Placer entities with different names but same address (rebranded locations)
- Multiple Placer matches for one Klever store at same confidence (pick preferred type, then closest address match)
- Complex entities that contain the store as a sub-venue (confirms correct match)

### 5. Output Bridge CSV

Write to ticket folder or /tmp:

```csv
klever_location_id,placer_entity_id,entity_type,location_name,address,city,state,match_confidence,alternative_entity_ids,notes
```

Columns:
- `entity_type`: derived from apiId prefix (venue/complex/chain)
- `alternative_entity_ids`: pipe-separated list of other entity IDs that matched the same address (enables switching between venue/complex later without re-running)
- `notes`: disambiguation notes, data quality flags, fallback notices

Separate sections:
- **Matched (HIGH)**: ready for bridge table
- **Matched (MEDIUM/LOW)**: need manual review before bridge insertion
- **Unmatched Klever stores**: not found in Placer. Downstream action: report to ops for manual POI creation via KTP-608 "Request POI" path (1-3 biz day SLA for Placer to build managed entities)
- **Chain-unverified matches**: matched by address but apiId not in chain entity list. Likely false positive. Exclude from bridge table.

### 6. Summary Report and Acceptance Gate

Print:
- Total Klever stores: N
- Matched (HIGH): N (X%)
- Matched (MEDIUM): N
- Matched (LOW): N
- Unmatched: N
- Coverage: X%
- Entity type distribution: N venue / N complex
- Chain-verified: N / N matched (X%)

**Acceptance threshold: minimum 80% HIGH-confidence matches required to proceed to bridge population.** If HIGH rate is below 80%, STOP. The run needs human triage before inserting anything into the bridge table. Common causes: bad BQ addresses, stale name variants, or a brand with sparse Placer coverage.

**Stale-variant detection:** Compare matched complex count against the chain sub-entity total. If the ratio (matched / chain total) drops below 50% for an advertiser where you expect broad coverage, flag that the name variants in the advertiser profile may be outdated. Placer renames entities periodically. Example: if ExtraMile has 968 chain members but you only matched 200 complexes, the search terms are likely missing a new naming pattern. Investigate before proceeding.

### 7. CBG Pre-Check (Optional, Recommended for Complex Entities)

After matching, test CBG endpoint for each matched entity to flag locations with insufficient panel data:

```bash
ENTITY_ID="complex:xxx"
curl -s -w "\nHTTP:%{http_code}" \
  -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  -d "{\"apiIds\":[\"$ENTITY_ID\"],\"startDate\":\"2025-01-01\",\"endDate\":\"2025-02-01\",\"granularity\":\"month\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/cbgs"
```

- HTTP 200: CBG data available. Mark "CBG verified" in notes.
- HTTP 204: No CBG data (insufficient panel data). Flag as "limited CBG data" in notes.
- HTTP 202: Re-POST after 10 seconds. Classify on second response.

Rate limit: 1 request/second. For 100 entities, this takes ~2 minutes.

Report: N entities CBG verified / N with limited data / N total.

## Notes

- Rate limit Placer API: 1 request per second, 5,000/hour, 10,000/week
- Placer indexes by consumer-facing names. Always try the storefront brand first.
- **lat/lng search is non-functional** in Placer POI API. All geographic filtering is client-side.
- **Same address can return both venue and complex.** This is normal for gas stations. The preference system handles it.
- This skill produces the matching CSV. Populating the BQ bridge table is a separate manual step.
- Related skill: `/klever-placer-api` for the full Placer API lifecycle
- Related skill: `/klever-bq-store-lookup` for BQ store data
- Benchmark reference: Shrimp Basket matching (KTP-130, 25 venues matched)
- Design doc: `tickets/KTP/KTP-646/KTP-661/reports/architecture/entity-matcher-complex-support-design.md`
