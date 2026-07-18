# Closing draft — KTP-939 (pending WALL approval)

**Demo-dev (Cause A — confirmed):** POI panel 500 on demo-dev traced to DAC config pointing to retired host `proxrp-cos-retired.dead` after MR!21. Fix: update `dac-gcp-back-proxrp` env config to the correct COS host URL, redeploy. Exit: same repro green (200, panel renders).

**Prod + demo-prod (open):** 0 locations found for advertiser 842. Anchor confirmed (200-empty). No confirmed cause — BQ probe for advertiser 842 row count is the next step. Investigation requires a follow-up (comment posted; ticket to be created before close).

Note: demo-prod shares the prod backend + BQ. A prod fix will resolve demo-prod if the cause is backend/data.
