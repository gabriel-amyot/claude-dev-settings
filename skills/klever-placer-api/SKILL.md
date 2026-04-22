---
name: klever-placer-api
description: "Klever Placer.ai API integration skill. Use whenever the user mentions Placer, CBG data, visitor origins, foot traffic API, store entity IDs, custom POI build, or the visit-metrics/cbgs endpoint. Also triggers when the user wants to: check if a Klever advertiser's locations are registered in Placer, pull store location data from BQ for Placer submission, query visit trends or demographics for a POI, or diagnose a Placer API error. Covers the full lifecycle: auth check → entity lookup → BQ store export → Placer API call → 202 async polling → custom POI build process."
---

# Klever — Placer.ai API Integration

Full reference: `documentation/bibliotheque/vendors/placer-ai.md`
API key: `project-management/.env` → `PLACER_API_KEY`
API base: `https://papi.placer.ai`

---

## Step 1 — Auth Check (always start here)

```bash
source project-management/.env
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi?limit=1" | python3 -m json.tool | head -5
```

Expected: JSON with `data` array. A 401 means the key is wrong or the `.env` file is missing.

**Only `x-api-key` header works.** Bearer and Basic both fail with this key.

---

## Step 2 — Entity Lookup (does the brand exist in Placer?)

```bash
curl -s -H "x-api-key: $PLACER_API_KEY" \
  "https://papi.placer.ai/v1/poi/my-properties?limit=100" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Custom POIs: {len(d[\"data\"])}'); [print(f'  {e[\"name\"]} → {e[\"apiId\"]}') for e in d['data']]"
```

- **0 results** → brand not in Placer. Go to Step 5 (Custom POI Build).
- **Results found** → copy the `apiId` values (format: `venue:xxxx` or `chain:xxxx`). Use in Step 3.

---

## Step 3 — Query Placer API

Read `references/endpoints.md` for full schemas. Key rule: **all fields are camelCase** (`entityIds`, `startDate`, `endDate`, `granularity`). Snake_case returns HTTP 400.

### CBG Visitor Origins (premium — confirmed in contract)
```bash
curl -s -w "\nHTTP:%{http_code}" \
  -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  -d "{\"entityIds\":[\"$ENTITY_ID\"],\"startDate\":\"$START\",\"endDate\":\"$END\",\"granularity\":\"month\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics/cbgs"
```

### Visit Metrics (standard tier)
```bash
curl -s -H "x-api-key: $PLACER_API_KEY" \
  -H "Content-Type: application/json" -X POST \
  -d "{\"entityId\":\"$ENTITY_ID\",\"startDate\":\"$START\",\"endDate\":\"$END\"}" \
  "https://papi.placer.ai/v1/reports/visit-metrics"
```

---

## Step 4 — Handle Async (202 response)

Heavy endpoints (CBG, trade-area-demographics) return HTTP 202 with status `IN_PROGRESS`. Use the script:

```bash
bash ~/.claude/skills/klever-placer-api/scripts/poll_report.sh "$REPORT_ID"
```

Placer reimburses 202 calls hourly — polling doesn't permanently burn quota.
Sparse CBGs are privacy-redacted (missing from response = expected, not an error).

---

## Step 5 — Custom POI Build (when entity doesn't exist)

When `my-properties` returns 0 for a brand, follow this process:

### 5a — Pull store locations from BQ
```bash
# ADVERTISER_ID in BQ is DSP string, NOT the Klever integer ID
# Use scripts/export_stores.sh <dsp_advertiser_id>
bash ~/.claude/skills/klever-placer-api/scripts/export_stores.sh "la8clii"
```

To resolve Klever integer ID → DSP string:
```bash
bq query --project_id=prj-p-biz-report-fo53kywlio --nouse_legacy_sql --format=prettyjson \
"SELECT DISTINCT DSP_ADVERTISER_ID FROM \`prj-p-biz-report-fo53kywlio.portal_dashboards_data.advertisers_daily_performance\`
 WHERE KLEVER_ADVERTISER_ID = <integer>"
```

### 5b — QA the export
Check: state codes correct, addresses complete, no INACTIVE=TRUE rows included. Known flag: Tuscaloosa (loc 870) may show FL instead of AL — verify.

### 5c — Submit to Placer AM
Contact: **Nick Christensen** (Placer technical, POI builds)
Request: custom POI build for [Brand] — [N] locations
Attach: CSV with `klever_location_id, location_name, address, city, state, zip_code`
SLA: ~1 week for ≤15 locations. 16+ may run longer.

### 5d — Store the mapping when entity IDs return
Map Placer `apiId` values → `klever_location_id` in the backend adapter.

---

## Quick Reference

| Scenario | Go to |
|----------|-------|
| First time using Placer API | Step 1 (auth check) |
| Check if brand is in Placer | Step 2 (entity lookup) |
| Query visit data | Step 3 + Step 4 if 202 |
| Brand not in Placer | Step 5 (custom POI build) |
| BQ advertiser ID lookup | Step 5a |
| 401 error | Key missing from `.env` or wrong header |
| 400 error | Check camelCase fields |
| 404 on `/v1/search` | Not in our tier — use Step 5 instead |
| Empty `visitsByCBGs` | Chain-level entity or sparse CBG privacy redaction — check entity type |

## Known Advertisers (Klever)

| Brand | Klever Int ID | DSP String ID | Placer Status |
|-------|---------------|---------------|---------------|
| The Shrimp Basket (Artistry Brands) | 51 | `la8clii` | Pending custom POI build (KTP-130) |
