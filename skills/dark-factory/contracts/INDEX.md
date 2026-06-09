# Dark Factory v2 — Phase Contracts (the "muscle")

Each phase agent in `dark-factory.workflow.js` reads its contract here and executes it.
Contracts are the reasoning instructions, **harvested from v1's proven phases** — NOT written from
any specific ticket. The workflow spine (gates, order, human-gate split) lives in the `.js`. Stack
tooling lives in `toolcrib/` belts, never in these shared contracts.

**Status: WRITTEN** (copied + adapted from v1, blind to any specific ticket).
Source = `~/.claude/skills/dark-factory/SKILL.md` (v1), proven across KTP-681/682.

| # | Contract file | Harvest from v1 SKILL.md | Returns (schema) |
|---|---------------|--------------------------|------------------|
| 1 | `1-concierge.md` | Phase 1 ANALYZE + Phase 2 prerequisites/escalation ladder, merged into one front gate | spec_quality, needs_human, ac_count, prereqs_ok, open_questions |
| 2 | `2-design.md` | Phase 2 DESIGN (impl plan + mandatory test specs, brownfield gate) | status, summary, artifacts |
| 3 | `3-grill.md` | Phase 3 GRILL (interrogate plan; use git not local files — KTP-680 lesson) | status, summary, notes |
| 4 | `4-implement.md` | Phase 4 IMPLEMENT (TDD RED-GREEN-REFACTOR per AC with a PROVEN RED — test-only commit, fail-on-assertion, per-AC ledger — adversarial edge tests, execution verification, integration tests) | status, execution_verified, ac_progress, ac_tdd, branch |
| 5 | `5-review.md` | Phase 5 REVIEW (fresh adversarial agent, "try to break it", test-your-findings) + 5b convergence | criticals_open, findings[] |
| 6 | `6-qa.md` | Phase 6 QA (segregated agent, per-AC evidence, tech-adaptation table) | raw_overall, per_ac[] |
| 7 | `7-ship.md` | Phase 7 SHIP (/klever-mr, /post-comment, transition ceiling) | status, summary |
| 8 | `8-validate.md` | Phase 8 VALIDATE (post-merge dev smoke / frontend human gate) | status, summary |

## Harvest rules
- Carry over the **anti-patterns** verbatim (synthetic-data, rationalize-skip, advocacy-bias) —
  they are the hard-won part.
- Keep the **TDD discipline** in contract 4; stack tooling (build/test/execute) lives in `toolcrib/`
  belts, not the contract.
- Shared contracts stay **stack-agnostic**; work-type tooling lives in `toolcrib/` belts (`java`,
  `scripting`, `frontend` racked). A belt swaps tools only (ADR-002).
- The JS gates in the spine ALREADY enforce: spec-quality halt, zero-open-CRITICAL, QA verdict cap
  from execution_verified, pre-ship blockers, the **TDD RED gate** (`tddViolations` on `ac_tdd` +
  `tddVerifiedCap` on QA's `red_verified`), and the **visual-AC gate** (`classifyQaGap` routes a
  visual-only QA gap to `NEEDS_VISUAL_VERIFY` instead of HALT; concierge `acs` carries the visual/logic +
  fixture classification; QA's `visual_pending` marks proven-logic rendered-UI ACs). Contracts describe
  the *work*; the spine enforces the *gates*. Do not duplicate gate logic as prose in the contracts.
