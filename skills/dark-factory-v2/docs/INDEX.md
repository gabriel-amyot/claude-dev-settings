# Dark Factory v2 — Docs Index

**Status:** Spec stage. No `SKILL.md` and no workflow code yet (written when the seed build starts).
v2 is a **new skill** built beside v1 (`~/.claude/skills/dark-factory/`), which stays intact as the
working fallback and the **benchmark baseline** (v1 vs v2, same ticket, two terminals).

**Seed ticket:** KTP-728 · **Origin session:** wise-owl (2026-06-01)

| Doc | What it is | Read when |
|-----|-----------|-----------|
| [seed-spec-v1.md](seed-spec-v1.md) | The first version scope: one workflow spine + one backend/Java floor + KTP-728, like-for-like, human concierge front gate. In/out of scope, success criteria, build order. | Starting the build, or scoping any change. |
| [roadmap.md](roadmap.md) | Everything deferred past v1: targeted design rigor (R1), blind-impl (R2), multi-gate+model-diversity (R3), multi-floor (R4), floor-manager-as-tool-crib (R5), lights-out + infra (R6), reasoning-failure tracking → Supervisr.ai (R7). | Planning the next layer after the seed proves out. |
| [grounding-and-decisions.md](grounding-and-decisions.md) | Anti-hype record: claim tiers, accepted gaps, corrected token rationale, 3 pre-registered falsifiable predictions, governing principle (seed-ship-build, no monument). | Before trusting any claim about v2; when measuring the seed. |
| [adr/ADR-001-workflow-orchestration-over-prose.md](adr/ADR-001-workflow-orchestration-over-prose.md) | The crucial decision (Accepted): orchestrate via the Workflow tool, not prose. Primary rationale = no step can be skipped. Context, consequences, accepted gaps. | Understanding *why* v2 exists; revisiting if a prediction fails. |

## Build order (from seed-spec-v1.md)

1. KTP-728 + backend/Java floor (chosen).
2. Write `dark-factory-v2.workflow.js` skeleton (phases as `agent({schema})`, gates as JS `if`).
3. Harvest phase-contract prompts from v1 `SKILL.md`.
4. Solve the concierge front-gate pause/resume (highest-risk unknown).
5. Run on KTP-728. Measure vs predictions #1 and #3. Write findings.
6. Benchmark v1 vs v2 on KTP-728 in two terminals (optional, post-build).
7. Decide: grow a floor / add rigor / stop.
