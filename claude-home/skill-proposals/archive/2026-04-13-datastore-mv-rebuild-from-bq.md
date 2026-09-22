# Skill Proposal: datastore-mv-rebuild-from-bq

Date: 2026-04-13
Source: SPV-92 emergency recovery — Richard's MPA mocks wiped pre-demo

## Trigger

User says: "dev data wiped", "rebuild MV from BQ", "restore datastore from the
sink", "dashboard is empty and I need it back before {deadline}", or any
variation where a Supervisr dev Datastore materialized view needs to be
reconstructed from its BigQuery event-store sink.

## Scope

Project-level: `~/Developer/supervisr-ai/project-management`. Applies to any
Supervisr MV backed by an ERS BigQuery sink (interactions, leads, rules,
supervisors, etc.).

## Draft Steps

1. **Confirm scope.** Ask which kind, which partner (`organizationId`), which
   time window. Refuse to run without explicit org — this incident's root
   cause was a cleanup script with no org filter.
2. **Pre-flight reads.** Load the schema contract
   (`documentation/bibliotheque/stack/interactions-mv-schema-and-key.md` or
   equivalent for the target kind). Confirm: identifier property, key-name
   contract, `id`-property mirroring requirement, indexed vs unindexed fields,
   BQ column case mapping.
3. **Confirm BQ sink has the data.** `bq show --schema` + a `COUNT(*) WHERE
   organizationid = @org` probe. Abort if zero.
4. **Confirm MV is actually empty** for the target org before writing. Don't
   clobber live data.
5. **Generate a self-contained Python script** under `tickets/{TICKET}/tools/`
   using `restore-mpa-mv-from-bq.py` as the template. Must include:
   - Dedup by identifier keeping latest `eventMetadata.entityLastModified`.
   - Recursive Row/dict → `datastore.Entity` with `exclude_from_indexes` at
     every nesting level.
   - Key name = identifier, top-level `id` property = identifier.
   - Org case normalization (BQ lowercase → Datastore camelCase).
   - `--dry-run`, `--limit N`, `--yes` flags.
6. **Three-phase rollout with manual gates:**
   - Dry-run, no writes — user inspects samples.
   - `--limit 1 --yes` — user inspects in Datastore console AND downstream
     read path (dashboard detail view, not just list view).
   - `--yes` full run only after both gates pass.
7. **Verify** — keys-only count, dashboard spot-check, partner sign-off.
8. **File follow-ups** — PITR ticket, cleanup-script guardrail ticket,
   postmortem under `documentation/process/incidents/`.

## Reference material

- `documentation/bibliotheque/operations/dev-datastore-recovery-from-bq.md`
- `documentation/bibliotheque/stack/interactions-mv-schema-and-key.md`
- `tickets/SPV-92/tools/restore-mpa-mv-from-bq.py`

## Anti-goals

- Never rebuild by replaying through ERS — pollutes event store with fake
  ingest timestamps and triggers downstream fan-out.
- Never run the full write without the `--limit 1` manual gate, even under
  time pressure. A half-restored env with wrong-schema entities is worse than
  an honest fallback (asking the partner to rerun their own mock generator).
- Never run without explicit `--org` scope.
