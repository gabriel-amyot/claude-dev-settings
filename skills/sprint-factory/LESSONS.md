# Dark Factory — Lessons Learned

Quick reference. Full lesson details live in the bibliothèque:
`documentation/bibliotheque/development/dark-factory/lessons/`

## Catalog

| # | Title | Source | Status | Key Rule |
|---|-------|--------|--------|----------|
| 1 | Syntax checks ≠ execution | KTP-676 | Fixed | Two-tier verify: compile + execute |
| 2 | External URLs rot silently | KTP-676 v2 | Fixed | Execute download scripts before merge |
| 3 | Spec assumptions can be wrong | KTP-676 v2 | Fixed | First execution validates the spec |
| 4 | Agents rationalize around blocks | KTP-676 v2 | Fixed | Anti-pattern examples + verdict taint |
| 5 | Unit tests alone insufficient | KTP-681 | Fixed | Startup check + integration tests mandatory |
| 6 | Accepted risk becomes inertia | KTP-681 | Fixed | Convergence escalation + analysis over advocacy |
| 7 | Tests after code confirm, they don't specify | KTP-682 | Fixed | RED-GREEN-REFACTOR per AC in Phase 4 |
| 8 | Grill phase catches React hook timing bugs | KTP-684 | Open | Probe store state between async trigger and resolution |
| 9 | Adversarial false positive on ref tracking | KTP-684 | Open | Trace ref write/read/reset sites before filing CRITICAL |
| 10 | AC referencing non-existent data fields | KTP-684 | Open | Leo AC readiness check must include data availability dimension |
| 11 | QA self-certification bypasses mandatory checks | KTP-713 | Fixed | Phase 6 agent segregation + Phase 7 pre-ship artifact gate |
| 12 | Greenfield bias in spec invents scope | KTP-713 | Fixed | ticket-to-pr-analyst Step 4.5 brownfield audit + Phase 2 brownfield gate |

## How This File Grows

After each pipeline run, Phase 8 (RETROSPECTIVE) does:
1. Reads all `runs/*.yaml` telemetry files
2. Detects snag patterns recurring across 2+ runs
3. Writes a new lesson file to `documentation/bibliotheque/development/dark-factory/lessons/{NNN}-{slug}.md`
4. Adds a row to the catalog table above
5. Updates the bibliothèque INDEX.md

Lessons start as `Open` → move to `Fixed` when they produce a SKILL.md change, or `Accepted` when understood but not worth fixing.

## Themes

- **Verification depth** (L1, L2, L3, L5): Syntax < compile < unit test < integration test < execution < real data.
- **Agent rationalization** (L4, L5): Agents optimize for throughput over integrity. Negative examples and mechanical constraints required.
- **Test ordering** (L7): Tests written after code are biased by implementation knowledge. RED-GREEN catches bugs that test-after misses.
- **React async state** (L8): React hooks watching Zustand store slices fire in intermediate states during async cascades. Grill must probe store state between async trigger and resolution.
- **Adversarial false positives** (L9): Adversarial reviewers working from diffs produce false positives on cross-effect ref tracking. Ref lifecycle tables required before filing CRITICAL.
- **Spec-to-data-model gaps** (L10): ACs written against domain models reference fields absent from the frontend data model. Leo's gate must include a data availability dimension.
- **Self-certification** (L11, L12): Prose instructions the agent reads and self-certifies. Adding more text increases surface area for selective compliance. Structural fixes (artifact gates, agent segregation, brownfield search) required.
