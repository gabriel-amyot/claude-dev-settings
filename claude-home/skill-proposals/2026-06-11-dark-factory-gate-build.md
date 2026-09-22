# Skill Proposal: dark-factory-gate-build
Date: 2026-06-11
Source: deft-falcon session (4 dark-factory hardening passes followed the identical flow)

## Trigger
"Add/harden a gate in dark-factory", "the factory keeps hitting X at QA", "extend dark-factory with a new
phase/gate", or any change to `~/.claude-shared-config/skills/dark-factory/` driven by run-telemetry feedback.

## Scope
global (the skill lives in shared-config; the procedure is reusable for every dark-factory extension).

## Draft Steps
1. **Audit the gap from real run telemetry** — read `runs/*.yaml` (Retro output), find the recurring
   red_flag / HALT pattern; ground the change in observed runs, not speculation.
2. **Design doc + locked decisions** — write `docs/<feature>-spec-<ver>.md`; surface the 2–4 genuine forks
   to the human via AskUserQuestion; record the locked decisions in the doc.
3. **Implement** — extend the spine schema + a pure gate function (sibling to preShipBlockers / tddViolations
   / classifyQaGap) + the affected contracts + belts. Keep default runs byte-identical (arg-gate new modes).
4. **Mutation-checked test** — `tests/<gate>.test.mjs`: extract the gate's pure fns VERBATIM from source via
   regex + `new AsyncFunction`; adversarial matrix (assert both fires and doesn't); mutation-probe one
   condition to prove load-bearing.
5. **Adversarial subagent pass** — a hostile reviewer tries to bypass/false-block the gate; fold the cheap
   high-value fixes; document residuals honestly.
6. **Ship** — async-wrapped syntax check; version bump + CHANGELOG entry (why+what) + update SKILL.md Status;
   commit the FEATURE and the run telemetry as SEPARATE commits.

## Notes
Honest-limitation rule: every dark-factory gate rests on the segregated-agent + captured-artifact trust
model (the spine is a JS sandbox, can't run git/skills). State that ceiling rather than overclaiming
"un-skippable." Where a deterministic check IS possible, it lives in the MAIN LOOP (e.g. the TDD RED git
audit), never the subagent.
