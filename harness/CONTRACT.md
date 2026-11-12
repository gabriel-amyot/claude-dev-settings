# Harness implementation contract

Approved by Gabriel on 2026-10-26: shared SQLite catalog, bridges preserving producer outputs, rigid separate schemas and a generated HTML/CSS view. No server, framework or JavaScript required. Existing eval evidence stays authoritative in its producer location.

## Module boundaries

- store.py + schema/001.sql: standard-library SQLite domain store. Python schema validation, STRICT tables, FK/unique/check constraints, short transactions, busy timeout, immutable events, idempotent replay. CLI helper is the supported write path, not a security sandbox against arbitrary local filesystem access.
- bridges.py: inventory, Claude/Codex evidence collection, legacy report and eval/factory import. Do not run workflows, evals, shells embedded in skill text, or transmit data. Metadata/structured events only. Source paths + fingerprints + observation time required. Never count quoted payloads or mere static references as executions.
- render.py: generated read-only HTML/CSS overview and per-capability detail pages. Escape all source text, stable safe filenames, evidence links, last refresh and coverage. No script/network resources. Atomic refresh. Preserve source reports.
- catalog.py: CLI orchestrates refresh, render, record, query, backup. Processes can call a small emit helper after writing their own artifacts, with errors surfaced separately without changing existing result/exit semantics.
- tests/: actual semantic/concurrency/idempotency/import/render checks using temporary fixtures. No live eval suites, session ledger mutation, external posts or deployments.

## Store API for parallel implementation

`Store(db_path)` initializes and opens a row-factory SQLite connection as `.conn`; context manager closes it.
`store.record(kind, payload, producer="agent") -> bool`: true on a new/changed record, false on identical replay. Unknown keys or wrong types rejected. Same immutable event ID with changed content rejected. Valid write kinds: capability, availability, dependency, usage, friction, eval, outcome, decision, coverage, artifact.
`store.rows(sql, parameters=()) -> list[dict]`: read-only SELECT helper for view/queries.
`store.backup(path)` uses sqlite backup API for a consistent snapshot.
`utc_now()` and `stable_id(*parts)` helpers.

Payload fields (required unless marked ?; null optional fields accepted):
- capability: id, kind(skill|agent|hook|workflow), name, description, source_path, revision, discovered_at, group_name? (default ungrouped), active? bool(default true)
- availability: capability_id, host(claude|codex|shared|unknown), role, path, status(discovered|validated|blocked|unknown), observed_at, evidence
- dependency: capability_id, target_id, relationship(references|requires|delegates), evidence
- usage: id, capability_id, host, role, session_id, occurred_at, signal(invoked|loaded|historical_estimate), source_path, source_ref, revision?, outcome?(unknown|success|failure), count? int(default 1)
- friction: id, capability_id, host, role, session_id, occurred_at, summary, impact, evidence, status?(open|resolved; default open), resolves_id?
- eval: id, suite_id, capability_id, occurred_at, outcome(pass|fail|error|skipped|unknown), source_path, source_ref, revision?, host?(unknown default), layer?(unknown default), summary?
- eval_suite: id, suite_id, capability_id, layer, source_path, observed_at, runner?, last_green? (historical date, never a current-revision verdict)
- outcome: id, capability_id, occurred_at, status, source_path, source_ref, host?(unknown default), role?(unknown default), revision?, summary?
- decision: id, capability_id, occurred_at, action(keep|promote|polish|review|retire|prioritize|propose), status(proposed|approved), rationale, authority, evidence
- coverage: id, source, host, scope, since?, until?, observed_at, status(complete|partial|unavailable), detail
- artifact: id, kind, source_path, fingerprint, observed_at, summary?

Table names plural: capabilities, availability, dependencies, usage_events, frictions, eval_suites, eval_runs, outcomes, decisions, coverage, artifacts. Field names match payload except kind is absent from most tables. producer column on all tables.

Producer ownership: collector writes capability/availability/dependency/usage/outcome/coverage/eval_suite/artifact. eval-runner writes eval/artifact. agent writes friction and proposed decisions only. maintainer writes approved decisions and friction resolutions; bootstrap may seed capability metadata but should use collector. No agent eval passes or lifecycle retirement approvals. Any producer may add an artifact reference.

For updates: capabilities keyed id; availability keyed(capability_id,host,role,path); dependencies keyed(capability_id,target_id,relationship); coverage keyed id. Domain event tables otherwise immutable. Unknown foreign capability IDs should be rejected, so bridges inventory/register placeholders before events.

## Runtime locations

Source installed at ~/.claude-shared-config/harness. Default database and generated view under that harness/data and harness/view. Data and generated pages are ignored by Git; schema/code/docs/tests are versioned. Explicit --root, --db, --view, --home and --org klever options support fixtures and avoid reading other org transcripts. Shared/global metadata inventory is allowed; activity collection scoped to Klever unless explicitly overridden.

## Acceptance

- All available personal/project/plugin skill inventory deduplicated by canonical source path, archive/fixtures excluded and host/role/reference claims distinguished from observed use.
- Actual structured Claude tool calls, user slash invocations and Codex SKILL.md file reads collected separately; unsupported evidence remains unknown, imports idempotent.
- Existing eval and telemetry artifacts bridged without rewriting raw data or falsifying historical revision coverage.
- Producers emit into this shared contract, and existing outputs/return codes remain compatible.
- Static view opens locally, overview -> detail -> original artifacts, states coverage/staleness honestly.
- Supported append operations validate field/domain ownership and cannot let an agent approve retirement or forge an eval pass.
- Database snapshots exist before refreshing existing operational data; never Git-merge a live SQLite file.
