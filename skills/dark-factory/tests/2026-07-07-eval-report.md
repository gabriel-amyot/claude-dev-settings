# tdd-gate.test.mjs — eval report (2026-07-07)

Target: `tddViolations` / `tddVerifiedCap` extracted verbatim from `../dark-factory.workflow.js`
(the Dark Factory TDD gate — layer 1 structural RED-proof check, layer 2 QA-branch re-verification
cap).

## Results

`tdd-gate.test.mjs` — **24/24 passing** (16 pre-existing + 8 new). `visual-readiness.test.mjs`
unaffected — **18/18 passing**, unchanged.

Run:
```
node ~/.claude-shared-config/skills/dark-factory/tests/tdd-gate.test.mjs
node ~/.claude-shared-config/skills/dark-factory/tests/visual-readiness.test.mjs
```
(plain `node`, no `node --test` runner needed — both files are self-contained scripts with their
own pass/fail counters and `process.exit`.)

## New cases (T17–T24)

- T17 — mixed valid + invalid ACs: only the invalid one is flagged (violations.length === 1, not a
  blanket failure).
- T18/T19 — malformed-`exempt` regex boundary: empty parens (`not_applicable()`) and trailing text
  after the close-paren (`infra_blocked(no DB) extra`) both correctly violate — the regex is
  anchored `^...$` with a non-empty `.+` capture group, so both edges hold.
- T20 — `red.artifact: ''` (empty string, present-but-falsy) is treated identically to a missing
  artifact — RED violation. Confirms the check is a JS-truthiness check (`!red.artifact`), not an
  "is the key present" check.
- T21 — `tddVerifiedCap` never upgrades or otherwise touches a `FAIL` overall, even with fully
  unverified RED — only `ALL_PASS` is subject to the cap. Boundary the original 16 tests didn't
  exercise directly.
- T22 — cap boundary: one unverified PASS AC mixed among several verified PASS ACs still caps the
  whole run to `PARTIAL` (any single violation is enough; the check is `.some(...)`, not a
  threshold count).
- T23 — `red_verified: 1` (truthy but not strictly `true` or `"exempt"`) still caps — confirms
  the comparison is strict (`!== true && !== 'exempt'`), not loose truthiness.
- T24 — malformed input: `qa.per_ac` entirely absent (`{}`) does not throw and does not cap
  (`(qa.per_ac || [])` defaults to empty array — no violation possible with no data).

## Notes

- No reimplementation risk: the harness extracts the real function source via regex from the
  workflow file (see file header), same technique as the pre-existing 16 tests — new cases test
  the same extracted functions, not a copy.
- No bugs found in `tddViolations`/`tddVerifiedCap`. All boundary and malformed-input behavior
  matched what the inline code comments describe.
