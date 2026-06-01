---
name: placer-onboarding
description: "Full Placer AI discovery and integration playbook for onboarding new advertisers to the Klever Measurement Map. Self-contained: no external skill dependencies. Orchestrates 4 phases: entity discovery (search Placer, classify taxonomy), compatibility validation (test all 7 API endpoints), data assessment (BQ advertiser/stores/campaigns), and recommendations. Use whenever someone mentions onboarding an advertiser to Placer, running a Placer discovery, checking if a brand can be integrated with Measurement Map, or says 'what do we need to onboard X to Placer'. Also triggers on: 'full Placer discovery', 'Placer readiness check', 'can we add X to Measurement Map', 'Placer integration assessment'. Klever org. Input: advertiser name. Returns: discovery report, endpoint matrix, data readiness, action plan."
nav:
  bay: build
  when: "Full Placer AI discovery and integration for onboarding new advertisers."
  when_not: "Just matching entities (use /placer-entity-matcher). API queries only (use /klever-placer-api)."
  org: [klever]
---

# Placer Onboarding: Full Discovery + Integration Playbook

Runs the full pipeline from "can we onboard this advertiser?" to "here's exactly what needs to happen." Self-contained: all queries and API calls are inline. No external skills required.

## Prerequisites

Before starting, verify two things:

**1. Placer API key** — must be set as an environment variable:
```bash
echo $PLACER_API_KEY
```
If empty, the user needs to set it. The key authenticates via `x-api-key` header (not Bearer, not Basic). Source it from 1Password or your team's credential store.

**2. BigQuery CLI access** — must have `bq` CLI configured with read access to `prj-p-biz-report-fo53kywlio`:
```bash
bq query --use_legacy_sql=false "SELECT 1"
```
If this fails, the user needs to run `gcloud auth application-default login` with their Klever Google account.

If either prerequisite fails, stop and tell the user what's missing.

## Modes

**Full discovery:** When the user says "full Placer discovery for X" or "onboard X to Placer", run all 4 phases sequentially. Pause between Phase 3 and Phase 4 for the user to review before generating recommendations.

**Single phase:** The user can request any phase individually (e.g., "just check if McDonald's is in Placer" = Phase 1 only).

---

## Phase 1: Entity Discovery

**Goal:** Determine whether the advertiser exists in Placer and classify its entity taxonomy.

### 1a. Prepare Brand Name Variants

Build a list of search terms before hitting the API. Brands often have multiple consumer-facing names.

Sources for variants:
- Consumer brand name (what's on the storefront)
- Corporate parent name
- DBA / franchise name
- Check the Advertiser Profiles table at the bottom of this file
- Ask the user: "Are there other names this brand operates under?"

**Brand alias rule:** Placer indexes by consumer-facing names, not corporate parents. "Artistry Brands" returns 0 results. "Shrimp Basket" returns 25 venues. Always search the storefront name first. If the API returns 0 results, try alternate names before declaring "not found."

### 1b. Search Placer

For each brand name variant, search the POI endpoint:

```bash
VARIANT="ExtraMile"  # replace with each variant

curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi?query=$(echo "$VARIANT" | sed 's/ /+/g')&limit=100" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
results = d.get('data', [])
venues = [r for r in results if r['apiId'].startswith('venue:')]
complexes = [r for r in results if r['apiId'].startswith('complex:')]
chains = [r for r in results if r['apiId'].startswith('chain:')]
print(f'Total: {len(results)} | Venues: {len(venues)} | Complexes: {len(complexes)} | Chains: {len(chains)}')
for r in results[:5]:
    print(f'  {r[\"name\"]} | {r[\"apiId\"]} | {r.get(\"city\",\"?\")}, {r.get(\"state\",\"?\")}')
"

sleep 1  # rate limit: 1 req/sec
```

**Rate limits:** 1 request/second, 5,000/hour, 10,000/week. A discovery run uses 3-6 requests (one per variant). Not a concern.

Run for each variant. Collect results into a search summary table.

### 1c. Classify Entity Taxonomy

Placer has three entity types. The same physical location can exist as multiple types simultaneously:

| Entity Type | Prefix | What It Represents | Metric Scope |
|---|---|---|---|
| **Venue** | `venue:xxx` | Single business footprint | One tenant's foot traffic only |
| **Complex** | `complex:xxx` | Multi-tenant property | All visitors to the entire property |
| **Chain** | `chain:xxx` | National/regional brand rollup | Aggregate across all member locations |

How to classify the advertiser:

| Business Type | Expected Taxonomy | Example |
|---|---|---|
| Single-tenant (restaurant, standalone retail) | Primarily `venue:` entities | Shrimp Basket |
| Multi-tenant (gas station, strip mall, food court) | Primarily `complex:` entities with `venue:` sub-entities | Chevron ExtraMile |
| National/regional brand with 50+ locations | Should have a `chain:` entity | Most large brands |

**Why this matters:** For campaign lift reporting, complex entities measure total property traffic (gas + store + car wash). Venue entities measure just one tenant. The business decision of which to use belongs to the PO/sales team. Flag it if both types exist.

### 1d. Capture Sample Entity IDs

Record 2-3 entity IDs per type found. These feed Phase 2 testing.

If a chain entity exists, also query its member count:
```bash
CHAIN_ID="chain:xxx"
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi/$CHAIN_ID/entities?limit=1" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Chain members: {d.get(\"totalCount\", \"unknown\")}')"
```

### Phase 1 Output

```markdown
## Entity Discovery: [Advertiser]

| Search Term | Total | Venues | Complexes | Chains |
|---|---|---|---|---|
| [variant 1] | N | N | N | N |
| [variant 2] | N | N | N | N |

### Taxonomy Classification
[Single-tenant / Multi-tenant] — [reasoning based on results]

### Sample Entity IDs
| Name | API ID | City, State |
|---|---|---|
| [name] | [venue:xxx or complex:xxx] | [city, state] |

### Chain Entity (if found)
Chain ID: [chain:xxx] ([N] members)
```

---

## Phase 2: Compatibility Validation

**Goal:** Confirm all 7 Measurement Map API endpoints work with this advertiser's entity type.

The Measurement Map frontend consumes 7 Placer endpoints. All must return data for the advertiser to work on the map. The backend passes entity IDs as opaque strings with no type branching, so if the API accepts the entity ID, the backend will too.

### 2a. Test All 7 Endpoints

Pick a sample entity ID from Phase 1. Set up variables:

```bash
ENTITY_ID="complex:xxx"  # or venue:xxx
START="2025-01-01"
END="2025-02-01"
```

Test each endpoint. Record HTTP status and whether data was returned:

```bash
# 1. CBG / Visitor Origins (flow lines) — CRITICAL: use "apiIds" not "entityIds"
echo "=== 1. visit-metrics/cbgs ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" -X POST \
  -d "{\"apiIds\":[\"$ENTITY_ID\"],\"startDate\":\"$START\",\"endDate\":\"$END\",\"granularity\":\"month\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/cbgs" | tail -1
sleep 2

# 2. Visit Metrics (KPI cards)
echo "=== 2. visit-metrics ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" -X POST \
  -d "{\"apiIds\":[\"$ENTITY_ID\"],\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics" | tail -1
sleep 2

# 3. Hourly Distribution
echo "=== 3. visit-metrics/hours ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/hours" | tail -1
sleep 2

# 4. Daily Distribution
echo "=== 4. visit-metrics/days ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/days" | tail -1
sleep 2

# 5. Dwell Time
echo "=== 5. visit-metrics/dwell-time ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/dwell-time" | tail -1
sleep 2

# 6. Visit Trends (time series)
echo "=== 6. visit-trends/single ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\",\"granularity\":\"week\"}" \
  "https://papi.placer.ai/v1/reports/visit-trends/single" | tail -1
sleep 2

# 7. Loyalty / Visit Frequency
echo "=== 7. loyalty/visits-frequency ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/loyalty/visits-frequency" | tail -1
```

**Field name gotcha:** Endpoints 1-2 use `apiIds` (plural, array). Endpoints 3-7 use `apiId` (singular, string). Using the wrong field silently returns empty data with HTTP 200.

### 2b. Handle Async (202) Responses

Some endpoints return HTTP 202 (IN_PROGRESS) on first call. This is normal. Re-POST the exact same request after 10 seconds. Classify based on the second response.

### 2c. Test a Second Entity

Test at least one more entity ID from Phase 1 on the CBG endpoint. CBG data availability varies by location due to privacy thresholds:

- **HTTP 200**: CBG data available. Flow lines will render.
- **HTTP 204**: No content. Insufficient panel data for this location. Flow lines will be empty for this store. This is normal for low-traffic locations.

### 2d. Backend Compatibility Note

The Klever backend (`app-proximity-report`) is entity-type-agnostic by design. It passes entity IDs as opaque strings through every layer:

| Component | Handling |
|---|---|
| `PlacerEntityBridgeAdapter` | Reads `placer_entity_id` as raw STRING from BQ |
| `PlacerApiHttpClient` | Passes entity ID verbatim to Placer API |
| `StoreMetricsService` | Fans out to 6 endpoints, all receive entity ID as String |
| `VisitorOriginService` | String pass-through to `fetchVisitorCbgs()` |
| Bridge table schema | `placer_entity_id STRING`, no type constraints |

If Placer's API accepts the entity ID (Phase 2a confirms this), the backend will too. No code changes needed. Flag only if a completely new entity type prefix appears (not `venue:`, `complex:`, or `chain:`).

### Phase 2 Output

```markdown
## Endpoint Compatibility: [Advertiser]

Test entity: [entity_id] ([name], [city, state])

| # | Endpoint | HTTP Status | Data? | Verdict |
|---|---|---|---|---|
| 1 | visit-metrics/cbgs | [200/204/202] | [yes/no] | [PASS/FAIL] |
| 2 | visit-metrics | ... | ... | ... |
| 3 | visit-metrics/hours | ... | ... | ... |
| 4 | visit-metrics/days | ... | ... | ... |
| 5 | visit-metrics/dwell-time | ... | ... | ... |
| 6 | visit-trends/single | ... | ... | ... |
| 7 | loyalty/visits-frequency | ... | ... | ... |

**Result: [N]/7 endpoints PASS**

### Secondary CBG Test
Entity: [entity_id_2] — CBG: [200/204]
[Note on CBG coverage variance if applicable]

### Backend: AGNOSTIC — no code changes needed
```

---

## Phase 3: Data Assessment

**Goal:** Determine what Klever-side data exists and what's missing.

All queries target the shared Klever BQ project `prj-p-biz-report-fo53kywlio`.

### 3a. Advertiser Identity

Does this advertiser exist in Klever's entity tables?

```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT advertiser_id, advertiser_name, dsp_advertiser_id, agency_id, agency_name
   FROM \`prj-p-biz-report-fo53kywlio.klever_core_entities.advertiser\`
   WHERE LOWER(advertiser_name) LIKE LOWER('%BRAND_NAME%')
   LIMIT 10"
```

Record: Klever advertiser ID, DSP string ID, agency. If no rows, the advertiser hasn't been set up in the system yet.

### 3b. Store Locations

```bash
# Replace <dsp_string_id> with the DSP ID from 3a
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT
     COUNT(*) as total_stores,
     COUNTIF(LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL) as geocoded,
     COUNTIF(INACTIVE = FALSE) as active,
     COUNTIF(LATITUDE IS NULL OR LONGITUDE IS NULL) as missing_coords
   FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
   WHERE ADVERTISER_ID = '<dsp_string_id>'"
```

If stores exist, also pull a sample to eyeball data quality:
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT KLEVER_LOCATION_ID, LOCATION_NAME, ADDRESS, CITY, STATE, ZIP_CODE, LATITUDE, LONGITUDE
   FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
   WHERE ADVERTISER_ID = '<dsp_string_id>' AND INACTIVE = FALSE
   ORDER BY STATE, CITY
   LIMIT 5"
```

Flag: total stores, how many have coordinates, how many are active. Stores without coordinates can't be plotted on the map.

### 3c. Campaign Data

Campaign data is independent of Placer. Its absence doesn't block Placer onboarding, but the advertiser won't have campaign performance overlay on the map.

```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT COUNT(*) as rows, MIN(DATE) as earliest, MAX(DATE) as latest
   FROM \`prj-p-biz-report-fo53kywlio.portal_dashboards_data.proximity_daily_geo_zip_performance\`
   WHERE DSP_ADVERTISER_ID = '<dsp_string_id>'"
```

### 3d. Bridge Table (Placer Mapping)

The bridge table maps Klever location IDs to Placer entity IDs. This is what makes a store pin clickable on the map.

```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT COUNT(*) as mapped_stores
   FROM \`prj-p-biz-report-fo53kywlio.dts_external_data.klever_placer_entity_map\`
   WHERE klever_location_id IN (
     SELECT CAST(KLEVER_LOCATION_ID AS STRING)
     FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
     WHERE ADVERTISER_ID = '<dsp_string_id>'
   )"
```

If mapped_stores > 0, the advertiser is already (partially) onboarded.

### 3e. User Management

The advertiser needs a User Management entry with Measurement component permissions (component ID 8) for portal access. This is not queryable via BQ. Flag as "verify manually via User Management API or portal admin."

### Phase 3 Output

```markdown
## Data Readiness: [Advertiser]

| Dimension | Status | Details |
|---|---|---|
| Advertiser in BQ | [YES / NOT FOUND] | ID: X, DSP: Y, Agency: Z |
| Store locations | [N total, M geocoded, K active] | [or: NOT FOUND] |
| Campaign data | [YES: date range / NO] | |
| Bridge table entries | [N mapped / M total stores] | [or: NONE] |
| User Management | VERIFY MANUALLY | Component 8 (Measurement) needed |

### What's Missing
- [Ordered list of what needs to happen before this advertiser works on the map]
```

---

## Phase 4: Recommendations

**PAUSE HERE in full-discovery mode.** Present Phases 1-3 to the user and wait for their review before generating recommendations.

### 4a. Entity Type Recommendation

Based on Phase 1 taxonomy:
- **Single-tenant** (restaurants, standalone stores) → recommend `venue` entities
- **Multi-tenant** (gas stations, malls) → recommend `complex` entities
- **Both exist** → surface the decision to the PO. Explain: complex = total property traffic, venue = single tenant traffic. Campaign lift reporting usually wants complex (a billboard drives people to the property, not just the store).

### 4b. Readiness Summary

Combine all phases into a go/no-go:

| Condition | Required? | Status |
|---|---|---|
| Entities found in Placer | Yes | Phase 1 result |
| 7/7 endpoints return data | Yes | Phase 2 result |
| Advertiser exists in BQ | Yes | Phase 3a |
| Store locations with coordinates | Yes | Phase 3b |
| Bridge table populated | Yes | Phase 3d |
| Campaign data in BQ | No (nice to have) | Phase 3c |
| User Management entry | Yes | Phase 3e |

### 4c. Action Plan

Based on what's missing, generate a prioritized action list. Common patterns:

**Already fully onboarded (everything green):**
> No action needed. [Advertiser] is live on the Measurement Map.

**Entities exist in Placer but not yet wired:**
> 1. Populate store locations in BQ (via Google Sheet if not present)
> 2. Geocode any stores missing coordinates
> 3. Run entity matching (match each store to its Placer entity ID)
> 4. Insert matches into bridge table (`klever_placer_entity_map`)
> 5. Verify in User Management (component 8 permissions)
> 6. Test end-to-end on portal

**Brand not found in Placer:**
> 1. Submit POI request via Placer web UI (`analytics.placer.ai` → "Request POI")
> 2. Wait 1-3 business days for Placer to build managed entities
> 3. Then follow the "entities exist" path above

Each action item should note who owns it (engineering, ops, PO) and any SLA/timeline constraints.

### 4d. Write Findings Document

Write the complete findings to disk. Suggested path: a file the user can share with the team or attach to Jira. Include all phase outputs in one document.

### Phase 4 Output

```markdown
## Placer Onboarding Assessment: [Advertiser]

### Verdict: [READY / BLOCKED / PARTIALLY READY]

### Entity Type Recommendation
[venue / complex] — [reasoning]
[If ambiguous: DECISION NEEDED from PO]

### Action Plan
1. [action] — owner: [who] — timeline: [when]
2. ...

### Full Assessment
[Include Phase 1-3 outputs as sections]
```

---

## Advertiser Profiles (Reference)

Known advertisers and their Placer configurations. Updated after each onboarding run.

| Advertiser | Entity Type | Chain ID | Klever DSP ID | Store Count | Notes |
|---|---|---|---|---|---|
| Shrimp Basket | venue | N/A | `la8clii` | 25 | Restaurants. Single-tenant. Original benchmark. Fully onboarded. |
| Chevron ExtraMile | complex | `chain:6649b70716e815d6fb3dede8` (968 members) | TBD | TBD | Gas stations. Multi-tenant. 7/7 endpoints confirmed. Pending location ingestion. |

If the advertiser is not in this table, that's expected for new onboarding requests. Phase 1 will determine its profile.

---

## API Reference (Quick)

| Detail | Value |
|---|---|
| Base URL | `https://papi.placer.ai` |
| Auth header | `x-api-key: <key>` (not Bearer, not Basic) |
| Rate limits | 1 req/sec, 5,000/hour, 10,000/week |
| POI search | `GET /v1/poi?query=<name>&limit=100` |
| Chain members | `GET /v1/poi/<chain_id>/entities?limit=1000` |
| Report endpoints | `POST /v1/reports/...` (see Phase 2 for all 7) |
| Async response | HTTP 202 = re-POST after 10 seconds |
| CBG no-data | HTTP 204 = insufficient panel data (privacy redaction) |
| Silent fail | Using `entityIds` instead of `apiIds` on CBG returns empty 200 |
| Date format | `YYYY-MM-DD`, range must span at least one full period |
| Field casing | All camelCase (`startDate`, `apiId`). Snake_case returns 400. |

## BQ Tables (Klever)

| Table | Purpose | Key Columns |
|---|---|---|
| `klever_core_entities.advertiser` | Advertiser identity | `advertiser_id`, `dsp_advertiser_id`, `agency_name` |
| `klever_external_data.normalized_klever_stores_mapping` | Store locations | `KLEVER_LOCATION_ID`, `ADVERTISER_ID` (DSP string), `LATITUDE`, `LONGITUDE` |
| `portal_dashboards_data.proximity_daily_geo_zip_performance` | Campaign performance | `DSP_ADVERTISER_ID`, `DATE` |
| `dts_external_data.klever_placer_entity_map` | Placer bridge | `klever_location_id`, `placer_entity_id` |

All in BQ project `prj-p-biz-report-fo53kywlio`.
