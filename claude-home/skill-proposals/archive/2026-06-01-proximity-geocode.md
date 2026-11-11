# Skill Proposal: proximity-geocode
Date: 2026-06-01
Source: bold-finch / KTP-755 — proved a repeatable address-geocoding workflow

## Trigger
User supplies an ordered list of store addresses and wants paste-ready
coordinates for the "Normalized Klever Stores locations" Google Sheet. First
member of a future `proximity` plugin. See companion handoff
`sessions/active/bold-finch/prompts/2026-06-01-proximity-plugin-geocode-skill.md`.

## Scope
org (Klever) — generalizes existing `geocode-bq-locations` / `location-scraper`
with an ordered, paste-back-to-sheet output contract + storage-licensing guard.

## Draft Steps
1. Input: ordered address list (row key + street/city/prov/postal), sheet order.
2. Geocode via Nominatim/OSM only (storage-safe, ODbL); rate-limit ≥1.1s; certifi SSL.
3. Preserve order; tiered fallback (street+postal → street+city → centroid, flagged); region bbox validation.
4. Output paste-ready TSV (lat⇥long, no header, in order) + verification.csv + failures report, to a committed folder (never /tmp).
5. Echo advertiser id/brand + footprint sanity check so the human catches a mislabel.

## Notes
Do NOT fork — consolidate with `geocode-bq-locations`, `placer-onboarding`,
`location-scraper`. The new angles: ordered paste contract + storage licensing.
