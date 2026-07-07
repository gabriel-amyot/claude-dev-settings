---
name: klever-proximity-dev-backfill
description: "Copy proximity geo-performance data for one or more advertisers from PROD BigQuery into DEV BigQuery, so the Measurement Map renders for them on portal.dev. A documented stopgap for when dev's curated advertiser subset is missing an advertiser (foot traffic / flow lines show 0 on dev but exist in prod). Idempotent (safe to re-run), reversible, backed up, schema-drift-guarded. Read-only by default; requires --apply to write. Trigger: 'backfill dev proximity', 'copy campaign data prod to dev', 'advertiser shows 0 foot traffic on dev', 'dev map has no flow lines for X', 'unblock onboarding on dev', 'sync proximity data to dev'. Klever org. Input: KLEVER_ADVERTISER_ID(s). Returns: dev row counts matching prod + a reversal command."
user_invocable: true
nav:
  bay: ops
  when: "Foot traffic / flow lines render in prod but show 0 on portal.dev for an advertiser, because dev's curated subset never ingested it. Copy the geo-performance rows prod->dev to unblock validation/demo."
  when_not: "A permanent fix (that's an upstream pipeline change — add the advertiser to dev ingestion). Pulling store locations (use /klever-bq-store-lookup). Understanding the pipeline (use /klever-data-pipeline). Locations missing on the map (that's the locations table, not geo-performance)."
  org: [klever]
---

# klever-proximity-dev-backfill

Copy proximity geo-performance rows for specific advertisers from **prod** BQ into **dev** BQ so the Measurement Map renders for them on portal.dev.

## When this is the right tool

An advertiser renders foot traffic / flow lines in prod but shows **0 on portal.dev**. Root cause: the dev Measurement Map reads `prj-d-biz-report-im9q1fvvc7.klever_proximity_data`, but dev's *upstream* TTD/foot-traffic sources only ingest a curated ~18-advertiser subset. The output tables are not allowlist-filtered themselves — the advertiser simply never flows through dev ingestion. Prod has the rows; dev doesn't.

This skill copies the rows directly. **It is a stopgap, not a pipeline fix.** A permanent fix means adding the advertiser to dev ingestion upstream.

## Quick start

```bash
# 1. VERIFY first (default mode — read-only, no write): is it missing in dev?
scripts/backfill.sh 326 27 407

# 2. APPLY (writes to dev): replace these advertisers' rows from prod
scripts/backfill.sh --apply 326 27 407

# Undo:
scripts/backfill.sh --reverse 326 27 407
```

The default mode does **not** write — you must pass `--apply` to mutate dev.

## Workflow

1. **Confirm the gap.** Run the default (verify) mode, or count the advertiser in prod vs dev across the three tables (`proximity_daily_geo_zip_performance`, `_country_performance`, `_conversions`). Proceed only if prod > 0 and dev is missing/short. Source `prj-p-biz-report-fo53kywlio`, target `prj-d-biz-report-im9q1fvvc7`, dataset `klever_proximity_data`.
2. **Apply.** `scripts/backfill.sh --apply <ids...>`:
   - writes a pre-state backup file (`proximity-dev-backfill-pre-<ts>.txt`) to `$BACKFILL_BACKUP_DIR` (defaults to CWD) — set it to the ticket's `data/backups/`;
   - for each table, **deletes** the advertiser's dev rows then **inserts** from prod with an explicit, name-matched column list. This is idempotent: re-running never duplicates, and it self-heals a prior accidental double-run;
   - verifies dev now matches prod.
3. **Reverse path.** Undo with `--reverse <ids>` (also printed by `--apply`).
4. **Remember the second gate.** Flow lines also need **store locations** loaded in dev (`proximity_advertiser_locations`, rebuilt from the Google Sheet by Dataform). Campaign data alone renders nothing without pins. Check locations separately.

## Caveats

- **Stopgap.** Real cause is dev ingestion not covering the advertiser. Don't present this as a pipeline fix in tickets.
- **Incremental DELETE window.** All three targets are `type: incremental` with a 30-day `DELETE FROM self WHERE DATE >= CURRENT_DATE - 30` pre-op (verified for zip, country, and conversions). If a Dataform run hits the dev project, rows dated in the last 30 days for these advertisers can be dropped (dev can't repopulate them); older rows survive. A `--full-refresh` wipes everything. Re-running `--apply` safely restores it (replace semantics, no duplication).
- **Schema drift is fatal-by-design.** The script compares prod vs dev column names per table and **aborts** if they differ, rather than risk a positional `SELECT *` shifting data into the wrong columns. If it aborts, the environments are out of sync — reconcile before forcing.
- **Idempotency depends on `--apply`'s delete-then-insert.** Do not hand-write a plain `INSERT ... SELECT` to do this; that path duplicates on re-run.
- **Permissions.** Needs `bq` read on prod and `bigquery.dataEditor` on the dev project. If the write is denied, hand the script to someone with the dev SA.
- **Projects/backup dir are overridable** via `PROXIMITY_PROD_PROJECT`, `PROXIMITY_DEV_PROJECT`, and `BACKFILL_BACKUP_DIR` env vars.
- **Provenance.** Rows inserted this way are indistinguishable from pipeline rows. Record the backfill in the ticket so a later auditor doesn't mistake it for dev ingestion actually covering the advertiser.
