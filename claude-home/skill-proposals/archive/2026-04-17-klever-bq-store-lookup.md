# Skill Proposal: klever-bq-store-lookup
Date: 2026-04-17
Source: KTP-130 session — pulling Shrimp Basket store locations from BQ

## Trigger
"Find store locations for advertiser X", "pull location list from BQ", "what stores do we have for [brand]", "export locations for Placer". Any request to retrieve physical store data for a Klever advertiser.

## Scope
org (Klever)

## Draft Steps

1. **Resolve DSP string ID** — `ADVERTISER_ID` in store mapping is a DSP string, not the Klever integer. Use bridge table:
   ```sql
   SELECT DISTINCT DSP_ADVERTISER_ID
   FROM `prj-p-biz-report-fo53kywlio.portal_dashboards_data.advertisers_daily_performance`
   WHERE KLEVER_ADVERTISER_ID = <integer_id>
   ```

2. **Query store mapping:**
   ```sql
   SELECT KLEVER_LOCATION_ID, LOCATION_NAME, ADDRESS, CITY, STATE, ZIP_CODE, LATITUDE, LONGITUDE, INACTIVE
   FROM `prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping`
   WHERE ADVERTISER_ID = '<dsp_string_id>'
   ORDER BY STATE, CITY
   ```
   Always use `bq` CLI directly — gcloud skill is Supervisr-only.

3. **QA flags** — Check: STATE correctness, ZIP validity, INACTIVE=FALSE, address completeness. Flag any suspect rows.

4. **Export CSV** — Columns: `klever_location_id, location_name, address, city, state, zip_code`. Write to `/tmp/{brand}-locations-{date}.csv`. Do NOT commit to git.

5. **Report** — Return count, state breakdown, any QA flags. Suggest next step (e.g., submit to Placer for custom POI build).

## Known Data in Table (2026-04-17)
| DSP ID | Brand | Klever ID | Count |
|--------|-------|-----------|-------|
| `la8clii` | The Shrimp Basket | 51 | 18 |
| `cq7l1tl` | Unknown | — | 397 |
| `x2cenj0` | Unknown | — | 197 |
