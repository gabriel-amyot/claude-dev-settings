# Playbook: data-gap / onboarding

Seeder, not a gate. Recency-weighted. Capped at 50% of seeded cards.

## Signature it matches
- `200` with empty/zero results — the app works, the data isn't there.
- One advertiser/entity/region missing while others render.
- A new entity that was never onboarded / never made it through the pipeline.

## Cheapest checks first
1. `[S]` read the source table directly for the missing key; count rows.
   Component = the BQ dataset git-ref (data domain). A `panel shows 0`
   ui-probe is a SYMPTOM, not proof of a data gap — the stamp-check rejects a
   data-gap cause backed only by a ui-probe (IFM-2). (method: exhaustive-read)
2. `[S]` sweep ALL known aliases before declaring "not in vendor/table":
   consumer brand, corporate parent, DBA, franchise (glossary + ticket links +
   BQ names). 0 rows on one name ≠ absent (KTP-130 B1). (method: exhaustive-read)
3. `[M]` trace the ingestion/Dataform path that should populate the key; find
   where it drops. A confabulated "nightly DAG copies it" with no file/line is an
   `[ASSUMED]` card, never a fact (IFM / SFE-15). (method: log-trace / exhaustive-read)

## Source incidents
- KTP-939 Cause A (advertiser 842 never onboarded to the stores mapping).
- KTP-130 B1 (alias sweep — "Artistry Brand" 0 rows, "Shrimp Basket" rich).
