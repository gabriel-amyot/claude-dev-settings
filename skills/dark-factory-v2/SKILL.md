---
name: dark-factory-v2
version: "0.1.0"
description: "EXPERIMENTAL v2 of the ticket-to-dev factory, orchestrated by the Workflow tool instead of prose. Gates are code (un-skippable), with a human concierge gate at the front. Seed scope: backend/Java floor only, single-pass review + QA. Runs one ticket end-to-end. Triggers on: '/dark-factory-v2', 'dark factory v2', 'factory v2'. Klever."
user_invocable: true
nav:
  bay: build
  when: "Run a backend/Java Klever ticket through the v2 (workflow-orchestrated) factory. Code gates, front human gate."
  when_not: "Frontend/SQL/scripting tickets (not built yet - use v1 /dark-factory). Multi-ticket epics (use v1). Quick ship (use /autonomous-ticket-ship)."
  personas: [amelia, quinn, winston]
  org: [klever]
---

# Dark Factory v2 (seed)

Ticket-to-dev factory, rebuilt on the **Workflow tool**. The orchestration is a deterministic
script; the phase gates are JavaScript, not prose, so no step can be skipped or self-certified past.
A human concierge gate at the front stops for the engineer on spec/context/prereq/infra decisions.

**Seed scope:** one **backend/Java** floor, single-pass review + QA, one ticket at a time. Other
floors and added rigor are on the roadmap (`docs/roadmap.md`). v1 (`/dark-factory`) stays the
fallback and the benchmark baseline.

**Design:** `docs/seed-spec-v1.md` · **Decision:** `docs/adr/ADR-001-...md` · **Why/limits:**
`docs/grounding-and-decisions.md`

## Files

- `dark-factory-v2.workflow.js` — the orchestrator (steps + gates + human-gate split).
- `contracts/*.md` — per-phase instructions the worker agents read and execute.

## Invocation

```
/dark-factory-v2 <TICKET>      # e.g. /dark-factory-v2 KTP-728
```

## How to run it

1. **Resolve** the org and ticket folder from the ticket key (KTP/INS → klever).
2. **Invoke the Workflow tool** with:
   - `scriptPath`: `~/.claude/skills/dark-factory-v2/dark-factory-v2.workflow.js`
   - `args`: `{ "ticket": "<TICKET>", "org": "<org>" }`
   This is explicit Workflow opt-in (the user invoked this skill).
3. **Handle the workflow's return:**
   - `AWAITING_HUMAN` → the concierge needs decisions. Present each item in `decision_packet` to the
     user via `AskUserQuestion`. Collect answers. **Re-invoke the Workflow** with `resumeFromRunId`
     (the runId from the first invocation) and `args.humanDecisions = { <id>: <answer>, ... }`. The
     concierge result is cached on resume, so this is cheap; the run continues to Design.
   - `BLOCKED_SPEC_QUALITY` → report the concierge's findings; do not proceed. Suggest a Jira
     clarification comment (do not post automatically).
   - `BLOCKED_REVIEW_CRITICAL` → report the open CRITICAL finding(s); the code stays on the branch,
     unshipped.
   - `HALT_PRESHIP` → report the `blockers` (execution not verified / open CRITICAL / QA not green);
     do not ship.
   - `COMPLETE` → report the MR URL, `qa_capped`, and `execution_verified`. The human merges the MR.
4. **Write a short run note** to the ticket folder (what ran, the return status, the MR if any).

## Guardrails

Same as v1: no direct push to dev/main, no destructive git, DAC repos dev-only, no IAM changes,
ticket transition ceiling = In Review/Testing, all external posts via `/post-comment`. The gates in
the workflow script enforce execution-verified, zero-open-CRITICAL, QA-green-before-ship, and the
front human gate.

## Benchmark note

v1 and v2 are intentionally separate skills so the same ticket can be run through both (two
terminals) to compare results and cost. See `docs/seed-spec-v1.md` → "Optional post-v1 validation".

## Status

`0.1.0` — seed, not yet run on a real ticket. First run target: KTP-728 (read its handoff only at
run time, per the anti-overfitting rule). Review the workflow script + contracts before first run.
