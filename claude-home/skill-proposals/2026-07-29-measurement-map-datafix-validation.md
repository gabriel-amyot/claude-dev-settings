# Skill Proposal: measurement-map-datafix-validation
Date: 2026-07-29
Source: KTP-992 — validating a DV360 state-suffix fix on dev/prod without UI access

## Trigger
Validating a Measurement Map data/backend fix (hover-card metrics, state/zip/county aggregates)
when the affected advertiser is NOT selectable in the UI dropdown (User-Management gated), or when
you need query-layer ground truth rather than a visual check.

## Scope
Klever (org). Overlaps `ui-probe`, `klever-bq-store-lookup`, `gcloud` — composes them, doesn't
reimplement.

## Draft Steps
1. Identify the affected advertiser by `KLEVER_ADVERTISER_ID` in BQ (dropdown is UM-driven, so the
   advertiser exists in data even when absent from the UI). Confirm the bug precondition is present
   (e.g. `SELECT COUNTIF(STATE LIKE '% (State)%') ...`).
2. Controlled before/after on the exact backend WHERE: pre-fix predicate → expect 0 (repro); fixed
   predicate → expect the real rows. Same table the endpoint reads.
3. Close the loop end-to-end: authenticated `POST /api/map/data/<scope>` with `advertiserId` in the
   body (the route gates only on the `Measurement` component, not per-advertiser). Confirm the API
   returns the real metrics, suffix stripped, matching the BQ ground truth.
4. Report: what the pre-fix returned vs the fixed value, and which deployed version was tested.

## Notes
- Depends on live BQ auth (dev `prj-d-biz-report-im9q1fvvc7` / prod `prj-p-biz-report-fo53kywlio`).
- Request DTO: `{advertiserId, startDate, endDate, ids:[2-letter codes], country, channels?, campaignId?}`.
- Borderline: could also just live as a bibliothèque SOP (nuggets #5/#6 in the inbox). File as a
  proposal for the backlog; promote to a skill only if this validation pattern recurs.
