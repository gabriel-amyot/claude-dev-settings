# Skill Proposal: debug-fix-ship
Date: 2026-05-20
Source: Cross-session feedback from KTP-646 bug fix pipeline experience
Status: PARKED (future build)

## Trigger
`/debug-fix-ship KTP-XXX --findings "IF-1, IF-2, IF-3"`

## Scope
Global. Brownfield bug fix pipeline (distinct from ticket-to-pr greenfield pipeline).

## 10-Phase Pipeline
1. **INVESTIGATE** — Parallel Dexter agents per finding
2. **PERSIST** — RCA + SBEs + Bibliotheque, parallel
3. **DESIGN** — Winston, writes design doc to disk
4. **CHALLENGE** — Codex-framed adversarial review (reads design doc)
5. **ADDRESS** — Update design with challenge findings
6. **IMPLEMENT** — Amelia, worktree off dev, tsc check
7. **REVIEW** — Quinn code review + Codex cascade
8. **SHIP** — /klever-mr (reuse, don't reimplement)
9. **VALIDATE** — Human gate: test on dev, report back
10. **LOOP or CLOSE** — New findings go to Phase 1, or done

## Existing Skills to Stitch
- `/investigate` — Phase 1
- `/adversarial-cascade` — Phase 4 and Phase 7
- `/klever-mr` — Phase 8
- `/challenge` — Phase 4 alternative

## Phase Gates
- Design must exist on disk before implement
- Challenge must pass before implement
- tsc must pass before review
- Post-deploy validation is mandatory with human confirmation

## Boundaries from Supervisr Pipelines
- Spec gate (Leo AC quality) before Phase 3
- Context gate (curator) before Phase 6
- Hook-enforced phase transitions (sprint-harness pattern)
- ralph-loop wrapper for overnight execution
- Jira comment at Phase 8 (plan) and Phase 9 (validation + MR link)

## Lessons Learned (from KTP-646 session)
- Q6 (once vs on/off) would have shipped broken without the challenge. Adversarial review is not theater.
- v1.1.20 deployed, IF-1 worked, IF-2 didn't. Without manual testing, stale closure bug would have shipped as "done."
- Codex framing trick removes deference bias. Reviewer challenged harder.
- Bibliotheque distillation should run in parallel, not wait for a clean break.
- The design doc is the contract between phases. Each phase consumed the same doc.
- Worktree creation is 100% automatable.
- Version bump + changelog is a gate, not an afterthought.

## What's Useful vs. Not
| Keep | Cut or automate |
|------|----------------|
| Winston design doc on disk | Brainstorming skill for bug fixes (overkill) |
| Codex-framed adversarial challenge | Asking "do you want me to..." (just do it) |
| Parallel investigation agents | Sequential investigation (4x slower) |
| Post-deploy human validation gate | Claiming "done" without dev testing |
| SBE persistence after each finding | Writing SBEs before investigation |
| Reading persona files | Full BMAD menu activation (skip the menu) |
