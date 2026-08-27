# Data Mutation Safety

Load when: writing a script that writes, updates, or deletes datastore or database entities.

The always-on rule in CLAUDE.md is short: **back up before you write.** This file holds the procedure and the incidents behind it.

## Backup procedure

Any script that mutates records must first read and save the affected records to a local backup file (JSON).

One line changed equals one line backed up.

- Backup location: `tickets/{TICKET-ID}/data/backups/`
- Filename: timestamped
- No exceptions, even for operations you believe are idempotent
- If you cannot back up (no read access), stop and ask the user

Learned from the SPV-141 data loss incident (2026-04-13).

## Datastore upsert drops unlisted fields

A Datastore `upsert` mutation replaces the **entire** entity. Any property not included in the mutation payload is silently deleted.

Two safe options:

1. Read the full entity first and include **all** fields in the upsert.
2. Use an `update` (patch) operation instead of upsert when changing only specific fields.

Learned from SPV-85 (2026-04-26): `eventMetadata` was lost this way.

## Related

- Liquibase changesets have their own safety rules. See the Klever project's `documentation/bibliotheque/stack/database/liquibase-safety-rules.md`.
