# Skill Proposal: placer-api-integration
Date: 2026-04-17
Source: KTP-130 session — Placer API live testing and store data unblock

## Trigger
Any dev work involving Placer API endpoints: CBG visitor origins, visit metrics, entity lookups, custom POI onboarding. Trigger phrases: "check Placer", "query Placer API", "Placer entity IDs", "CBG data", "visitor origin data".

## Scope
org (Klever)

## Reference
Full integration knowledge: `documentation/bibliotheque/vendors/placer-ai.md`
Live test scripts already documented there.

## Draft Steps

1. **Auth check** — Verify `x-api-key` header works. Load key from `project-management/.env`. Run `/v1/poi?limit=1` health check.

2. **Entity lookup** — Check if brand exists as Placer managed entity via `/v1/poi/my-properties`. If 0 results, trigger Custom POI Build Process (see step 5).

3. **Endpoint selection** — Standard tier: visit-metrics, visit-trends, trade-area-demographics. Premium tier: visit-metrics/cbgs (confirmed in contract). `/v1/search` returns 404 — not available.

4. **Request / poll** — Build camelCase request body (`entityIds`, `startDate`, `endDate`, `granularity`). Handle 202 async with exponential backoff poll (5s→15s→30s→60s cap). 204 = empty data, not error.

5. **Custom POI build (if entity missing)**
   - Pull locations from BQ: `klever_external_data.normalized_klever_stores_mapping` using DSP string ADVERTISER_ID (NOT integer)
   - Export CSV: `klever_location_id, location_name, address, city, state, zip_code`
   - Submit to Nick Christensen (Placer AM) with mapping request
   - SLA: ~1 week ≤15 locations
   - Store returned entity IDs mapped to `klever_location_id` in backend adapter

## Key Gotchas to Encode
- camelCase schema only (not snake_case)
- `x-api-key` header only (Bearer/Basic fail)
- `ADVERTISER_ID` in BQ store mapping = DSP string, not Klever integer
- Sparse CBGs are privacy-redacted — missing CBG in response is not an error
- `gcloud` skill is Supervisr-only — use `bq` CLI for Klever BQ queries
