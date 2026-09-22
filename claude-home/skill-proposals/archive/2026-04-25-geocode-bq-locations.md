# Skill Proposal: geocode-bq-locations
Date: 2026-04-25
Source: KTP-130 Phase 1 store locations gap closure

## Trigger
When onboarding a new advertiser to the proximity map and their store locations lack coordinates. "geocode stores for X", "add coordinates for X", "onboard X locations".

## Scope
org (Klever)

## Draft Steps
1. Query `normalized_klever_stores_mapping` for the advertiser's stores (by DSP ID)
2. Geocode addresses via Nominatim (free, no key, 1 req/sec rate limit)
3. For failures, fall back to Google Maps URL extraction via web search
4. Generate output: JSON backup + Google Sheet update instructions (preferred) + BQ UPDATE SQL (fallback)
5. Optionally update `StoreLocationCoordinateFallback.java` if immediate runtime fix needed
