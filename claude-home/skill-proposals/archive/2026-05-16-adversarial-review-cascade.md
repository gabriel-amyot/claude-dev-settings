# Skill Proposal: adversarial-review-cascade
Date: 2026-05-16
Source: KTP-669 implementation session

## Trigger
After a pre-planned implementation compiles and tests pass. Invoke with: "run adversarial cascade", "quality gate", "review before MR", or automatically as Phase B/C in any plan that includes an adversarial review step.

## Scope
Global (works on any repo with compilable code and tests)

## Draft Steps
1. **Quinn adversarial review** — Load Quinn persona, review all changed files for logic errors, missed edge cases, contract violations, validation gaps, untested paths. Report findings by severity.
2. **Fix CRITICAL/HIGH** — Apply fixes from Quinn's findings. Recompile + retest.
3. **Loop** — If round produced findings, run Quinn again (max 3 rounds). Exit early if zero findings.
4. **Final code review (Codex framing)** — Review as AI-generated code (security, unnecessary complexity, spec over-reach, caching correctness, broken patterns). Fix CRITICAL findings.
5. **Final verify** — Recompile + retest. Report clean bill of health or remaining LOW/MEDIUM items as accepted risk.

## Notes
- Quinn and Codex-framed reviews catch different classes of bugs (Quinn: logic/edge cases, Codex: security/over-engineering)
- The "distinct from plan spec" framing for the final review prevents confirmation bias
- This is already described in the plan template but could be standardized as a standalone skill invokable after any implementation phase
