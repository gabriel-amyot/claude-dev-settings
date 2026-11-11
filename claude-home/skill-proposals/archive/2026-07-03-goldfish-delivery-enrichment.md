# Skill Proposal: goldfish-delivery-report-enrichment
Date: 2026-07-03
Source: KTP-830 (Chevron ExtraMile weekly DOOH reporting) — clever-otter session

## Trigger
"Add screen IDs to a Goldfish/DOOH delivery report", "match Goldfish delivery to DSP",
"enrich a report that only has lat/lon", "join Goldfish reporting bucket to TTD delivery".
Likely a new mode on the existing `adtech:goldfish` skill rather than a standalone skill.

## Scope
org (Klever). Extends `adtech:goldfish` (currently modes: fetch, plan).

## Why (gap it fills)
The existing skill covers inventory (`fetch`) and planning (`plan`) but NOT the DOOH
*delivery reporting* path. Goldfish delivers per-client delivery CSVs via a GCS reporting
bucket that carry no screen ID — only lat/lon. Recovering the Place Exchange UUID and
joining to DSP (TTD) delivery is a repeatable pipeline, now proven on Chevron.

## Draft Steps (new mode: `enrich`)
1. Input: a delivery CSV with lat/lon (from `gs://reporting_bucket_klever/<client>/...`).
2. Dedup by unique (lat,lon).
3. For each screen: `GET /v2/inventory?latitude=&longitude=&radius=0.2`, nearest screen,
   then `GET /v2/inventory/{id}` → `programmaticPlatformKey` (Place Exchange UUID).
4. Optionally join UUID → TTD `SITE` in
   `prj-p-biz-report-fo53kywlio.klever_data_aggregation.ttd_normalized_daily_inventory_performance`
   (filter `SITE != '[tail aggregate]'`) for per-screen DSP impressions + SPEND_USD.
5. Emit the report with `place_exchange_uuid` (the DSP join key) stitched on.

## Reference implementation
Working scripts already exist at `tickets/KTP/no-epic/KTP-830/scripts/` (01–05). Lift these
into the skill / a Cloud Function once Sisi finalizes the ID source and report shape.

## Also patch (not a skill)
`documentation/bibliotheque/vendors/goldfish/goldfish-ads.md`: add the GCS reporting-bucket
delivery surface, the lat/lon→screen-ID enrichment recipe, the UUID-not-numeric-id rule,
and the Razorfish Chevron TTD validation (second join proof). Handled via the inbox nugget.
