# Contract 3 — Grill

Interrogate the implementation plan **before any code is written**. Surface gaps, unverified
assumptions, and missing edge cases. Cheaper to find a bad decision here than in Review or QA.

Adapted from the old skill's Phase 3 (GRILL). Pragmatic-architect (Winston) posture.

## Inputs

- The ticket-folder path is in your prompt. Read `<ticket_folder>/design/impl-plan.md`, plus the AC
  list and assumptions in `<ticket_folder>/analyst/`.

## Method — reason before you file

For EACH assumption you intend to challenge:
1. **State the assumption explicitly** (one line).
2. **Look for code evidence** that confirms or refutes it. Use git, not just local files:
   `git show origin/dev:<path>` to confirm a file/table/symbol exists on the branch you build against.
   Local working state can differ from `origin/dev`. (KTP-680 lesson.)
3. **Only then** file it as a resolved decision (with the file reference) or an unresolved gap.

Do not file snap verdicts on ambiguous code — do step 2 first.

When two approaches are genuinely equivalent, pick one and move on; tiebreaker: **prefer the approach
with fewer new files/classes.**

## Outputs (write to the ticket folder)

- `<ticket_folder>/design/grill-report.md` — resolved decisions, parked items, gaps.
- `<ticket_folder>/architecture/adr/ADR-draft-<topic>.md` — any non-obvious decision, in the repo's
  ADR format. NOT committed automatically.

## Unworkable-design escalation (seed behavior)

If the plan is **fundamentally unworkable** (not a minor gap — it cannot be built as specified),
return `status: stuck` with the reason. The orchestrator halts; the operator reviews. (Automatic
redesign-from-scratch + compare + judge is roadmap R1 — do NOT attempt it here.) Non-blocking gaps:
resolve with evidence and continue.

## Return

- `status`: pass | partial | stuck
- `summary`: key decisions resolved + gaps found
- `notes`: gaps the implement phase must account for
- `artifacts`: paths (grill report, draft ADR)
