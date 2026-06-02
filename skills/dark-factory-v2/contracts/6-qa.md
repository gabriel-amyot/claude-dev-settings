# Contract 6 — QA (evidence, segregated)

Prove each acceptance criterion is met with **concrete evidence**. Not test execution (Phase 4 did
that) — proof that each AC is satisfied. You run separately from the implementor so the builder
cannot self-certify.

Adapted from the old skill's Phase 6 (QA). Backend/Java floor.

## Inputs (get them yourself)

- The Workflow runtime gave you your own worktree. Fetch + check out the pushed branch (name in your
  prompt): `git fetch origin <branch> && git checkout <branch>`.
- AC list: read `<ticket_folder>/analyst/` (path in your prompt).
- Changed files: `git diff --name-only origin/dev..HEAD`.

You do NOT get the implementation plan or the implementor's rationale. Judge by what the code does.

## Per-AC evidence

For each AC, collect:
- `code_ref`: file path + line range that satisfies it.
- `test_ref`: the test name + its pass output proving the behavior.
- A verdict: PASS | PARTIAL | FAIL.

**Code review alone is NEVER a PASS.** A `PASS` with no `test_ref` is a contradiction — the
orchestrator will cap it to PARTIAL. So only mark PASS when you have both a `code_ref` and a passing
`test_ref`.

## Backend/Java tech-adaptation

Verification requires running integration tests OR curling the affected endpoints with expected
response shapes. If you cannot run integration tests or hit the endpoints, the verdict is
`PARTIAL (no endpoint verification)` — never `PASS`.

## Return

- `raw_overall`: ALL_PASS | PARTIAL | FAIL  (your raw read of the evidence)
- `per_ac`: array of `{ ac, verdict, code_ref, test_ref }`
- `summary`: 1-3 sentences

**Example per_ac row:**
`{ "ac": "AC-1", "verdict": "PASS", "code_ref": "src/main/java/.../ProximityValidator.java:42-55", "test_ref": "ProximityValidatorTest#shouldRejectNullCountry — PASS" }`

Return RAW verdicts only. The orchestrator clamps the overall level based on evidence and on
`execution_verified` from Phase 4 — that cap is not yours to set.
