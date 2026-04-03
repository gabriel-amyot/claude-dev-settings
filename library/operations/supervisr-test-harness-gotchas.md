# Supervisr Test Harness Gotchas

Hard-won operational knowledge from building and running the SPV-3 test harness. Every entry here caused a debugging session.

## Architecture

- **DTU (Dial Test Utility):** Mock Retell AI at port 4010. Fires webhook lifecycle: `call_started` → `call_ended` → `call_analyzed`. Supports scenarios with matchers (`agent_id`, `customer_number`, `lead_uuid`, `nth_call`). Scenarios have either `error` or `webhook` config (mutually exclusive).
- **Harness bypass:** retell-service direct-POSTs disposition to lead-lifecycle (no PubSub). retell-service lacks `spring-cloud-gcp-pubsub` in pom.xml.
- **EQS propagation gap:** EQS reads from a separate Datastore projection not updated by lead-lifecycle disposition events. Known service-level gap.

## Shell Scripting

**`set -euo pipefail` + `grep` on empty input = silent script exit.**
Always add `|| echo "0"` or `|| true` after grep in pipelines. An empty grep match returns exit code 1, which `-e` treats as a fatal error.

## DTU

**Scenario `arguments` field is `Map<String, Object>`, not a JSON string.**
Jackson rejects strings. Pass a JSON object, not `"{\"key\": \"value\"}"`.

**`analysisDelivered` is gated on 2xx from retell-service.**
Non-2xx response from retell-service means analysis is NOT delivered. DTU silently skips it.

**After DTU reset, tick processes ALL pending leads.**
Not just the target SBE's lead. Phone-specific polling is needed to isolate test results.

## Curl

**`curl -sf` hides HTTP status on error.**
Use `-o file -w "%{http_code}"` when you need both body and status code.

## Datastore

**Emulator: `SELECT __key__ FROM kind` returns 0 results.**
But `SELECT * FROM kind` works. Always use `SELECT *` with the Datastore emulator.

**LLS uses `lead_lifecycle` namespace.**
Queries without specifying this namespace return 0 results. See `operations/supervisr-datastore-topology-environments.md`.

**`updateLead(updates: { nextCallAt: null })` is a no-op.**
Service ignores null values in updates. To clear backoff, use a past date like `"2020-01-01T00:00:00Z"`.

## GraphQL

**Query is `lead(uuid:)` NOT `getLead(uuid:)`.**
Response key is `data.lead`, not `data.getLead`.

**Mutation `updateLead` uses `updates:` parameter, not `input:`.**

## Service Behavior

**Stale recovery reads in-memory `updatedAt`, not Datastore.**
Need DTU hang scenario or service endpoint for true stale recovery testing.

## Harness Lifecycle

**Always shut down harness-driver agents at the end of a crawl.**
They hang idle otherwise, consuming resources.

## Repo Locations

| Component | Path |
|-----------|------|
| Harness scripts | `project-management/tools/test-harness/scripts/` |
| DTU source | `project-management/tools/test-harness/dtu/` |
| docker-compose | `project-management/tools/test-harness/docker-compose.yml` |
| SBE specs | `app/micro-services/lead-lifecycle-service/agent-os/sbe/` |
| Nuke tool | `project-management/tools/datastore-ops/nuke_entities.py` |
| Extract tool | `project-management/tools/datastore-extract/extract_dev_data.py` |
