# Skill Proposal: bq-schema-preflight
Date: 2026-04-03
Source: KTP-329 session — conversions IS_OFFLINE bug, CHANNEL=UNKNOWN bug, METRIC_TYPE mapping bug

## Trigger
Before wiring or modifying any BigQuery adapter (any file matching `*BigQueryAdapter.java` with a real-data SQL query), run this skill to verify the actual BQ schema matches the query's assumptions.

## Scope
Klever org (proximity-report backend). Could generalize to any BQ-backed service.

## Problem It Solves
Three bugs in one session all stemmed from assumed column semantics:
- `METRIC_TYPE` mapped as `CONVERSION_TYPE` (wrong column)
- `CHANNEL='UNKNOWN'` not matching UI channel names (wrong values)
- `DISTRIBUTED_VISITS` always 0 (correct but surprising)

The Schema Validation Gate in CLAUDE.md says "verify before wiring" but doesn't provide tooling. This skill automates the check.

## Draft Steps
1. Accept a table name (or detect from the adapter being edited)
2. Query `INFORMATION_SCHEMA.COLUMNS` for the table's actual schema
3. Parse the SQL query in the adapter to extract column references
4. Compare: flag any column in the SQL that doesn't exist in the schema
5. For columns that exist, show sample values (`SELECT DISTINCT col LIMIT 10`) to catch semantic mismatches (e.g., `CHANNEL` exists but only has value 'UNKNOWN')
6. Output: pass/fail with specific mismatches highlighted

## Dependencies
- `bq` CLI authenticated to the relevant project
- The adapter file path to extract SQL from
