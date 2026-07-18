PROBE: exhaustive-read bq-dataset 842   METHOD: exhaustive-read   ENV: prod
RESULT (from world.yaml): "advertiser 842 has zero rows in normalized_klever_stores_mapping (never onboarded)."
CITATION: klever-data-workflow@def456
FINDING: No store data for advertiser 842 in BQ. The backend returns 200-empty because the query returns 0 rows — correct behavior, wrong data.
MECHANISM: Missing onboarding data → backend returns empty set → 0 locations displayed.
OWNER: Data owner (Rajan / data-onboarding team) must onboard advertiser 842 into BQ.
TRACKED: KTP-901 (pre-existing data-owner follow-up ticket)
