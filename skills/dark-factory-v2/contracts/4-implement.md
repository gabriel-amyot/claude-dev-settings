# Contract 4 — Implement

Write code, one AC at a time, test-first, in an isolated worktree. Then **attempt to run the
artifact**. Backend/Java floor.

Adapted from the old skill's Phase 4 (IMPLEMENT). This is the most enforcement-heavy contract.

## Worktree

Work in a git worktree off `origin/dev`:
`git worktree add /tmp/<TICKET> -b <TICKET>-short-desc origin/dev`.
If it already exists and is clean, reuse it; if dirty, stop and report rather than clobbering.

## TDD per AC (sequential)

For each AC, in order:

1. **Baseline** (only if the AC modifies existing behavior): write a test asserting the *current*
   behavior. Run it. It must PASS. **Hard stop:** if the baseline fails, the AC's premise is wrong —
   the behavior it assumes does not exist. Return `status: stuck` and report the failing assertion.
   Do NOT rationalize ("test setup is wrong"). The test tells you what the code actually does.
2. **RED:** write the failing test for the new behavior. Run it. It must FAIL. If it passes
   immediately, it is tautological — tighten the assertions to target the real change.
3. **GREEN:** minimum code to make the test pass. Run all tests. Do NOT add features beyond the
   test, do NOT refactor adjacent code.
4. **REFACTOR** (optional): clean up within the AC's scope, keep tests green.
5. **WIP commit:** `<TICKET>: AC-<N> — <short what>`. Then compile/type-check
   (`mvn compile -pl <module>`) and run the relevant unit + integration tests.
6. Max 3 fix attempts per AC. If still failing, mark that AC stuck and continue with the rest.

## Adversarial edge-case tests (after all ACs are green)

For each AC, write one test that tries to break it via an edge case the AC does not mention: null
inputs from callers that may not pass new params, empty strings, old call signatures, boundaries.
Run each. A failure is a real bug — fix the code and commit the fix with the test
(`<TICKET>: edge-case guard — <what broke>`). This is the KTP-682 pattern.

## Integration tests (mandatory when validators/DTOs/controllers change)

Java/Maven: MockMvc `@WebMvcTest` with (a) happy path: valid new input → 200 + expected shape, and
(b) rejection path: invalid input → 400. If you change a validator, the controller integration test
MUST be updated.

## Execution verification (UNCONDITIONAL — never skip)

After all ACs are green, attempt to run the app:
`mvn spring-boot:run -pl <module> -Dspring-boot.run.profiles=local` (timeout ~120s).
Success signal: `Started <App>Application in N seconds`.

- Startup succeeds → set `execution_verified: "true"`, then kill the process.
- **Code errors** (missing import, duplicate bean, circular dependency): fix them, re-run until
  startup succeeds.
- **Infra errors** (no DB connection, missing API key, no BQ credentials): the attempt happened and
  proved the failure is not a code bug → set `execution_verified: "infra_blocked(<specific error>)"`.

**Do NOT skip the attempt.** These are not valid reasons to skip: "all unit tests pass", "validators
only", "BQ creds aren't local", "would take too long". Unit tests do not catch Spring wiring issues.
Be honest: only write `"true"` if startup actually succeeded — the orchestrator caps the QA verdict
based on this value.

## Return

- `status`: pass | partial | stuck
- `execution_verified`: `"true"` | `"infra_blocked(<reason>)"` | `"not_applicable(<reason>)"` | `"false"`
- `ac_progress`: object, e.g. `{ "AC-1": "done", "AC-2": "stuck" }`
- `branch`: the branch name you pushed work onto
- `summary`: what was implemented
