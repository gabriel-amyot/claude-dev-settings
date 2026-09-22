# Skill Proposal: placer-entity-matcher
Date: 2026-04-23
Source: KTP-130 Phase 1 entity matching

## Trigger
When onboarding a new advertiser to Placer (matching Klever stores to Placer venues). Also useful for validating existing mappings after Placer adds/removes venues.

## Scope
org (Klever)

## Draft Steps
1. Query BQ for advertiser's store locations (DSP string ID)
2. Search Placer API for brand name venues
3. Match by city+ZIP+address fuzzy similarity
4. Flag known data bugs (wrong state/ZIP in BQ)
5. Output bridge CSV + unmatched report
