# Skill Proposal: placer-entity-matching
Date: 2026-04-23
Source: KTP-130 architecture session

## Trigger
"match Placer entities", "map stores to Placer", "entity matching", or when onboarding a new advertiser's stores to Placer.

## Scope
org (Klever)

## Draft Steps
1. Read Klever store locations from BQ (lat, lng, name, address per store)
2. For each store, search Placer API: `GET /v1/poi?query={brand}&lat={lat}&lng={lng}&radius=1&limit=5`
3. Match by address similarity or closest lat/lng distance
4. Produce bridge table CSV: `klever_location_id, placer_entity_id, location_name, match_confidence`
5. Validate matches (address comparison, manual review for low-confidence matches)
6. Output: ready for BQ bridge table population
