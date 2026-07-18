---
name: sprint-close
description: "Validate (and optionally close) sprint tickets with adversarial-gated, evidence-backed Jira comments. Generates FRESH per-AC proof live (ui-probe for frontend, API probe for backend, bq for data, grep for code), runs parallel adversarial reviews, then posts an evidence comment on EVERY reviewed ticket: PASS with proof, FAIL with what broke, CANT-TEST with why. Input: sprint name or ticket list. Returns: per-ticket verdicts + posted comments + coverage classification."
user_invocable: true
nav:
  bay: ship
  when: "Validate sprint tickets with fresh live proof and adversarial-gated evidence-backed Jira comments; optionally close them."
  when_not: "Sprint management/tracking (use /klever-sprint-mgmt). Archiving (use /archive). Pure live UI inspection with no posting (use /ui-probe)."
---

# Sprint Ticket Validation & Closure

Validate a batch of sprint tickets by generating **fresh live proof** per acceptance criterion, gate it through adversarial review, post an evidence comment on every ticket, and (in close mode) transition the closeable ones.

**Two modes:**
- **validate-only** (default for in-progress / mixed sprints): generate proof, classify each AC PASS / FAIL / CANT-TEST, post an evidence comment per ticket. Does NOT transition status. Use for the recurring "review every ticket and prove where it stands" sweep.
- **close**: everything validate-only does, plus the closeable-status gate, FAIL hard-gate, and transition to Done. Use when actually closing the sprint.

**Usage:**
```
/sprint-close --validate KTP-754 KTP-779 KTP-758   # Validate-only sweep: prove pass/fail/can't-test, post evidence, no transition
/sprint-close --validate --project KTP --sprint current   # Validate every ticket in the current sprint
/sprint-close KTP-328 KTP-337                       # Close mode: validate + close specific tickets
/sprint-close --close --project KTP --sprint current      # Close all "In review/testing" tickets
```

**Posting policy (both modes):** post an evidence comment on EVERY reviewed ticket — PASS with proof, FAIL with the failing observation, CANT-TEST with the blocker. All posts go through `/post-comment` (draft → preview → explicit approval → post). Passing tickets are not silently skipped.

## Prerequisites

- Jira access configured (`/jira` skill working)
- `/post-comment` skill available
- Ticket folders exist in project-management with reports/evidence
- Read `~/.claude/library/context/ticket-quality-standards.md` for quality gate rules

## Workflow

### Phase 1: Fetch Jira State

For each ticket, use `/jira get {KEY} --full --org {org}` to retrieve:
- Current status. **close mode:** must be "In review/testing" or equivalent. **validate-only mode:** any status is fine (you validate in-progress and to-do tickets too; a TO-DO ticket simply yields CANT-TEST(not-started) for most ACs, which is itself a useful, honest result).
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

### Phase 2a: Live Evidence Generation (NEW)

**Generate fresh proof per AC.** Do not rely only on evidence already on disk — exercise the live system. Load `live-evidence-probes.md` (in this skill folder) for the full routing table, the backend-probe procedure, and the Klever setup (JDK17, Placer/Goldfish creds, dev BQ, ui-probe auth caveats).

For each ticket, for each AC:
1. **Classify** the AC: frontend / backend / data / code / manual.
2. **Route the probe:**
   - frontend → `ui-probe` against the user's authenticated **dev** tab (preferred) → **save a screenshot** to `tickets/KTP/{EPIC}/{KEY}/design/screenshots/{KEY}-AC{n}-{date}.png`
   - backend → API probe (bring up `app-proximity-report` on :8097 per the companion, or hit dev) → save response log
   - data → `bq query` against dev BQ → save result
   - code → `grep`/`rg` → save matched/absent pattern
   - manual → CANT-TEST(needs-human) unless a human is in the loop
3. **Assign a verdict:** PASS (with artifact), FAIL (with the failing observation), or CANT-TEST (with the blocker + what was attempted). Every verdict must point to an artifact on disk.
4. Write the per-ticket bundle: `tickets/KTP/{EPIC}/{KEY}/reports/reviews/{KEY}-validation-{date}.md` (per-AC verdict table + artifact links) plus the screenshots/logs.

This bundle is the input to Phase 2 (adversarial judge) and Phase 3 (the evidence comment). A frontend PASS without a saved screenshot is not a PASS — downgrade to CANT-TEST until captured.

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

No `[automated]`/persona header. Post as Gabriel, in his voice (see JIRA_AGENT_RULES Rule 3).

### Phase 4: Post and (close mode only) Transition

An evidence comment is posted for **every reviewed ticket**, regardless of verdict:
- all-PASS → the "what was done / why it's closeable" comment
- any FAIL → a comment stating which AC failed and the failing observation (screenshot/response/query)
- any CANT-TEST → a comment stating which AC couldn't be exercised and the blocker

For each ticket, sequentially:
1. Write draft to `tickets/{TICKET}/reports/status/{validation|closing}-comment-draft-{date}.md`
2. Preview the rendered comment to the user
3. Wait for explicit approval via `AskUserQuestion`
4. Post to Jira via `/post-comment` (which handles the draft→preview→approval→audit pipeline)
5. **close mode only:** if all-PASS (or user-approved overrides), transition to Done via `/jira transition`. **validate-only mode: never transition** — the comment stands on its own. Respect the status ceiling (never beyond In review/testing without explicit user request).

**Decision gates:**
- If adversarial returned FAIL on any AC: this ticket should not have reached Phase 4. If it did, STOP. This is a workflow violation. Do not transition.
- If adversarial returned BLOCKED and user approved override in Phase 2.5: proceed with override noted in comment
- If parent ticket has open sub-tasks: post status comment only, do not close
- If Jira ACs differ from local ACs: flag the discrepancy, use Jira as source of truth

### Phase 5: Spillover Handoff

After all tickets are processed, invoke `/spillover-scan` to aggregate findings. If the user has not specified a tracking ticket, ask which ticket should receive the spillover findings.

## Verdict & Coverage Classification Reference

Phase 2a assigns a **verdict** per AC; Phase 3 maps it to a **coverage label** in the comment:

| Verdict (2a) | Coverage label (comment) | Meaning | Example |
|--------------|--------------------------|---------|---------|
| PASS | VERIFIED | Observed working end-to-end with a fresh artifact | ui-probe screenshot shows pins; API probe got 200 + correct fields; bq returned the rows |
| PASS (no live exec) | CODE VERIFIED | Unit test passes, no live observation | Unit test captures SQL string, asserts columns |
| FAIL | FAIL | Observed NOT working | Screenshot of the bug; 4xx/5xx body; wrong/empty query result |
| CANT-TEST | BLOCKED | Could not be exercised; the blocker is itself shown | Needs real BQ data not present; infra down; needs human on demo.dev; ticket not started |

Never conflate CODE VERIFIED with VERIFIED. Learned from INS-205 session 2026-03-27: coverage was inflated from 36% to 86% by relabeling "unit test exists" as "PASS." A FRONTEND PASS requires a saved screenshot; without it, downgrade to CANT-TEST.

## Changelog

- **2026-06-08:** Added validate-only mode + Phase 2a (Live Evidence Generation) that generates fresh per-AC proof by routing to ui-probe / API probe / bq / grep (see `live-evidence-probes.md`). Posting policy now covers every reviewed ticket (PASS/FAIL/CANT-TEST), not only closeable ones. Added the FAIL and CANT-TEST verdicts and the backend-probe procedure (the previously-missing gap).

## Anti-patterns

- Do not close tickets without adversarial review
- Do not mention local ticket folder paths in Jira comments
- Do not mention autonomous tooling (night-crawls, agents, etc.) in external comments
- Do not close parent tickets while sub-tasks are still open
- Do not silently drop adversarial findings. Track them via `/spillover-scan`
- Do not proceed to Phase 3 before all Phase 2 adversarial agents have returned results
- Do not transition a ticket to Done when any AC has a FAIL verdict without explicit user override
- Do not treat adversarial review as informational. It is a blocking gate
