---
name: placer
description: "Placer.ai foot-traffic vendor integration for the Measurement/proximity map. One multi-mode skill: onboard (full discovery + integration playbook), api-check (test/explore the 7 Placer report endpoints, async polling), entity-match (map Klever stores to Placer venue/complex entities). Trigger: 'onboard X to Placer', 'Placer discovery', 'can we add X to Measurement Map', 'match Placer entities', 'map stores to Placer', 'test Placer endpoints', 'Placer API check', 'CBG / visitor origins', 'foot traffic'. Klever org. Input: advertiser name/ID. Returns: discovery report / endpoint matrix / bridge CSV."
nav:
  bay: build
  when: "Any Placer.ai work for the map: onboarding an advertiser, validating the API endpoints, or matching stores to Placer entities."
  when_not: "Geocoding addresses (use mapping:geocode). Pulling the raw store list from BQ (use klever-bq-store-lookup). DOOH inventory (use adtech:goldfish)."
  org: [klever]
---

# adtech:placer — Placer.ai Vendor Integration (multi-mode)

Merges the former `placer-onboarding`, `klever-placer-api`, and `placer-entity-matcher`
into one skill with shared context and three modes. They share the same auth, rate
limits, gotchas, and BQ tables, so that reference lives here once. The mode sections
below contain the full working procedures inline — there are no external skill
dependencies. Bundled: `scripts/export_stores.sh`, `scripts/poll_report.sh`,
`references/endpoints.md`.

## Modes

| Mode | Replaces | Does |
|---|---|---|
| `onboard` | `placer-onboarding` | Full discovery + integration playbook: 4 phases (entity discovery → endpoint compatibility → BQ data assessment → recommendations & action plan). Go/no-go for a new advertiser. |
| `api-check` | `klever-placer-api` | Explore/validate the Placer report API: test the 7 Measurement-Map endpoints, handle 202 async, interpret 204 (no CBG panel data). |
| `entity-match` | `placer-entity-matcher` | Match Klever stores → Placer venue/complex entities by address/city/ZIP; produce the bridge CSV; chain-verify; 80% HIGH-confidence acceptance gate. |

Pick the mode from intent. "Onboard X" → `onboard` (which itself calls the
`api-check` and `entity-match` procedures as Phases 2 and 3).

---

## Shared reference (all modes)

### Auth & limits
| Detail | Value |
|---|---|
| Base URL | `https://papi.placer.ai` |
| Auth header | `x-api-key: $PLACER_API_KEY` (NOT Bearer, NOT Basic) |
| Key source | 1Password: `op item get "placer API key" --vault grp-client-portal-ui --fields credential --reveal`, or `project-management/.env` |
| Rate limits | 1 req/sec, 5,000/hour, 10,000/week |
| Async | HTTP 202 = IN_PROGRESS → re-POST same body after 10s |
| No data | HTTP 204 = insufficient panel data (privacy redaction) — normal for low-traffic locations |
| Date format | `YYYY-MM-DD`, range must span ≥ one full period |
| Field casing | camelCase (`startDate`, `apiId`); snake_case → 400 |

**Prerequisites (verify before any mode):**
```bash
# 1. Placer key present (sources from project-management/.env or 1Password)
source project-management/.env 2>/dev/null; echo "$PLACER_API_KEY" | head -c 6
# 2. Key works — only x-api-key works (Bearer/Basic → 401)
curl -s -H "x-api-key: $PLACER_API_KEY" "https://papi.placer.ai/v1/poi?limit=1" | python3 -m json.tool | head -5
# 3. BQ read access to the shared project (modes onboard/entity-match)
bq query --use_legacy_sql=false "SELECT 1"
```
If the Placer call 401s, the key is wrong/missing. If `bq` fails, run
`gcloud auth application-default login` with the Klever Google account. Stop and tell
the user which prerequisite is missing.

### Gotchas (silent failures)
- **`apiIds` (plural array) vs `apiId` (singular)** — CBG and visit-metrics use `apiIds`; the other 5 endpoints use `apiId`. Wrong one → empty data with HTTP 200.
- **`entityIds` is wrong** — using it instead of `apiIds` on CBG returns an empty 200.
- **POI search is text-only** — lat/lng/radius and state/city params are IGNORED. Search by name or address text.
- **Brand alias rule** — Placer indexes consumer-facing names, not corporate parents. Search the storefront name first ("Shrimp Basket" → 25; "Artistry Brands" → 0).

### Entity taxonomy
| Type | Prefix | Represents | Metric scope |
|---|---|---|---|
| Venue | `venue:` | single business footprint | one tenant's traffic |
| Complex | `complex:` | multi-tenant property | all property visitors |
| Chain | `chain:` | brand rollup | aggregate across members |

Single-tenant (restaurants) → venue. Multi-tenant (gas, malls) → complex. The
venue-vs-complex choice for lift reporting is a PO decision; surface it when both exist.

### BQ tables (project `prj-p-biz-report-fo53kywlio`)
| Table | Purpose | Key columns |
|---|---|---|
| `klever_core_entities.advertiser` | advertiser identity | `advertiser_id`, `dsp_advertiser_id`, `agency_name` |
| `klever_external_data.normalized_klever_stores_mapping` | store locations | `KLEVER_LOCATION_ID`, `ADVERTISER_ID` (DSP string), `LATITUDE`, `LONGITUDE` |
| `portal_dashboards_data.proximity_daily_geo_zip_performance` | campaign perf | `DSP_ADVERTISER_ID`, `DATE` |
| `dts_external_data.klever_placer_entity_map` | Placer bridge | `klever_location_id`, `placer_entity_id` |

### 7 Measurement-Map endpoints (deep detail in `references/endpoints.md`)
`visit-metrics/cbgs` (apiIds), `visit-metrics` (apiIds), `visit-metrics/hours`,
`visit-metrics/days`, `visit-metrics/dwell-time`, `visit-trends/single`,
`loyalty/visits-frequency`. All must return data for an advertiser to work on the map.

### Advertiser profiles (reference; update after each run)
| Advertiser | Klever ID | DSP ID | Variants | Entity pref | Notes |
|---|---|---|---|---|---|
| Shrimp Basket | 51 | `la8clii` | Shrimp Basket | venue | restaurants, single-tenant, benchmark (KTP-130, 25 venues matched), fully onboarded; corporate parent "Artistry Brands"; CBG confirmed working 2026-04-23 |
| Chevron ExtraMile | TBD | TBD | ExtraMile, Extra Mile, Extra Mile Full Site, Chevron ExtraMile | complex | gas, multi-tenant; chain `chain:6649b70716e815d6fb3dede8` (968) |

---

## Mode: `onboard` (full discovery + integration)

Full pipeline from "can we onboard this advertiser?" to "here's exactly what needs to
happen." Self-contained. Run all 4 phases sequentially for a full discovery; the user
may also request a single phase (e.g. "just check if McDonald's is in Placer" = Phase 1
only). **Pause between Phase 3 and Phase 4** and present Phases 1-3 for review before
generating recommendations. Verify prerequisites (Shared reference) first.

### Phase 1: Entity Discovery
**Goal:** Does the advertiser exist in Placer, and what is its entity taxonomy?

**1a. Build brand-name variants.** Sources: consumer storefront name, corporate parent,
DBA/franchise name, the Advertiser-profiles table (Shared reference), and ask the user
"are there other names this brand operates under?". Apply the **brand alias rule**
(Shared reference): Placer indexes consumer-facing names, not corporate parents
("Artistry Brands" → 0; "Shrimp Basket" → 25). Search the storefront name first; only
declare "not found" after trying alternates.

**1b. Search Placer** per variant (a discovery run is 3-6 requests; rate is not a
concern):
```bash
VARIANT="ExtraMile"  # repeat per variant
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi?query=$(echo "$VARIANT" | sed 's/ /+/g')&limit=100" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin); results = d.get('data', [])
venues = [r for r in results if r['apiId'].startswith('venue:')]
complexes = [r for r in results if r['apiId'].startswith('complex:')]
chains = [r for r in results if r['apiId'].startswith('chain:')]
print(f'Total: {len(results)} | Venues: {len(venues)} | Complexes: {len(complexes)} | Chains: {len(chains)}')
for r in results[:5]:
    print(f'  {r[\"name\"]} | {r[\"apiId\"]} | {r.get(\"city\",\"?\")}, {r.get(\"state\",\"?\")}')
"
sleep 1  # 1 req/sec
```

**1c. Classify taxonomy** using the entity-taxonomy table (Shared reference). Mapping:
single-tenant (restaurants, standalone retail) → primarily `venue:`; multi-tenant (gas,
strip malls, food courts) → primarily `complex:` with `venue:` sub-entities; a
national/regional brand with 50+ locations should have a `chain:`. Why it matters for
lift: complex = total property traffic (gas + store + car wash), venue = one tenant.
The venue-vs-complex choice is a PO/sales decision — flag it when both exist.

**1d. Capture 2-3 sample entity IDs per type** (these feed Phase 2). If a chain exists,
get its member count:
```bash
CHAIN_ID="chain:xxx"
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi/$CHAIN_ID/entities?limit=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Chain members: {d.get(\"totalCount\",\"unknown\")}')"
```

**Phase 1 output:**
```markdown
## Entity Discovery: [Advertiser]
| Search Term | Total | Venues | Complexes | Chains |
|---|---|---|---|---|
| [variant] | N | N | N | N |

### Taxonomy Classification
[Single-tenant / Multi-tenant] — [reasoning]

### Sample Entity IDs
| Name | API ID | City, State |
|---|---|---|

### Chain Entity (if found)
Chain ID: [chain:xxx] ([N] members)
```

### Phase 2: Compatibility Validation
**Goal:** Confirm all 7 Measurement-Map endpoints return data for this entity type.
This is the `api-check` procedure run against a Phase 1 sample entity — see Mode
`api-check` below for the full per-endpoint payloads. Run all 7, handle 202, then:

**2b. Async (202).** Some endpoints return 202 (IN_PROGRESS) on first call — normal.
Re-POST the **exact same body** after 10s; classify on the second response.

**2c. Test a second entity** on CBG. CBG availability varies by location (privacy
thresholds): 200 = data available, flow lines render; 204 = insufficient panel data,
flow lines empty for that store (normal for low-traffic locations).

**2d. Backend is entity-type-agnostic.** `app-proximity-report` passes entity IDs as
opaque strings with no type branching (`PlacerEntityBridgeAdapter` reads
`placer_entity_id` as raw STRING; `PlacerApiHttpClient` passes it verbatim;
`StoreMetricsService` fans out to 6 endpoints as String; `VisitorOriginService` is a
String pass-through to `fetchVisitorCbgs()`; bridge schema is `placer_entity_id STRING`
with no type constraints). If Placer accepts the ID (2a), the backend will too — no code
changes. Flag only if a brand-new prefix appears (not `venue:`/`complex:`/`chain:`).

**Phase 2 output:**
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
### Backend: AGNOSTIC — no code changes needed
```

### Phase 3: Data Assessment
**Goal:** What Klever-side data exists and what's missing. All queries target BQ project
`prj-p-biz-report-fo53kywlio` (tables in Shared reference).

**3a. Advertiser identity:**
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT advertiser_id, advertiser_name, dsp_advertiser_id, agency_id, agency_name
   FROM \`prj-p-biz-report-fo53kywlio.klever_core_entities.advertiser\`
   WHERE LOWER(advertiser_name) LIKE LOWER('%BRAND_NAME%') LIMIT 10"
```
Record Klever advertiser ID, DSP string ID, agency. No rows → not set up in the system yet.

**3b. Store locations** (replace `<dsp_string_id>` with the DSP ID from 3a):
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT COUNT(*) total_stores,
     COUNTIF(LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL) geocoded,
     COUNTIF(INACTIVE = FALSE) active,
     COUNTIF(LATITUDE IS NULL OR LONGITUDE IS NULL) missing_coords
   FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
   WHERE ADVERTISER_ID = '<dsp_string_id>'"
```
Sample to eyeball quality (`SELECT KLEVER_LOCATION_ID, LOCATION_NAME, ADDRESS, CITY,
STATE, ZIP_CODE, LATITUDE, LONGITUDE ... WHERE ADVERTISER_ID='<dsp_string_id>' AND
INACTIVE=FALSE ORDER BY STATE, CITY LIMIT 5`). Stores without coordinates can't be
plotted.

**3c. Campaign data** (independent of Placer; absence doesn't block onboarding, only
removes the perf overlay):
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT COUNT(*) rows, MIN(DATE) earliest, MAX(DATE) latest
   FROM \`prj-p-biz-report-fo53kywlio.portal_dashboards_data.proximity_daily_geo_zip_performance\`
   WHERE DSP_ADVERTISER_ID = '<dsp_string_id>'"
```

**3d. Bridge table** (maps Klever location IDs → Placer entity IDs; makes a pin
clickable). `mapped_stores > 0` → already (partially) onboarded:
```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT COUNT(*) mapped_stores
   FROM \`prj-p-biz-report-fo53kywlio.dts_external_data.klever_placer_entity_map\`
   WHERE klever_location_id IN (
     SELECT CAST(KLEVER_LOCATION_ID AS STRING)
     FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
     WHERE ADVERTISER_ID = '<dsp_string_id>')"
```

**3e. User Management** — needs an entry with Measurement component permissions
(**component ID 8**) for portal access. Not BQ-queryable. Flag "verify manually via User
Management API or portal admin."

**Phase 3 output:**
```markdown
## Data Readiness: [Advertiser]
| Dimension | Status | Details |
|---|---|---|
| Advertiser in BQ | [YES / NOT FOUND] | ID: X, DSP: Y, Agency: Z |
| Store locations | [N total, M geocoded, K active] | [or NOT FOUND] |
| Campaign data | [YES: date range / NO] | |
| Bridge table entries | [N mapped / M total] | [or NONE] |
| User Management | VERIFY MANUALLY | Component 8 (Measurement) needed |

### What's Missing
- [ordered list of what must happen before the advertiser works on the map]
```

### Phase 4: Recommendations
**PAUSE before this phase in full-discovery mode.** Present Phases 1-3, wait for review.

**4a. Entity-type rec:** single-tenant → `venue`; multi-tenant → `complex`; both exist →
surface to PO (complex = total property traffic, venue = single tenant; lift reporting
usually wants complex since a billboard drives people to the property, not just the store).

**4b. Go/no-go matrix:**
| Condition | Required? | Source |
|---|---|---|
| Entities found in Placer | Yes | Phase 1 |
| 7/7 endpoints return data | Yes | Phase 2 |
| Advertiser exists in BQ | Yes | Phase 3a |
| Store locations with coordinates | Yes | Phase 3b |
| Bridge table populated | Yes | Phase 3d |
| Campaign data in BQ | No (nice to have) | Phase 3c |
| User Management entry | Yes | Phase 3e |

**4c. Action plan** (note owner — engineering/ops/PO — and any SLA on each item):
- *Already onboarded (all green):* "No action needed. [Advertiser] is live on the Map."
- *Entities exist but not wired:* 1) populate store locations in BQ (via Google Sheet if
  absent); 2) geocode stores missing coordinates; 3) run entity matching (Mode
  `entity-match`); 4) insert matches into `klever_placer_entity_map`; 5) verify User
  Management component 8; 6) test end-to-end on portal.
- *Brand not found in Placer:* 1) submit POI request via Placer web UI
  (`analytics.placer.ai` → "Request POI"); 2) wait 1-3 business days for Placer to build
  managed entities; 3) follow the "entities exist" path.

**4d. Write findings to disk** — one document with all phase outputs, shareable with the
team or attachable to Jira.

**Phase 4 output:**
```markdown
## Placer Onboarding Assessment: [Advertiser]
### Verdict: [READY / BLOCKED / PARTIALLY READY]
### Entity Type Recommendation
[venue / complex] — [reasoning] [If ambiguous: DECISION NEEDED from PO]
### Action Plan
1. [action] — owner: [who] — timeline: [when]
### Full Assessment
[Phase 1-3 outputs as sections]
```

---

## Mode: `api-check` (endpoint validation/exploration)

Test/explore the Placer report API for a given entity ID. Verify prerequisites (Shared
reference) first. Full per-endpoint schemas: `references/endpoints.md`.

### Lifecycle
1. **Auth check** (Shared-reference prerequisites). Only `x-api-key` works; Bearer/Basic 401.
2. **Entity lookup** — confirm the brand exists. Either search POI by name (Phase 1b
   pattern above) or list custom POIs:
   ```bash
   curl -s -H "x-api-key: $PLACER_API_KEY" "https://papi.placer.ai/v1/poi/my-properties?limit=100" \
     | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Custom POIs: {len(d[\"data\"])}'); [print(f'  {e[\"name\"]} -> {e[\"apiId\"]}') for e in d['data']]"
   ```
   0 results → brand not in Placer (go to Custom POI Build below). Results → copy the
   `apiId` values (`venue:`/`complex:`/`chain:`).
3. **Query the endpoints** (camelCase only; snake_case → 400). Handle 202. Interpret 204.

### Test all 7 Measurement-Map endpoints
```bash
ENTITY_ID="complex:xxx"   # or venue:xxx
START="2025-01-01"; END="2025-02-01"

# 1. CBG / Visitor Origins (flow lines) — uses apiIds (plural array), NOT entityIds
echo "=== 1. visit-metrics/cbgs ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" -H "Content-Type: application/json" -X POST \
  -d "{\"apiIds\":[\"$ENTITY_ID\"],\"startDate\":\"$START\",\"endDate\":\"$END\",\"granularity\":\"month\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/cbgs" | tail -1
sleep 2
# 2. Visit Metrics (KPI cards) — uses apiIds
echo "=== 2. visit-metrics ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" -H "Content-Type: application/json" -X POST \
  -d "{\"apiIds\":[\"$ENTITY_ID\"],\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics" | tail -1
sleep 2
# 3. Hourly — uses apiId (singular string)
echo "=== 3. visit-metrics/hours ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/hours" | tail -1
sleep 2
# 4. Daily — uses apiId
echo "=== 4. visit-metrics/days ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/days" | tail -1
sleep 2
# 5. Dwell time — uses apiId
echo "=== 5. visit-metrics/dwell-time ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/dwell-time" | tail -1
sleep 2
# 6. Visit trends (time series) — uses apiId
echo "=== 6. visit-trends/single ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\",\"granularity\":\"week\"}" \
  "https://papi.placer.ai/v1/reports/visit-trends/single" | tail -1
sleep 2
# 7. Loyalty / visit frequency — uses apiId
echo "=== 7. loyalty/visits-frequency ==="
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" -H "Content-Type: application/json" -X POST \
  -d "{\"apiId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/loyalty/visits-frequency" | tail -1
```

**Field-name gotcha (silent fail):** endpoints 1-2 (`cbgs`, `visit-metrics`) take
`apiIds` (plural array). Endpoints 3-7 take `apiId` (singular string). Using the wrong
field — or using `entityIds` instead of `apiIds` on CBG — silently returns empty data
with **HTTP 200**, not an error.

### Status interpretation
- **200** — data available.
- **204** — no content: insufficient panel data, **privacy redaction**. Normal for
  low-traffic locations. Sparse CBGs are redacted (missing from the response = expected,
  not an error). Empty `visitsByCBGs` → chain-level entity or sparse-CBG redaction —
  check the entity type.
- **202** — IN_PROGRESS. Re-POST the **exact same body** after 10s; classify on the
  second response. Placer reimburses 202 calls hourly, so polling doesn't permanently
  burn quota. Use the bundled poller for the loop:
  ```bash
  bash scripts/poll_report.sh "$REPORT_ID"
  ```
- **400** — check camelCase fields. **401** — key missing/wrong header. **404 on
  `/v1/search`** — not in our tier; use the Custom POI Build path instead.

### Custom POI Build (when the entity doesn't exist)
When POI/`my-properties` search returns 0 for a brand:
1. **Pull store locations from BQ** (`ADVERTISER_ID` in BQ is the DSP string, NOT the
   Klever integer):
   ```bash
   bash scripts/export_stores.sh "la8clii"
   ```
   Resolve Klever integer ID → DSP string when needed:
   ```bash
   bq query --project_id=prj-p-biz-report-fo53kywlio --nouse_legacy_sql --format=prettyjson \
     "SELECT DISTINCT DSP_ADVERTISER_ID FROM \`prj-p-biz-report-fo53kywlio.portal_dashboards_data.advertisers_daily_performance\`
      WHERE KLEVER_ADVERTISER_ID = <integer>"
   ```
2. **QA the export** — state codes correct, addresses complete, no `INACTIVE=TRUE` rows.
   Known data bug: Tuscaloosa (loc 870) may show FL instead of AL — verify.
3. **Submit to Placer AM** — contact **Nick Christensen** (Placer technical, POI builds).
   Request a custom POI build for [Brand] — [N] locations. Attach CSV with
   `klever_location_id, location_name, address, city, state, zip_code`. SLA ~1 week for
   ≤15 locations; 16+ may run longer.
4. **Store the mapping** when entity IDs return — map Placer `apiId` → `klever_location_id`
   in the backend adapter / bridge table.

---

## Mode: `entity-match` (stores → entities)

Match Klever advertiser store locations (from BQ) to Placer entities, produce the bridge
CSV. Verify prerequisites (Shared reference) first. Read the Advertiser-profiles table
(Shared reference) before starting — it sets search strategy and entity-type preference.
**If the advertiser is not in that table, ask the user for brand-name variants and the
entity-type preference before proceeding.** This mode produces the matching CSV **and an
idempotent MERGE `.sql` file** (step 6b) ready to populate the BQ bridge table — paste it
into bq CLI or the web console; no hand-written inserts.

### 1. Get Klever store locations
```bash
bq query --use_legacy_sql=false --format=csv \
  "SELECT KLEVER_LOCATION_ID, LOCATION_NAME, ADDRESS, CITY, STATE, ZIP_CODE, LATITUDE, LONGITUDE
   FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
   WHERE ADVERTISER_ID = '<dsp_string_id>' AND INACTIVE = FALSE
   ORDER BY STATE, CITY" > /tmp/klever-stores.csv
```
(Or `scripts/export_stores.sh <dsp_string_id>`.)

### 2. Search Placer PER STORE (address-based)
- **DO NOT use lat/lng/radius params** — Placer POI search ignores coordinates (returns
  0). State/city params are also ignored. Search is **text-only**. lat/lng search is
  non-functional; all geographic filtering is client-side.
- **DO NOT build a global catalog** — POI search caps at 100 results/query, but brands
  like ExtraMile have 968+ locations. A global catalog hits a ~20.7% coverage ceiling.
  Search per store instead.

```bash
source project-management/.env
# Strategy A (preferred): address + city — most precise, returns venue and complex at the exact address
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi?query=$(echo "$ADDRESS $CITY" | sed 's/ /+/g')&limit=10"
# Strategy B (fallback): brand + city — broader, good when address format differs
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi?query=$(echo "$BRAND $CITY" | sed 's/ /+/g')&limit=10"
sleep 1  # 1 req/sec
```
**Rate budget:** 1 call/store. 100 stores ≈ 2 min, 500 ≈ 9 min — within 5,000/hour.
**Scale ceiling:** up to ~2,000 stores/run (~34 min). For 5,000+ stores the weekly
10,000-request cap binds — batch across days or use the chain sub-entity endpoint to
pre-filter by known IDs.

**MANDATORY chain cross-reference (complex-type advertisers).** After matching, verify
every matched entity ID exists in the brand's chain. Without it you can silently match a
Subway complex next door to an ExtraMile.
```bash
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi/chain:6649b70716e815d6fb3dede8/entities?limit=1000"
```
For each matched entity, confirm its apiId appears in the chain list. If it does NOT,
flag "UNVERIFIED: not in chain" and demote confidence to LOW regardless of address-match
quality.

### 3. Match stores to entities
**3a. Candidate selection (any of):** city matches (normalized, case-insensitive, handle
abbreviations); state matches AND ZIP matches (first 5 digits); street number from
address matches.

**3b. Confidence scoring:**
- **HIGH** — address + city + ZIP all match
- **MEDIUM** — 2 of 3 match, or same city + similar street name
- **LOW** — only 1 dimension matches
- **NONE** — no plausible match

**3c. Entity-type preference.** If `entity_type_preference` is set in the advertiser
profile: among candidates, prefer that type — (1) a HIGH/MEDIUM preferred-type match →
select it; (2) only LOW preferred-type matches → select best overall, flag in notes;
(3) NO preferred-type match → fall back to best match of any type, note "No
{preferred_type} match found, using {actual_type} instead"; (4) log ALL alternative
matches (other entity IDs at the same address) in `alternative_entity_ids`. If NO
preference (e.g. Shrimp Basket): select highest-confidence match regardless of type.

### 4. Flag known data bugs
- Wrong STATE in BQ (e.g. an Alabama store listed as Georgia)
- Invalid ZIP codes
- Placer entities with a different name but the same address (rebranded locations)
- Multiple Placer matches for one store at equal confidence → pick preferred type, then
  closest address match
- Complex entities that contain the store as a sub-venue (confirms a correct match)

### 5. Output bridge CSV
Header:
```csv
klever_location_id,placer_entity_id,entity_type,location_name,address,city,state,match_confidence,alternative_entity_ids,notes
```
- `entity_type` — derived from the apiId prefix (venue/complex/chain)
- `alternative_entity_ids` — pipe-separated list of other entity IDs that matched the
  same address (lets you switch venue↔complex later without re-running)
- `notes` — disambiguation, data-quality flags, fallback notices

Separate sections:
- **Matched (HIGH)** — ready for the bridge table
- **Matched (MEDIUM/LOW)** — manual review before bridge insertion
- **Unmatched** — not found in Placer. **List each unmatched store with its full address**
  (the address you searched), and state the two next steps so onboarding is not blocked:
  (1) **submit it as a custom POI** via the "Request POI" path on `analytics.placer.ai`
  (KTP-608; 1-3 biz-day SLA for Placer to build the managed entity), or (2) **search the
  Placer UI manually** for a name/address variant the API text search missed, then re-run.
  Unmatched stores do **not** block bridge population for the matched ones — populate the
  HIGH matches now and backfill the unmatched as POIs land.
- **Chain-unverified** — matched by address but apiId not in the chain list. Likely false
  positive. Exclude from the bridge table.

### 6. Summary report and acceptance gate
Print: total stores N; Matched HIGH N (X%); MEDIUM N; LOW N; unmatched N; coverage X%;
entity-type distribution (N venue / N complex); chain-verified N/N matched (X%).

**Acceptance gate: ≥80% HIGH-confidence matches required to proceed to bridge
population.** Below 80% → **STOP** for human triage before inserting anything. Common
causes: bad BQ addresses, stale name variants, sparse Placer coverage.

**Stale-variant detection:** compare matched-complex count against the chain sub-entity
total. If (matched / chain total) < 50% where you expect broad coverage, the profile's
name variants may be outdated (Placer renames entities periodically). E.g. ExtraMile has
968 chain members but you matched only 200 complexes → search terms likely miss a new
naming pattern. Investigate before proceeding.

### 6b. Emit the idempotent bridge MERGE SQL (only after the 80% gate passes)
The bridge CSV is the matching artifact; populating `klever_placer_entity_map` is the
operational step. Do **not** hand-write the inserts. Generate a self-contained,
re-runnable `.sql` file from the CSV:
```bash
python3 scripts/csv_to_merge_sql.py <bridge.csv> --advertiser-id <klever_integer_id> \
  -o /tmp/<advertiser>-bridge.sql
```
What it produces and guarantees:
- A `CREATE TABLE IF NOT EXISTS` preamble + a single **`MERGE`** that is
  **keyed on `klever_location_id`** — paste it into the bq CLI or the BigQuery web console
  and re-run it as many times as you like; it **updates in place, never duplicates** a row.
- **Only HIGH-confidence, chain-verified rows are emitted** (the downstream guard for the
  80% acceptance gate). MEDIUM/LOW/UNVERIFIED/UNMATCHED rows can never reach the bridge
  through the generated SQL.
- The CSV does not carry `advertiser_id`; pass the Klever integer id with `--advertiser-id`.

**Environment (KTP-695).** The default `--project` is **dev** (`prj-d-grid-insigt-3vm2fcstbw`).
The prod bridge dataset does not yet exist; once infra confirms the prod project, pass
`--project <prod>` to repoint. Run it:
```bash
# ALWAYS back up the advertiser's existing rows first (org backup-before-mutation rule):
bq query --project_id=prj-d-grid-insigt-3vm2fcstbw --use_legacy_sql=false --format=prettyjson \
  "SELECT * FROM \`prj-d-grid-insigt-3vm2fcstbw.dts_external_data.klever_placer_entity_map\`
   WHERE advertiser_id = <id>" > backup-<advertiser>-$(date +%Y%m%d).json
# Validate syntax without executing (recommended):
bq query --project_id=prj-d-grid-insigt-3vm2fcstbw --use_legacy_sql=false --dry_run < /tmp/<advertiser>-bridge.sql
# Execute:
bq query --project_id=prj-d-grid-insigt-3vm2fcstbw --use_legacy_sql=false < /tmp/<advertiser>-bridge.sql
```

### 7. CBG pre-check (optional, recommended for complex entities)
After matching, test the CBG endpoint per matched entity to flag locations with
insufficient panel data:
```bash
ENTITY_ID="complex:xxx"
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $PLACER_API_KEY" -H "Content-Type: application/json" -X POST \
  -d "{\"apiIds\":[\"$ENTITY_ID\"],\"startDate\":\"2025-01-01\",\"endDate\":\"2025-02-01\",\"granularity\":\"month\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/cbgs"
```
200 → "CBG verified"; 204 → "limited CBG data"; 202 → re-POST after 10s, classify on the
second response. ~2 min for 100 entities. Report: N verified / N limited / N total.

---

## Composition (proximity use case)
`mapping:geocode` (coords) → `klever-bq-store-lookup` (store list/DSP id) →
**`adtech:placer` entity-match** → bridge table → live map. See the Bibliothèque
use-case page `onboard-advertiser-stores` for the full cross-layer wiring.

## Provenance (source references)
- Full vendor reference: `documentation/bibliotheque/vendors/placer-ai.md`.
- Brand-alias rule RCA (false-blocker, "Artistry Brands" → 0 hits):
  `tickets/KTP/KTP-115/KTP-130/reports/reviews/rca-b1-false-blocker-2026-04-23.md`.
- Entity-matcher design doc (complex/venue support):
  `tickets/KTP/KTP-646/KTP-661/reports/architecture/entity-matcher-complex-support-design.md`.
- Benchmark: Shrimp Basket matching (KTP-130, 25 venues matched).
