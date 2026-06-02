# Contract 3 — Grill

Interrogate the implementation plan **before any code is written**. Surface gaps, unverified
assumptions, and missing edge cases. Cheaper to find a bad decision here than in Review or QA.

Adapted from the old skill's Phase 3 (GRILL). Pragmatic-architect (Winston) posture.

## Inputs

- `design/impl-plan.md` from Phase 2, plus the AC list and assumptions from `analyst/`.

## Steps

1. Challenge the plan against the **existing domain model and docs** (CONTEXT.md, ADRs, contracts).
2. For each material assumption in the plan, **verify it against the actual code**:
   - If the code already handles a case, say so with a file reference.
   - If a choice is arbitrary (two equivalent approaches), pick one and move on.
   - If there is a real gap (no code handles this, no spec covers it), flag it unresolved.
3. **Use git, not local files, for existence checks.** Run `git show origin/dev:<path>` to confirm a
   file/table/symbol exists on the branch you will build against. Local working state can differ from
   `origin/dev`. (KTP-680 lesson: a local `find` missed a table that existed on `origin/dev`.)
4. Capture any non-obvious resolved decision (why approach A over B, why this data flow) as a draft
   ADR in the ticket folder, following the repo's ADR format. NOT committed automatically.

## Unworkable-design escalation (seed behavior)

If the grill concludes the design is **fundamentally unworkable** (not a minor gap — the plan cannot
be built as specified), return `status: stuck` with a clear reason. In the seed, the operator
reviews stuck runs. (The automatic "redesign-from-scratch + compare + judge" recovery is a future
addition, roadmap R1 — do NOT attempt it here.)

For normal gaps that are not blocking, resolve them with evidence and continue.

## Return

- `status`: pass | partial | stuck
- `summary`: key decisions resolved and any gaps found
- `notes`: gaps the implement phase must account for
- `artifacts`: paths (grill report, draft ADR)
