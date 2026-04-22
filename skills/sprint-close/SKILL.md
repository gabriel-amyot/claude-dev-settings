---
name: sprint-close
description: "Validate and close sprint tickets with adversarial-gated, evidence-backed Jira comments. Fetches Jira state, runs parallel adversarial reviews, posts closing comments with AC-by-AC proof and honest coverage classifications. Input: sprint name or ticket list. Returns: closing comments posted per ticket with coverage classification."
user_invocable: true
---

# Sprint Ticket Closure

Validate and close a batch of sprint tickets following the adversarial-gated quality protocol.

**Usage:**
```
/sprint-close KTP-328 KTP-337 KTP-105       # Close specific tickets
/sprint-close --project KTP --sprint current # Close all "In review/testing" tickets in current sprint
```

## Prerequisites

- Jira access configured (`/jira` skill working)
- `/post-comment` skill available
- Ticket folders exist in project-management with reports/evidence
- Read `~/.claude/library/context/ticket-quality-standards.md` for quality gate rules

## Workflow

### Phase 1: Fetch Jira State

For each ticket, use `/jira get {KEY} --full --org {org}` to retrieve:
- Current status (must be "In review/testing" or equivalent)
- ACs from Jira description (source of truth)
- Sub-task structure (parent tickets cannot close while sub-tasks are open)
- Available transitions

Cross-reference Jira ACs against local AC files in `tickets/{TICKET}/jira/ac/`.

**Important:** When spawning haiku subagents for Jira, always pass `--org {org}` flag. Subagents run from the skill directory, outside the org auto-detection path.

Present a summary table to the user:

```
| Ticket | Status | Type | ACs | Closeable? |
|--------|--------|------|-----|------------|
```

Ask the user to confirm which tickets to proceed with.

### Phase 2: Parallel Adversarial Reviews

Launch one background adversarial agent per ticket. Each agent receives:
- The Jira ACs (source of truth)
- Available evidence (test results, implementation summaries, commit SHAs, UI test screenshots)
- The adversarial prompt: "For each AC, give a verdict: PASS, FAIL, or BLOCKED. Can this test pass with a broken service? Verify coverage labels: if evidence is a unit test, label must be CODE VERIFIED, not VERIFIED."

Evidence sources to reference (search in order):
1. `tickets/{TICKET}/reports/` (implementation summaries, reviews)
2. `tickets/{EPIC}/reports/testing/` (UI test results, screenshots)
3. `tickets/{EPIC}/reports/e2e-scripts/` (E2E test output)
4. Backend test results (Gradle/Maven output)

### Phase 2.5: Adversarial Synchronization Gate

**BLOCKING GATE.** Wait for ALL background adversarial agents launched in Phase 2 to return results. Do not proceed to Phase 3 until every agent has reported.

For each ticket, compile a verdict table:

| AC | Verdict | Finding |
|----|---------|---------|
| AC-1 | PASS/FAIL/BLOCKED | {summary} |

**Hard gate per ticket:**
- If ANY AC has verdict **FAIL**: present the verdict table and findings to the user. The ticket CANNOT proceed to Phase 3. The user must either:
  - (a) Resolve the failing AC (fix code, provide evidence, descope AC into a new ticket)
  - (b) Explicitly override with rationale (logged in the closing comment as "FAIL — overridden: {reason}")
- If ANY AC has verdict **BLOCKED**: ask user whether to close anyway or leave open
- If ALL ACs are **PASS**: proceed to Phase 3

**Timeout:** If an adversarial agent has not returned after 10 minutes, flag to user and ask whether to wait or skip that ticket.

**Headless/autonomous mode:** FAIL verdicts cannot be overridden without a human. The ticket stays open. Log the failure, write a report, move on to the next ticket.

### Phase 3: Draft Closing Comments

**Prerequisite:** Phase 2.5 must be complete for this ticket. Every ticket reaching this phase has either all-PASS verdicts or user-approved overrides for FAIL/BLOCKED ACs.

For each ticket, draft a Jira comment with three sections:

**h3. What was done**
- Per-AC summary of work delivered
- Each AC gets an honest coverage label:
  - **VERIFIED** = tested end-to-end (E2E script, UI test, or direct observation)
  - **CODE VERIFIED** = unit test passes but no E2E
  - **BLOCKED** = cannot test without infrastructure (staging, GCP, etc.)
- Never inflate coverage. Never label CODE VERIFIED as VERIFIED.

**h3. Why it's closeable**
- Test suite results (count, date)
- UI test results (UC references, screenshot filenames)
- Adversarial review verdict with accepted findings

**h3. References**
- Branch name(s) and integration branch
- Key commit SHAs
- New/modified classes and test classes
- No local file paths (ticket folders are local-only, not in Jira)

Add `_[automated] Posted by Gabriel via CI/QA tooling._` header.

### Phase 4: Post and Transition

For each ticket, sequentially:
1. Write draft to `tickets/{TICKET}/reports/status/closing-comment-draft-{date}.md`
2. Preview the rendered comment to the user
3. Wait for explicit approval via `AskUserQuestion`
4. Post to Jira via `/jira add-comment`
5. Transition to Done via `/jira transition`

**Decision gates:**
- If adversarial returned FAIL on any AC: this ticket should not have reached Phase 4. If it did, STOP. This is a workflow violation. Do not transition.
- If adversarial returned BLOCKED and user approved override in Phase 2.5: proceed with override noted in comment
- If parent ticket has open sub-tasks: post status comment only, do not close
- If Jira ACs differ from local ACs: flag the discrepancy, use Jira as source of truth

### Phase 5: Spillover Handoff

After all tickets are processed, invoke `/spillover-scan` to aggregate findings. If the user has not specified a tracking ticket, ask which ticket should receive the spillover findings.

## Coverage Classification Reference

| Label | Meaning | Example |
|-------|---------|---------|
| VERIFIED | Observed working end-to-end | UI test showed pins rendering, E2E script got 200 with correct fields |
| CODE VERIFIED | Unit test passes, no E2E | Unit test captures SQL string, asserts correct columns |
| BLOCKED | Cannot test without infrastructure | Needs real BQ data, staging deploy, or Demo environment |

Never conflate CODE VERIFIED with VERIFIED. Learned from INS-205 session 2026-03-27: coverage was inflated from 36% to 86% by relabeling "unit test exists" as "PASS."

## Anti-patterns

- Do not close tickets without adversarial review
- Do not mention local ticket folder paths in Jira comments
- Do not mention autonomous tooling (night-crawls, agents, etc.) in external comments
- Do not close parent tickets while sub-tasks are still open
- Do not silently drop adversarial findings. Track them via `/spillover-scan`
- Do not proceed to Phase 3 before all Phase 2 adversarial agents have returned results
- Do not transition a ticket to Done when any AC has a FAIL verdict without explicit user override
- Do not treat adversarial review as informational. It is a blocking gate
