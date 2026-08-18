# Functional Test Report — ticket-from-rca-pipeline

**Date:** 2026-04-21
**Tester:** Claude (automated functional test)
**Skill version:** SKILL.md as read 2026-04-21

---

## Scenario

Parse SPV-141 incidental findings and execute Steps 1–3 (Draft phase) of the pipeline.

---

## Input

**File found:** Yes
**Path:** `/Users/gabrielamyot/Developer/supervisr-ai/project-management/tickets/SPV/SPV-141/rca-2026-04-11/incidental-findings.md`

---

## Steps Executed

### Step 1 — Parse RCA Findings

The file is semi-structured: seven numbered sections with headers and prose bodies. The skill's Step 1 guidance to "scan for paragraph breaks, bullet transitions, or numbered items" applies cleanly here.

**All seven findings extracted:**

| # | Title (extracted) | Status in file | Action |
|---|---|---|---|
| 1 | Missing push subscription for Compliance_Interaction_Persisted → LLS | FILED (Jira exists) | Skip |
| 2 | ERS pull-sub starvation when Cloud Run scales to zero | FILED as comment | Skip |
| 3 | `wakeErs()` cold-start trigger is ineffective | FILED as comment | Skip |
| 4 | Poison pill message in Compliance_Lead_Update (non-DreamPipe bare string) | NOT FILED | **Draft** |
| 5 | BigQuery `compliance.interaction_events` schema drift (3 missing fields) | NOT FILED | **Draft** |
| 6 | EQS silently ignores `sort` clauses in report queries | NOT FILED | **Draft** |
| 7 | Stray LeadAdmin tracer lead in LLS state | NOT FILED — harmless, user decided leave as-is | **Flag, no ticket** |

**Actionable findings:** 3 (findings 4, 5, 6).
Finding 7 carries an explicit user decision (leave as-is) and severity label (harmless). Step 1 severity signal check: Finding 4 contains "nacks" and "DLQ" (silent redelivery loop) — flagged as potential HIGH. Finding 6 contains "non-deterministic" and "latent risk" — flagged as MEDIUM. Finding 5 is informational/follow-up — LOW.

---

### Step 2 — Draft Tickets

---

#### Draft A — Finding 4: Poison Pill in Compliance_Lead_Update

```
## Intent
Prevent ERS from endlessly nacking a malformed bare-string message in
Compliance_Lead_Update that consumes CPU and masks real failures via
repeated deserialization errors.

## Acceptance Criteria

**Given** the `Compliance_Lead_Update` PubSub topic contains a message
whose body is a bare string (e.g., `'f2-probe'`) rather than a wrapped
DreamPipe payload,
**When** ERS attempts to deserialize the message,
**Then** the message is routed to a Dead Letter Queue (DLQ) instead of
being nacked and redelivered indefinitely.

**Given** a DLQ is configured for `Compliance_Lead_Update`,
**When** a message is dead-lettered,
**Then** an observable signal (log entry, metric, or alert) is emitted
identifying the message ID and the deserialization error.

## Blockers / Dependencies
- DLQ provisioning is a DAC/IAC change — requires coordination with
  infrastructure team.
- Decision needed: manual removal of the current poison-pill message
  before or after DLQ is in place? (see References)

## References
- Source RCA: tickets/SPV/SPV-141/rca-2026-04-11/incidental-findings.md (finding 4)
- ERS deserialization path: EventReceiverFramework adapters/dto/EntityPropertyValue
- Related: SPV-141 (data loss), SPV-142 (ERS cold-start)
```

---

#### Draft B — Finding 5: BigQuery compliance.interaction_events Schema Drift

```
## Intent
Ensure the BigQuery `compliance.interaction_events` table schema
includes all expected fields from real Retell traffic before data
analysis or reporting relies on them.

## Acceptance Criteria

**Given** the `compliance.interaction_events` table in BigQuery,
**When** a query is run for rows with non-null `date`, `attemptNumber`,
and `source` fields from the last 30 days of real Retell traffic,
**Then** the query returns at least one row, confirming these fields are
populated by real traffic and not only by tracer runs.

**Given** ERS receives a Retell interaction payload containing `date`,
`attemptNumber`, and `source`,
**When** ERS writes the event to BigQuery,
**Then** all three fields are written to the corresponding columns
(no null substitution or silent drop).

## Blockers / Dependencies
- Requires real Retell traffic to have hit dev ERS recently. If ERS
  was cold for an extended period (see SPV-142), rows may be absent.
  Determine investigation window before scheduling.

## References
- Source RCA: tickets/SPV/SPV-141/rca-2026-04-11/incidental-findings.md (finding 5)
- ERS schema-update path: BigQueryService (auto-adds columns on unknown field)
- Related: SPV-142 (ERS cold-start finding)
- Follow-up query suggested in source: `compliance.interaction_events` BQ table
```

---

#### Draft C — Finding 6: EQS Silently Ignores sort Clauses

```
## Intent
Prevent EQS report queries from silently ignoring sort clauses,
which would cause any frontend feature relying on server-side ordering
to display results in non-deterministic order.

## Acceptance Criteria

**Given** a valid `InteractionReportResults` query with
`sort: [{ key: "startTime", order: 1 }]`,
**When** EQS executes the query against Datastore,
**Then** the returned results are ordered by `startTime` ascending,
verifiable by inspecting the `startTime` field across consecutive rows.

**Given** a valid `LeadReportResults` query with
`sort: [{ key: "attemptNumber", order: 1 }]`,
**When** EQS executes the query,
**Then** the returned results are ordered by `attemptNumber` ascending.

**Given** the EQS Datastore query builder,
**When** a sort clause is present in the GraphQL input,
**Then** the Datastore query includes a corresponding `addOrderBy`
(or equivalent) call — confirmed by a unit test asserting the
query builder output.

## Blockers / Dependencies
- Root cause is TBD: either missing Datastore composite indexes or
  sort clause not wired into query builder. Investigation required
  before AC-3 can be verified. Flag as AC BLOCKED — decision needed:
  which layer is the fix (Datastore index config vs. EQS query builder)?

## References
- Source RCA: tickets/SPV/SPV-141/rca-2026-04-11/incidental-findings.md (finding 6)
- EQS query types: InteractionReportResults, LeadReportResults
- Workaround in use: tracer.py Phase 4 sorts client-side by attemptNumber
- Related: SPV-141 (tracer work that surfaced this)
```

---

### Step 3 — Leo AC Gate

Each draft reviewed adversarially against the six failure modes.

---

#### Draft A — Poison Pill

| Check | Result |
|---|---|
| Vague outcome | PASS — outcomes name DLQ routing and observable signal |
| Untestable conditional | PASS — no "should/may/might" |
| Task-list AC | PASS — ACs describe system behavior, not implementation steps |
| Missing decision gate | FLAG — DLQ provisioning path is TBD (DAC/IAC). AC-1 cannot be verified until infra decision made. Marked in Blockers. |
| Fabricated numbers | PASS — no invented thresholds |
| Intent is a task | PASS — Intent names the problem (endless nacking, CPU waste, masked failures) |

**Verdict: PASS** (with one Blocker flag noted inline)

---

#### Draft B — BQ Schema Drift

| Check | Result |
|---|---|
| Vague outcome | NEEDS_REVISION — AC-1 says "at least one row" which is technically testable but relies on the external precondition that real traffic exists. Acceptable given the finding's investigation nature, but the 30-day window is a fabricated threshold not in the source. |
| Untestable conditional | PASS |
| Task-list AC | PASS |
| Missing decision gate | PASS — Blockers section flags the cold-ERS dependency |
| Fabricated numbers | FLAG — "last 30 days" is invented. Source says "recent rows." Must replace with "TBD" or "a time range determined at investigation time." |
| Intent is a task | PASS |

**Verdict: NEEDS_REVISION** — Replace "last 30 days" with "TBD (time range to be determined based on known last ERS activity)".

**Revised AC-1:**
> **Given** the `compliance.interaction_events` table in BigQuery,
> **When** a query is run for rows with non-null `date`, `attemptNumber`, and `source` fields from a time range covering known Retell traffic in dev (range TBD based on ERS uptime),
> **Then** the query returns at least one row, confirming these fields are populated by real Retell traffic.

**Post-revision verdict: PASS**

---

#### Draft C — EQS Sort

| Check | Result |
|---|---|
| Vague outcome | PASS — AC-1 and AC-2 name specific fields and specific order direction |
| Untestable conditional | PASS |
| Task-list AC | PASS — AC-3 is structural (unit test assertion on query builder output), not a task step |
| Missing decision gate | FLAG — AC-3 has an explicit "AC BLOCKED" note because root cause (index vs. query builder) is unresolved. Correctly handled per skill spec. |
| Fabricated numbers | PASS |
| Intent is a task | PASS — Intent names the silent misbehavior and the user-facing risk |

**Verdict: PASS** (AC-3 correctly marked BLOCKED pending investigation)

---

## Findings Extracted

**Total findings in file:** 7
**Already filed (skip):** 3 (findings 1, 2, 3)
**User-decided no-ticket:** 1 (finding 7 — harmless, explicit user decision)
**Actionable new tickets drafted:** 3 (findings 4, 5, 6)

---

## Draft Quality Assessment

| Draft | Leo Verdict | Key Issues |
|---|---|---|
| A — Poison Pill DLQ | PASS | One blocker flag (DLQ infra decision) correctly surfaced |
| B — BQ Schema Drift | NEEDS_REVISION → PASS after fix | Fabricated "30 days" threshold caught and corrected |
| C — EQS Sort Silent Failure | PASS | AC-3 correctly marked BLOCKED pending root cause investigation |

The skill's Step 2 quality bar ("do not invent numeric thresholds") was violated in Draft B's first pass. The Leo gate in Step 3 caught it correctly. The self-correction path (rewrite before presenting to user) worked as designed.

---

## Skill Behavior Observations

1. **File discovery.** The skill's error handling spec says "if the file does not exist, stop and ask." The actual path (`tickets/SPV/SPV-141/...`) uses a nested `SPV/` directory not mentioned in the SKILL.md usage example. The skill gives no guidance on path inference. An agent running blind would likely need to glob-search. The spec should mention that ticket paths may use org-prefix subdirectories.

2. **Already-filed finding handling.** The skill spec does not explicitly instruct the agent to skip findings already marked as "FILED." This is a gap: a naive parser would draft duplicate tickets for findings 1, 2, and 3. In this test, the "FILED" label was used as a filter heuristic, but the skill should explicitly state "skip findings already marked as FILED or FILED as comment."

3. **User-decided no-ticket handling.** Finding 7 carries the explicit label "NOT FILED — harmless" with a documented user decision. The skill spec has no guidance for findings with existing user disposition. An agent should surface these at Step 4 for confirmation ("user previously decided no ticket — confirm or override?") rather than silently skipping. Flagged as a spec gap.

4. **Severity signal detection.** Step 1 asks to flag severity signals. Finding 4 ("nacks repeatedly", "every redelivery", "DLQ") maps to HIGH correctly. Finding 6 ("non-deterministic", "latent risk") maps to MEDIUM correctly. Finding 5 is an investigation prompt, not a confirmed bug — LOW is correct. The severity signals in the source text were clear and unambiguous.

5. **Step 4 gate is not exercised in this functional test** (by design — this test covers Steps 1–3 only). The human gate would be the natural stopping point before Jira creation.

---

## Grade

**PARTIAL**

**Rationale:** Steps 1–3 execute successfully against real data. The pipeline correctly parsed 3 actionable findings from 7 total (correctly skipping 3 already-filed and 1 user-decided). Draft quality was high enough that Leo only flagged one fabricated threshold (caught and corrected inline). The PARTIAL grade reflects two genuine spec gaps surfaced by the test:

1. No guidance on skipping already-filed findings (gap in Step 1).
2. No guidance on handling findings with explicit user disposition (gap in Steps 1/4).

Neither gap is a blocker in practice (an experienced agent infers both), but both would cause a naive agent to produce duplicate or incorrect ticket proposals. The skill's core value proposition — parse, draft, gate — works as designed. The gaps are documentation/spec holes, not logic failures.

**Recommended follow-up:** Update `SKILL.md` Step 1 to add two clauses: (a) skip findings marked FILED or already associated with a Jira key, and (b) surface findings with explicit user disposition ("leave as-is", "harmless") as a separate "deferred/user-decided" list at Step 4 rather than silently dropping them.
