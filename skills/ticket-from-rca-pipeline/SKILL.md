---
name: ticket-from-rca-pipeline
description: Parses RCA incidental findings into verified Jira tickets. Trigger phrases: "create tickets from RCA", "file the incidental findings", "spin these into tickets", "ticket the parked findings".
---

# ticket-from-rca-pipeline

Converts RCA incidental findings into verified, AC-quality Jira tickets through a nine-step pipeline: parse, draft, Leo gate, human confirmation, Jira creation, adversarial codebase verification, rewrite with corrections, update Jira, and report keys.

See the pipeline quick-reference at `references/pipeline-steps.md`.

---

## When to Use This Skill

Invoke this skill when an incident investigation, tracer fire, or debugging session surfaces issues that are real but out-of-scope for the current ticket. The canonical input is a markdown file (e.g., `incidental-findings.md`, `rca-notes.md`) listing parked observations. The canonical output is a set of Jira ticket keys grounded against the actual codebase.

**Trigger phrases:**
- "create tickets from RCA"
- "file the incidental findings"
- "spin these into tickets"
- "ticket the parked findings"
- "turn the parked issues into Jira tickets"

---

## Usage

```
/ticket-from-rca-pipeline path/to/rca-or-incidental-findings.md [--org supervisrai|klever] [--project SPV|KTP]
```

Arguments:
- `path/to/rca-or-incidental-findings.md` — required. Path to the RCA or incidental findings markdown file.
- `--org` — optional. Defaults to the current working directory org context.
- `--project` — optional. Defaults to the project key inferred from the source ticket in the RCA file.

---

## Pipeline

The nine steps below are ordered. Steps 1-3 form the **Draft phase**. Step 4 is the **Human gate**. Step 5 is **Jira creation**. Steps 6-8 form the **Adversarial phase**. Step 9 is **Report**.

### Step 1 — Parse RCA Findings

**Input:** RCA or incidental-findings markdown file.

Read the file. Extract every distinct finding into a structured list. For each finding, capture:

- **Title** — a concise, imperative label (e.g., "Backup missing before DatastoreWriter mutations").
- **Context** — which ticket, service, or incident surfaced this finding.
- **Observation** — what was seen, concretely. Quote exact error messages, log lines, or code snippets when available.
- **Suspected cause** — the mechanism believed to be responsible. Mark it as suspected, not confirmed.
- **Related tickets** — any Jira keys already linked, even loosely.
- **Severity signal** — words like "data loss", "security", "silent failure", "regression" get flagged as HIGH priority candidates.

If the source file is poorly structured (prose narrative rather than a list), scan for paragraph breaks, bullet transitions, or numbered items. Each distinct issue becomes one finding. When two findings share a root cause, keep them separate but note the shared cause in both.

**Error handling:** If the file does not exist or is empty, stop and ask the user for the correct path. Do not proceed with zero findings.

---

### Step 2 — Draft Tickets

**Input:** Structured findings list from Step 1.

For each finding, draft a Jira ticket body using the standard template:

```
## Intent
[One sentence: what problem does this ticket solve, and why does it matter.]

## Acceptance Criteria

**Given** [precondition or system state],
**When** [the action or trigger],
**Then** [the observable, testable outcome].

[Repeat for each distinct AC. Minimum one. Maximum five per ticket. If more are needed, split the ticket.]

## Blockers / Dependencies
[List known blockers. Write "None identified." if none.]

## References
[Source RCA file path. Related Jira keys. Relevant file paths or line numbers if known.]
```

**Quality bar at draft time:**
- The Intent must identify a problem, not describe a task ("Ensure backup exists before mutation" not "Add backup logic to writer").
- Each AC must be testable by a human reading a diff or running a test. Vague outcomes ("system behaves correctly") are not acceptable.
- Do not invent numeric thresholds or SLAs not present in the source material. Write "TBD" instead.

---

### Step 3 — Leo AC Gate

**Input:** Drafted ticket bodies from Step 2.

Apply a Leo-style AC quality review to every draft before presenting them to the user. Leo reviews are adversarial: assume the draft is wrong until proven otherwise.

Check each ticket for the following failure modes:

| Failure Mode | Signal | Action |
|---|---|---|
| Vague outcome | "works correctly", "functions as expected", "behaves properly" | Rewrite to name the specific observable |
| Untestable conditional | "should", "may", "might" | Replace with "shall" or restructure as a definite Given/When/Then |
| Task-list AC | "Add X to Y", "Implement Z" | Rewrite as a system behavior statement |
| Missing decision gate | AC depends on a design choice not yet made | Flag as "AC BLOCKED — decision needed: [question]" |
| Fabricated numbers | Any SLA, duration, or count not in the source material | Replace with "TBD" |
| Intent is a task | "Implement backup for DatastoreWriter" | Rewrite: "Prevent silent data loss in DatastoreWriter mutations" |

After review, mark each ticket as PASS or NEEDS_REVISION. Rewrite NEEDS_REVISION tickets before moving to Step 4. If a ticket cannot be rewritten to pass without information only the user has, mark it as BLOCKED and flag it explicitly.

---

### Step 4 — Human Confirmation Gate

**Input:** Leo-reviewed ticket drafts.

Present all drafts to the user in a readable summary. For each ticket, show:

1. Proposed title
2. Intent (one sentence)
3. AC count
4. Leo verdict (PASS / BLOCKED)
5. Any flags or questions requiring user input

Wait for explicit approval before proceeding. Do not batch-create in Jira without a clear "go ahead" or equivalent confirmation.

**Gate questions to ask:**
- Are there any findings that should be merged into a single ticket?
- Are there any findings that should be deferred rather than filed?
- Is the target project and epic correct for each ticket?
- Are there assignees or labels to attach?

Incorporate any changes the user requests, then confirm the final list before Step 5.

---

### Step 5 — Create in Jira

**Input:** Confirmed ticket list from Step 4.

Batch-create via the `/jira` skill. Use the `create` subcommand. Pass `--org` and `--project` flags as resolved in Step 1. Apply the `[automated]` header convention if required by the org's Jira skill gotchas.

After creation, record each returned ticket key alongside its source finding. This mapping is used in Step 8 (update) and Step 9 (report).

**Error handling:** If a ticket fails to create, log the failure with the full error. Continue creating remaining tickets. At the end of Step 5, report any failures to the user before proceeding to the adversarial phase.

---

### Step 6 — Adversarial Codebase Verification

**Input:** Created Jira tickets (keys + descriptions) from Step 5.

Spawn one Explore agent per ticket. Each agent's mission: verify every factual claim in the ticket description against the local repos.

Claims to verify:
- Entity names and field names (do they exist in the codebase?)
- Schema fields (are they present in the GraphQL schema, Datastore entity, or data model?)
- Publisher/subscriber behavior (does the code actually do what the ticket says it does?)
- Config semantics (does the named config key exist and does it mean what the ticket implies?)
- File paths or line numbers cited in References

Each agent returns a findings report with severity classification:

| Severity | Meaning |
|---|---|
| CRITICAL | Factual claim is demonstrably false. Ticket describes a non-existent field, wrong service, or incorrect behavior. |
| HIGH | Claim is probably wrong or significantly misleading. Requires correction before the ticket is actionable. |
| MEDIUM | Claim is imprecise but approximately correct. Should be tightened. |
| LOW | Minor wording issue or missing citation. Cosmetic. |

**Error handling:** If an agent cannot locate the relevant repo or file (e.g., the code is in an uncloned repo), mark the claim as UNVERIFIED and note what repo is needed. Do not fabricate a verification result.

---

### Step 7 — Rewrite with Corrections

**Input:** Adversarial findings from Step 6.

Fix every CRITICAL and HIGH finding. For each:
- Replace incorrect entity/field names with the verified names.
- Correct service attribution.
- Anchor vague behavioral claims to actual code paths (cite file path and line number when possible).
- Preserve original intent — do not change what the ticket is solving, only correct how it describes the system.

Apply MEDIUM fixes at your discretion. Flag LOW findings in a comment for the user but do not block on them.

After rewriting, run the Leo gate again (abbreviated pass — focus only on changed sections). Confirm each rewritten ticket still passes the AC quality bar.

---

### Step 8 — Update Jira

**Input:** Corrected ticket bodies from Step 7 and the key mapping from Step 5.

For each ticket with CRITICAL or HIGH corrections, update the Jira description via the `/jira` skill `edit-description` (or equivalent) subcommand. Post a comment on each updated ticket noting that an adversarial codebase review was performed and corrections were applied.

**Error handling:** If an update fails, log the failure and continue. Report all failures in Step 9.

---

### Step 9 — Report Keys

**Input:** Complete key mapping and any failures from Steps 5 and 8.

Print a final summary to the user:

```
## ticket-from-rca-pipeline — Complete

Source: [path to RCA file]
Tickets created: N

| Key     | Title                                      | Leo | Adversarial |
|---------|--------------------------------------------|-----|-------------|
| SPV-### | [title]                                    | ✓   | CRITICAL fixed |
| SPV-### | [title]                                    | ✓   | PASS        |

Failures: [list any Jira creation or update failures]

Next steps:
- Add these keys to the source RCA notes.
- Assign and prioritize in sprint planning.
- Any BLOCKED tickets require user decisions before they can be scheduled.
```

Provide the ticket keys in a format the user can paste directly into their RCA document or Jira epic.

---

## Failure Modes and Recovery

| Failure | Recovery |
|---|---|
| RCA file not found | Stop. Ask for correct path. |
| Zero findings extracted | Stop. Ask user to confirm file or provide structured input. |
| Leo gate cannot resolve a BLOCKED ticket | Flag to user in Step 4. Proceed with remaining tickets. |
| Jira creation fails | Log failure. Continue with remaining tickets. Report in Step 9. |
| Explore agent cannot find a repo | Mark claim UNVERIFIED. Note which repo is missing. Do not fabricate. |
| Jira update fails in Step 8 | Log failure. Report in Step 9. User can manually apply corrections from Step 7 output. |

---

## Dependencies

- `/jira` skill — ticket creation (Step 5), ticket update (Step 8)
- `/create-tickets` skill — may be used for batch creation scaffolding in Step 5 if preferred
- Explore agents — adversarial codebase verification (Step 6)
- Leo AC quality review logic — applied inline in Step 3 and Step 7
- `references/pipeline-steps.md` — quick-reference diagram for this pipeline

---

## Notes

- This skill is global and org-agnostic. It works for any org with a configured `/jira` skill and local repos.
- Never post to Jira without Step 4 human confirmation. The gate is not optional.
- Never fabricate verification results in Step 6. UNVERIFIED is a valid and honest outcome.
- This skill respects the "no fabricated numbers in tickets" rule. Any SLA, threshold, or count not in the source RCA material must be written as "TBD".
