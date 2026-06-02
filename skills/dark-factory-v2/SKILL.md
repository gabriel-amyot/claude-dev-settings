---
name: dark-factory-v2
version: "0.2.0"
description: "EXPERIMENTAL v2 of the ticket-to-dev factory, orchestrated by the Workflow tool instead of prose. Gates are code (un-skippable), with a human concierge gate at the front. Seed scope: backend/Java floor only, single-pass review + QA. The workflow does code work and pushes the branch (terminal state READY_TO_SHIP); the main loop creates the MR + Jira comment and runs post-merge validate. Triggers on: '/dark-factory-v2', 'dark factory v2', 'factory v2'. Klever."
user_invocable: true
nav:
  bay: build
  when: "Run a backend/Java Klever ticket through the v2 (workflow-orchestrated) factory. Code gates, front human gate."
  when_not: "Frontend/SQL/scripting tickets (not built yet - use v1 /dark-factory). Multi-ticket epics (use v1). Quick ship (use /autonomous-ticket-ship)."
  personas: [amelia, quinn, winston]
  org: [klever]
---

# Dark Factory v2 (seed)

Ticket-to-dev factory, rebuilt on the **Workflow tool**. Orchestration is a deterministic script; the
phase gates are JavaScript, not prose, so no step can be skipped or self-certified past. A human
concierge gate at the front stops for the engineer on spec/context/prereq/infra decisions.

**Seed scope:** one **backend/Java** floor, single-pass review + QA, one ticket at a time. Other floors
and added rigor are on the roadmap (`docs/roadmap.md`). v1 (`/dark-factory`) stays the fallback and the
benchmark baseline.

**Design:** `docs/seed-spec-v1.md` · **Decision:** `docs/adr/ADR-001-...md` · **Why/limits:**
`docs/grounding-and-decisions.md` · **Review fixes:** `docs/review-findings-v0.1.0.md`

## Division of labor (important)

The **workflow** does the code work: concierge → design → grill → implement (TDD, execution check,
**pushes the feature branch**) → review → QA → ship-prep (version bump + push). It ends at
`READY_TO_SHIP`. The **main loop** (this conversational context) does the things a workflow agent
can't safely do: create the MR (`/klever-mr`), post the Jira comment (`/post-comment`), transition the
ticket, and — after the human merges — run post-merge validate (contract 8). This split is forced by
verified Workflow-API limits (skills aren't reliably callable inside an agent; no native wait).

## Files

- `dark-factory-v2.workflow.js` — the orchestrator (steps + JS gates).
- `contracts/*.md` — per-phase instructions the worker agents read and execute.

## Invocation

```
/dark-factory-v2 <TICKET>      # e.g. /dark-factory-v2 KTP-728
```

## How to run it

1. **Resolve** org from the ticket key (KTP/INS → klever).
2. **Invoke the Workflow tool** with:
   - `scriptPath`: `/Users/gabrielamyot/.claude/skills/dark-factory-v2/dark-factory-v2.workflow.js`
   - `args`: `{ "ticket": "<TICKET>", "org": "<org>" }`
   This is explicit Workflow opt-in (the user invoked this skill). **Note the returned `runId`** — you
   need it to resume after the human gate.
3. **Handle the workflow's return `status`:**
   - `AWAITING_HUMAN` → present each item in `decision_packet` via `AskUserQuestion`. Collect answers.
     **Re-invoke the Workflow** with `resumeFromRunId: <runId>` and
     `args: { ticket, org, humanDecisions: { <id>: <answer>, ... } }`.
   - `BLOCKED_NEEDS_HUMAN_AGAIN` → answers were supplied but the concierge still needs a human. Do NOT
     re-loop blindly; show the open questions, refine with the user, and only then resume.
   - `BLOCKED_SPEC_QUALITY` → report the concierge findings; suggest a Jira clarification (don't post
     automatically).
   - `HALT_DESIGN_STUCK` / `HALT_GRILL_UNWORKABLE` / `HALT_IMPLEMENT_STUCK` → report the reason; the
     code (if any) stays on its branch. Operator decides.
   - `BLOCKED_REVIEW_CRITICAL` → report the open CRITICAL finding(s); unshipped.
   - `HALT_PRESHIP` → report `blockers` (execution not verified / branch not pushed / open CRITICAL /
     QA not green); do not ship.
   - `HALT_SHIPPREP_FAILED` / `HALT_AGENT_SKIPPED` → report; nothing shipped.
   - `READY_TO_SHIP` → the code is done, reviewed, QA'd, version-bumped, and pushed. Now the MAIN LOOP:
     1. `/klever-mr` (no auto-merge) for `branch`.
     2. `/post-comment` — Jira comment: MR link + AC summary + QA evidence highlights.
     3. Transition the ticket to In Review/Testing (ceiling).
     4. After the human merges: run contract 8 (`docs`/`contracts/8-validate.md`) as a post-merge step.
4. **Write a short run note** to the ticket folder (status, MR if any, what the gates did).

## Guardrails

No direct push to dev/main; no destructive git; DAC repos dev-only; ticket transition ceiling =
In Review/Testing; all external posts via `/post-comment`. The workflow's JS gates enforce
execution-verified, branch-pushed, zero-open-CRITICAL, evidence-backed QA, and QA-green-before-ship,
plus the front human gate.

## Benchmark note

v1 and v2 are separate skills so the same ticket can run through both (two terminals) to compare
results and cost. See `docs/seed-spec-v1.md` → "Optional post-v1 validation".

## Status

`0.2.0` — seed, reviewed (adversarial-cascade + prompt specialist) and fixed, **not yet run on a real
ticket**. First run target: KTP-728 (read its handoff only at run time, per the anti-overfitting rule).
