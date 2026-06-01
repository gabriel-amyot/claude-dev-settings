---
name: klever-bq-store-lookup
description: "Retrieve physical store locations for a Klever advertiser from BigQuery. Resolves DSP string ID, queries normalized_klever_stores_mapping, QA-flags suspect rows. Trigger: 'find stores for advertiser X', 'pull location list from BQ', 'export locations for Placer'. Klever org. Input: advertiser name or Klever integer ID. Returns: store list with coordinates + QA flags."
nav:
  bay: know
  when: "Retrieve physical store locations for a Klever advertiser from BQ."
  when_not: "Geocoding missing coordinates (use /geocode-bq-locations). Schema check (use /bq-schema-preflight)."
  org: [klever]
---

# Klever BQ Store Lookup

Retrieves physical store locations for an advertiser from the normalized BQ mapping table.

## Steps

### 1. Resolve DSP String ID

If the user provides a Klever integer ID, resolve the DSP string identifier:

```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT DISTINCT DSP_ADVERTISER_ID
   FROM \`prj-p-biz-report-fo53kywlio.portal_dashboards_data.advertisers_daily_performance\`
   WHERE KLEVER_ADVERTISER_ID = <integer_id>"
```

If the user provides a brand name, first look up the Klever ID from the advertiser mapping (check `documentation/bibliotheque/` or the reference memory `reference_proximity_advertiser_mapping.md`).

Known advertisers (from memory):
- Check `~/.claude/projects/-Users-gabrielamyot-Developer-grp-beklever-com-project-management/memory/reference_proximity_advertiser_mapping.md` for the current list.

### 2. Query Store Mapping

```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT KLEVER_LOCATION_ID, LOCATION_NAME, ADDRESS, CITY, STATE, ZIP_CODE, LATITUDE, LONGITUDE, INACTIVE
   FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
   WHERE ADVERTISER_ID = '<dsp_string_id>'
   ORDER BY STATE, CITY"
```

### 3. QA Flags

Check each row for:
- **STATE validity:** must be a valid 2-letter US state code
- **ZIP validity:** must be 5 digits (or 5+4 format)
- **INACTIVE:** only include INACTIVE=FALSE unless user explicitly wants all
- **Address completeness:** ADDRESS, CITY, STATE, ZIP_CODE must all be non-null and non-empty
- **Coordinate bounds:** LATITUDE between 24.0 and 50.0, LONGITUDE between -125.0 and -66.0 (continental US)
- **Duplicate detection:** same address appearing under different KLEVER_LOCATION_IDs

Print any flagged rows separately with the reason.

### 4. Output

- Total store count (active only)
- Sample rows (first 10)
- QA flag summary
- If user wants CSV export:

```bash
bq query --use_legacy_sql=false --format=csv \
  "SELECT KLEVER_LOCATION_ID, LOCATION_NAME, ADDRESS, CITY, STATE, ZIP_CODE, LATITUDE, LONGITUDE
   FROM \`prj-p-biz-report-fo53kywlio.klever_external_data.normalized_klever_stores_mapping\`
   WHERE ADVERTISER_ID = '<dsp_string_id>' AND INACTIVE = FALSE
   ORDER BY STATE, CITY" \
  > /tmp/stores-<advertiser>-$(date +%Y%m%d).csv
```

Save to ticket folder if ticket context exists, otherwise `/tmp/`.

## Notes

- BQ project: `prj-p-biz-report-fo53kywlio`
- Auth: `gamyot@beklever.com` account via `gcloud auth application-default login`
- Brand alias resolution: before declaring "no stores found", search ALL known aliases (consumer brand, corporate parent, DBA, franchise name). Learned from KTP-130 where "Artistry Brand" vs "Shrimp Basket" caused a 21-day delay.
