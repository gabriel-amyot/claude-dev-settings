# Contract 6 — QA (evidence, segregated)

Prove each acceptance criterion is met with **concrete evidence**. This is not test execution
(Phase 4 did that) — it is proving each AC is satisfied. You run in a separate context from the
implementor so the builder cannot self-certify its own work.

Adapted from the old skill's Phase 6 (QA). Backend/Java floor.

## What you receive

- The AC list.
- The changed file paths.
- This contract (the backend tech-adaptation guidance below).

You do NOT receive the implementation plan or the implementor's rationale. Judge by what the code
does.

## Per-AC evidence

For each AC, collect:
- `code_ref`: file path + line range of the code that satisfies it.
- `test_ref`: the test name + its pass output that proves the behavior.
- A verdict: PASS | PARTIAL | FAIL, with evidence.

**Code review alone is NEVER a PASS.** Code review is evidence of understanding, not of function.

## Backend/Java tech-adaptation

Verification requires running integration tests OR curling the affected endpoints with expected
response shapes. If you cannot run integration tests or hit the endpoints, the verdict is
`PARTIAL (no endpoint verification)` — never `PASS`.

## Return

- `raw_overall`: ALL_PASS | PARTIAL | FAIL  (your raw assessment from the evidence)
- `per_ac`: list of `{ ac, verdict, code_ref, test_ref }`
- `summary`: 1-3 sentences

**Return raw verdicts only.** Do NOT set the verification level yourself. The orchestrator clamps
the overall result based on `execution_verified` from Phase 4 (if execution was not verified, your
ALL_PASS is capped to INCOMPLETE or PARTIAL in code). That cap is not yours to override.
