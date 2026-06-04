# Contract 4 — Implement

Write code, one AC at a time, test-first. Then run the deliverable, prove it produces the expected
output, **push the branch**, and **write the diff** so downstream agents can see it.

Adapted from the old skill's Phase 4 (IMPLEMENT). Stack specifics come from your **tool belt**, not
this contract.

## Equip your tool belt first

The path to your tool belt is in your prompt (`toolcrib/<belt>.md`). **Read it now.** It defines, for
this run's work-type: the compile/lint command, the unit-test command, integration-test rules (if
any), the **execute-verify** command + success signal, and the **proof shape** (what "expected output"
means). Use ITS commands. Do NOT assume Java/Maven (or any stack) — the belt is the source of truth.

## Worktree

The Workflow runtime gave you your own isolated git worktree. **Do NOT run `git worktree add`** — work
in your current directory. Create the feature branch: `git checkout -b <TICKET>-short-desc origin/dev`
(fetch origin first if needed).

## TDD per AC (sequential)

For each AC, in order:

1. **Baseline** (only if the AC modifies existing behavior): write a test asserting *current* behavior;
   run it; it must PASS. **Hard stop:** if it fails, the AC's premise is wrong → `status: stuck` with
   the failing assertion. Do NOT rationalize.
2. **RED:** write the failing test for the new behavior; run it; it must FAIL. Passes immediately ⇒
   tautological ⇒ tighten.
3. **GREEN:** minimum code to pass; run all tests. No features beyond the test; no adjacent refactors.
4. **REFACTOR** (optional): clean within scope, stay green.
5. **WIP commit:** `<TICKET>: AC-<N> — <short what>`. Compile/lint with the belt's command; run the
   belt's unit + (if specified) integration tests.
6. Max 3 fix attempts per AC; else mark it stuck. **If a stuck AC is a prerequisite for later ACs, mark
   those dependent ACs stuck too and skip them.**

## Adversarial edge-case tests (after all ACs green)

For each AC, write one test attacking an edge case it doesn't mention (null/old-signature callers,
empty, boundaries). Run each. A failure is a real bug — fix + commit with the test. (KTP-682 pattern.)

## Execution verification (UNCONDITIONAL — never skip)

Run your tool belt's **execute-verify** step exactly, with its timeout and success signal. Record:
- success per the belt's criteria → `execution_verified: "true"`
- a code error you can fix → fix and re-run
- an infrastructure blocker the belt calls out (missing DB/key/real input data) →
  `execution_verified: "infra_blocked(<specific reason>)"`
- a stack with no local exec the belt marks not-applicable → `execution_verified: "not_applicable(<reason>)"`

Do NOT skip the attempt and do NOT fabricate inputs/data to force a pass (synthetic-data anti-pattern).
Only write `"true"` if the belt's success criteria were actually met — the orchestrator caps QA on it.

## Publish your work (so Review/QA can see it)

1. **Push the feature branch:** `git push -u origin <branch>` (feature branch only — never dev/main).
   Set `pushed: true`; on failure `pushed: false` + `status: partial`.
2. **Write the diff:** `git diff origin/dev..HEAD > <ticket_folder>/review/diff.patch`. Return that
   path as `diff_artifact`.

## Return

- `status`: pass | partial | stuck
- `execution_verified`: `"true"` | `"infra_blocked(<reason>)"` | `"not_applicable(<reason>)"` | `"false"`
- `ac_progress`: object, e.g. `{ "AC-1": "done", "AC-2": "stuck" }`
- `branch`, `pushed` (bool), `diff_artifact` (absolute path), `summary`
