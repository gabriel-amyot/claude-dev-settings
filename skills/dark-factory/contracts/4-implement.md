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

## TDD per AC (sequential) — RED FIRST, PROVEN

The orchestrator gates this per AC (`tddViolations`) and QA independently re-verifies your RED commit on
the branch — you **cannot self-certify past it**. For each AC, in order:

1. **Baseline** (only if the AC modifies existing behavior): write a test asserting *current* behavior;
   run it; it must PASS. **Hard stop:** if it fails, the AC's premise is wrong → `status: stuck` with
   the failing assertion. Do NOT rationalize.
2. **RED — stub, assert, fail on the ASSERTION:** write the new-behavior test. First stub the signature
   so the code COMPILES (return null/0/throw "not implemented") — so the failure is an **assertion
   failure**, never a compile/import/typo error. Run it; it MUST fail on the assertion. A compile-error
   "RED" is NOT valid (D2 — strict, all belts). Passes immediately ⇒ tautological ⇒ tighten. Capture the
   command + failing output.
3. **RED commit (TEST-ONLY):** commit the test by itself — **no production change in this commit**:
   `<TICKET>: AC-<N> RED — <behavior>`. This commit is your proof: QA runs `git show --stat <sha>` to
   confirm it touches the test file only, and re-runs the test at that commit to confirm it fails. One
   extra commit per AC; cheap, near-irrefutable.
4. **GREEN:** minimum code to pass; run all tests (suite stays green). No features beyond the test; no
   adjacent refactors. Commit: `<TICKET>: AC-<N> GREEN — <short what>`.
5. **REFACTOR** (optional): clean within scope, stay green.
6. **Write the per-AC ledger** `<ticket_folder>/tdd/AC-<N>.md` (template below) and the matching `ac_tdd`
   return entry. Compile/lint with the belt's command; run the belt's unit + (if specified) integration
   tests.
7. Max 3 fix attempts per AC; else mark it stuck. **If a stuck AC is a prerequisite for later ACs, mark
   those dependent ACs stuck too and skip them.**

### The ledger + the `ac_tdd` you return

Per AC, write `<ticket_folder>/tdd/AC-<N>.md` (RED command + failing output + RED sha; GREEN command +
passing output + GREEN sha) and return a matching `ac_tdd` entry:
```yaml
ac: AC-1
test_file: <path>
kind: new            # new | baseline_plus_new | bugfix
red:   { artifact: "<ticket_folder>/tdd/AC-1.md", commit: <red_sha>, failed: true, right_reason: true }
green: { commit: <green_sha>, passed: true, suite_green: true }
exempt: null
```
**Exemptions are structured and honest (the gate rejects free-text):**
- `not_applicable(<why>)` — the AC has **no unit surface**:
  - a pure-render UI change with no extractable logic (see the frontend belt) — proof is the belt's
    method (live visual validation, an endpoint response, a fixture run), not a unit RED; OR
  - a **pure refactor with no behavior change** (extract/rename/move): `not_applicable(pure refactor: no
    behavior change)` — there is no new behavior to RED; the proof is that the **baseline/existing tests
    stay green**. (Klever norm: a refactor shouldn't ride inside a feature ticket anyway.)
  **Do NOT fake a unit test to satisfy the gate** — that's the synthetic-data anti-pattern relocated. And
  if you wrote ANY extractable pure function (a selector, transform, validator), it is NOT exempt — RED it.
- `infra_blocked(<why>)` — ONLY if the test cannot even be **authored/run** without the infra.
  `infra_blocked` on *execution-verify* does **not** excuse a unit RED you could have written locally (D3).

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
- `ac_tdd`: array, one entry per AC you touched (RED proof + GREEN + `exempt`) — see the ledger section.
  Every AC marked `done` in `ac_progress` must have an entry, or the gate halts.
- `branch`, `pushed` (bool), `diff_artifact` (absolute path), `summary`
