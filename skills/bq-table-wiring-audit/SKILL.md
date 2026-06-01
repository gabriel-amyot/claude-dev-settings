---
name: bq-table-wiring-audit
description: "Audit which BigQuery tables in a dataset are actually referenced in backend code. Classifies as wired/orphaned/ghost. Triggers: 'check BQ tables', 'audit BQ dataset', 'which tables are wired', 'BQ wiring audit', 'connected tables'. Klever org."
nav:
  bay: review
  when: "Audit which BQ tables are referenced in backend code. Wired vs orphaned vs ghost."
  when_not: "Verifying schema columns (use /bq-schema-preflight)."
  org: [klever]
---

# BQ Table Wiring Audit

Answers: "We have N tables in this dataset. Which ones does the app actually use?"

Catches two failure modes:
- **Orphaned tables** — data exists in BQ, no code references the table
- **Ghost references** — code references a table that doesn't exist in BQ

**Usage:** `/bq-table-wiring-audit <dataset-name>`

## Step 1: List All Tables

```bash
bq ls --format=prettyjson PROJECT:DATASET_NAME
```

For each table, get metadata:
```bash
bq show --format=prettyjson PROJECT:DATASET_NAME.TABLE_NAME
```

Extract: `tableId`, `numRows`, `lastModifiedTime`

**Klever BQ projects:**
- Prod: `prj-p-biz-report-fo53kywlio`
- Dev: `prj-d-biz-report-im9q1fvvc7`
- Insights dev: `prj-d-grid-insigt-3vm2fcstbw`

## Step 2: Search Codebase for References

For each table name, grep the Java source:

```
Grep: TABLE_NAME (case-sensitive)
Scope: src/main/java/**/*.java
```

Also grep uppercase variant (SQL uses uppercase in Java strings).

Check for Spring `@Value` property placeholders that resolve to table names.

Collect: which files reference it, whether any match `*BigQueryAdapter.java` or `*Repository.java`.

## Step 3: Determine UI Surface

For each wired table, check if the adapter is called from a controller/resolver:

```
Grep: AdapterClassName
Scope: src/main/java/**/*.java
```

UI-surfaced = reaches `@RestController`, `@QueryMapping`, or `@SchemaMapping`.
Backend-only = used in batch jobs or internal services only.

## Step 4: Detect Ghost References

Scan all `*BigQueryAdapter.java` for FROM clauses. Cross-check table names against BQ table list. Any table in code but not in BQ = ghost.

## Step 5: Classify

| Status | Condition |
|--------|-----------|
| **wired** | Exists in BQ AND referenced in code |
| **orphaned** | Exists in BQ with rows AND no code reference |
| **empty-orphan** | Exists in BQ with 0 rows AND no code reference |
| **ghost** | Referenced in code AND doesn't exist in BQ |

## Step 6: Output

```
BQ Wiring Audit — Dataset: {name}
Project: {project}  Audited: {date}

| table_name | row_count | last_modified | wired | adapter_class | ui_surfaced | status |
|------------|-----------|---------------|-------|---------------|-------------|--------|
```

Then two call-out sections:
- **Orphaned Tables** (data invisible to the app)
- **Ghost References** (will fail at runtime)

If both empty: "Dataset fully wired."

## Rules
- Read-only. Never modify code or BQ data.
- If `bq` CLI fails with auth error: user needs `gcloud auth application-default login`
- Always use `--use_legacy_sql=false` for any queries
