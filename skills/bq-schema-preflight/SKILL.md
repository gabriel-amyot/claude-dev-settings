---
name: bq-schema-preflight
description: "Verify BQ schema matches SQL query assumptions before wiring adapters. Runs INFORMATION_SCHEMA + sample value checks. Trigger: before modifying any BigQueryAdapter.java, 'check BQ schema', 'verify columns'. Klever org. Input: table name or auto-detect from adapter. Returns: pass/fail with column mismatches and sample values."
nav:
  bay: review
  when: "Verify BQ schema matches SQL query assumptions before wiring adapters."
  when_not: "Auditing which tables are wired (use /bq-table-wiring-audit)."
  org: [klever]
---

# BQ Schema Preflight

Prevents adapter bugs by verifying the actual BigQuery schema before wiring code.

## When to Run

- Before modifying any file matching `*BigQueryAdapter.java` that contains SQL queries
- When the user says "check BQ schema", "verify columns", "preflight"
- After discovering a column mismatch bug

## Steps

### 1. Identify the Target

Accept a table name directly, or auto-detect from the adapter file being edited:

```
Grep for SQL strings (SELECT, FROM) in the current *BigQueryAdapter.java file.
Extract the fully-qualified table name from the FROM clause.
```

If multiple tables are referenced (JOINs), run preflight on each.

### 2. Fetch Actual Schema

Use the Bash tool to query INFORMATION_SCHEMA:

```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT column_name, data_type, is_nullable
   FROM \`prj-p-biz-report-fo53kywlio\`.DATASET.INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = 'TABLE_NAME'
   ORDER BY ordinal_position"
```

Replace DATASET and TABLE_NAME from the fully-qualified table reference.

### 3. Extract SQL Column References

Use Grep to find all column references in the adapter's SQL:
- SELECT clause columns
- WHERE clause columns
- GROUP BY / ORDER BY columns
- Any column aliases or transformations

### 4. Compare: Schema vs SQL

For each column referenced in the SQL:
- Does it exist in INFORMATION_SCHEMA? If not: **FAIL** with "Column not found: X"
- Is the data type compatible with how the code uses it? Flag mismatches.

### 5. Sample Value Check

For each column that exists, run a sample query to catch semantic mismatches:

```bash
bq query --use_legacy_sql=false --format=prettyjson \
  "SELECT DISTINCT column_name
   FROM \`prj-p-biz-report-fo53kywlio.DATASET.TABLE_NAME\`
   WHERE column_name IS NOT NULL
   LIMIT 10"
```

This catches cases like:
- `CHANNEL` column exists but only contains 'UNKNOWN'
- `METRIC_TYPE` exists but values don't match expected enum
- Numeric columns that are always 0

### 6. Output Report

Print a summary table:

```
| Column | In Schema | In SQL | Type | Sample Values | Status |
|--------|-----------|--------|------|---------------|--------|
| CHANNEL | YES | YES | STRING | DISPLAY, VIDEO, UNKNOWN | WARN: UNKNOWN present |
| FAKE_COL | NO | YES | - | - | FAIL: not in schema |
```

Final verdict: PASS (all columns valid, no semantic warnings) or FAIL (with specific issues).

## Notes

- Always use `--use_legacy_sql=false` for BQ queries
- BQ project for Klever production data: `prj-p-biz-report-fo53kywlio`
- Common datasets: `portal_dashboards_data`, `klever_external_data`
- If `bq` CLI fails with auth error, user needs to run `gcloud auth application-default login` with the `gamyot@beklever.com` account
