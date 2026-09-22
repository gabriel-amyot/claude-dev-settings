# Skill Proposal: bq-table-wiring-audit
Date: 2026-04-24
Source: KTP-130 test hardening session

## Trigger
"check which BQ tables are wired", "audit BQ dataset", "are all tables connected"

## Scope
org (Klever)

## Problem
When Mo adds new tables to a BQ dataset, there's no quick way to check if the backend references them. Manual grep across adapter files is tedious.

## Draft Steps
1. Accept dataset name (e.g., `klever_proximity_data`)
2. Query `INFORMATION_SCHEMA.TABLES` for table list
3. Grep backend `src/main/java` for each table name
4. Report: wired (file + adapter) vs orphaned (not referenced)
5. For wired tables, verify the column names in the query match the BQ schema
