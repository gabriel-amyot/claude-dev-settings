# Contract 4 — Implement

Write code, one AC at a time, test-first. Then **attempt to run the artifact**, **push the branch**,
and **write the diff** so the downstream agents can see your work. Backend/Java floor.

Adapted from the old skill's Phase 4 (IMPLEMENT). Most enforcement-heavy contract.

## Worktree

The Workflow runtime has ALREADY given you your own isolated git worktree. **Do NOT run
`git worktree add`** — work in your current directory. Create the feature branch here:
`git checkout -b <TICKET>-short-desc origin/dev` (fetch origin first if needed).

## TDD per AC (sequential)

For each AC, in order:

1. **Baseline** (only if the AC modifies existing behavior): write a test asserting *current*
   behavior. Run it. It must PASS. **Hard stop:** if it fails, the AC's premise is wrong — return
   `status: stuck` and report the failing assertion. Do NOT rationalize.
2. **RED:** write the failing test for the new behavior. Run it. It must FAIL. If it passes
   immediately, it is tautological — tighten the assertions.
3. **GREEN:** minimum code to pass. Run all tests. No features beyond the test; no adjacent refactors.
4. **REFACTOR** (optional): clean within the AC's scope, keep tests green.
5. **WIP commit:** `<TICKET>: AC-<N> — <short what>`. Compile/type-check (`mvn compile -pl <module>`),
   run relevant unit + integration tests.
6. Max 3 fix attempts per AC. If still failing, mark that AC stuck. **If a stuck AC is a prerequisite
   for later ACs, mark those dependent ACs stuck too and skip them** (don't build on a broken base).

## Adversarial edge-case tests (after all ACs green)

For each AC, write one test attacking an edge case it does not mention (null/old-signature callers,
empty, boundaries). Run each. A failure is a real bug — fix it and commit with the test
(`<TICKET>: edge-case guard — <what broke>`). (KTP-682 pattern.)

## Integration tests (mandatory when validators/DTOs/controllers change)

Java/Maven: MockMvc `@WebMvcTest` — (a) happy path: valid new input → 200 + shape; (b) rejection:
invalid input → 400. Change a validator ⇒ update the controller integration test.

## Execution verification (UNCONDITIONAL — never skip)

`mvn spring-boot:run -pl <module> -Dspring-boot.run.profiles=local` (timeout ~120s). Success signal:
`Started <App>Application in N seconds`.
- Startup succeeds → `execution_verified: "true"`, then kill it.
- Code errors (missing import, duplicate bean, circular dep) → fix and re-run.
- Infra errors (no DB/API key/BQ) → `execution_verified: "infra_blocked(<specific error>)"`.
Do NOT skip the attempt. "All unit tests pass" / "validators only" / "no creds locally" are NOT valid
skips. Only write `"true"` if startup actually succeeded — the orchestrator caps the QA verdict on it.

## Publish your work (so Review/QA can see it)

After all ACs are done and execution is attempted:
1. **Push the feature branch:** `git push -u origin <branch>` (a feature branch — never dev/main).
   Set `pushed: true`. If the push fails, set `pushed: false` and `status: partial`.
2. **Write the diff:** `git diff origin/dev..HEAD > <ticket_folder>/review/diff.patch`. Return that
   path as `diff_artifact`. (Backup channel: Review/QA primarily fetch+checkout the branch.)

## Return

- `status`: pass | partial | stuck
- `execution_verified`: `"true"` | `"infra_blocked(<reason>)"` | `"not_applicable(<reason>)"` | `"false"`
- `ac_progress`: object, e.g. `{ "AC-1": "done", "AC-2": "stuck" }`
- `branch`: the pushed branch name
- `pushed`: boolean (did `git push` succeed?)
- `diff_artifact`: absolute path to the written diff
- `summary`: what was implemented
