# Dark Factory v2 — Docs Index

**Status:** Shipped seed, hardened to 0.5.0 (built + run on first live trial). v2 is a skill beside v1
(`~/.claude/skills/dark-factory/`, being reframed as "Sprint Factory" — the multi-ticket orchestrator).
v2 owns the **single-ticket, human-gated** mode.

**Seed ticket:** KTP-728 · **Origin session:** wise-owl (2026-06-01) · **0.5.0 hardening:** deft-heron (2026-06-03)

| Doc | What it is | Read when |
|-----|-----------|-----------|
| [seed-spec-v1.md](seed-spec-v1.md) | The first version scope: one workflow spine + one backend/Java floor + KTP-728, like-for-like, human concierge front gate. In/out of scope, success criteria, build order. | Starting the build, or scoping any change. |
| [roadmap.md](roadmap.md) | Everything deferred past v1: targeted design rigor (R1), blind-impl (R2), multi-gate+model-diversity (R3), multi-floor (R4), floor-manager-as-tool-crib (R5), lights-out + infra (R6), reasoning-failure tracking → Supervisr.ai (R7). | Planning the next layer after the seed proves out. |
| [grounding-and-decisions.md](grounding-and-decisions.md) | Anti-hype record: claim tiers, accepted gaps, corrected token rationale, 3 pre-registered falsifiable predictions, governing principle (seed-ship-build, no monument). | Before trusting any claim about v2; when measuring the seed. |
| [adr/ADR-001-workflow-orchestration-over-prose.md](adr/ADR-001-workflow-orchestration-over-prose.md) | The crucial decision (Accepted): orchestrate via the Workflow tool, not prose. Primary rationale = no step can be skipped. Context, consequences, accepted gaps. | Understanding *why* v2 exists; revisiting if a prediction fails. |
| [hardening-spec-0.5.0.md](hardening-spec-0.5.0.md) | The 0.5.0 hardening spec (7 ranked changes) from the KTP-728/699 trial retros: live-verify, schema preflight, advertiser-id, backend-gated sub-ACs, structured findings, resume fix, bucketed path. | Understanding the 0.5.0 changes; planning the next hardening pass. |
| [adr/ADR-003-live-verify-data-claims.md](adr/ADR-003-live-verify-data-claims.md) | The decision behind 0.5.0 #1/#2: data-layer claims must be live-verified; stale local checkouts are not evidence. | Touching the concierge's blocker logic. |
| [harvest-from-sprint-crawl.md](harvest-from-sprint-crawl.md) | What sprint-crawl + sprint-harness do, and which mechanisms port to v2 (concierge context checklist, per-AC loop-back) vs. which are hook-substrate-bound. The 3-tool division (sprint-crawl / Sprint Factory / v2). | Considering per-AC resilience, or the sprint-crawl→v2 convergence. |
| [fullstack-fanout-spec-0.10.0.md](fullstack-fanout-spec-0.10.0.md) | Full-stack fan-out spec. Multi-belt detection BUILT (0.9.2); fan-out pipeline + dual-MR is the 0.10.0 work. Carries the **observed fan-out spike** result (run wf_3743e789-d3b): `parallel()` runs two agents fine, but `isolation:'worktree'` sandboxes the WORKFLOW's repo, not the target repos — so each fan-out agent must self-manage a worktree in its own target repo. Resolved mechanism + build plan + a latent single-repo-isolation finding to verify. | Building the full-stack fan-out; touching the implement worktree assumptions. |
| [visual-ac-feasibility-spec-0.9.0.md](visual-ac-feasibility-spec-0.9.0.md) | The 0.9.0 visual-AC gate (BUILT) from the 0.8.0 TDD-gate run feedback (KTP-728/758/759/788 all HALT_PRESHIP on un-verifiable rendered-UI ACs): concierge classifies visual/logic ACs + fixture availability up front; QA marks `visual_pending`; a visual-only gap routes to `NEEDS_VISUAL_VERIFY` (main loop renders against the local stack) → READY_TO_SHIP or the `READY_FOR_VISUAL_QA` fallback. Deferred follow-ups listed. | Touching the concierge/QA/readiness logic; planning the next hardening pass. |
| [system-integrity-gate-design.md](system-integrity-gate-design.md) | **(grill in progress, 2026-06-15)** The system-integrity / AC-regression gate from the KTP-677 over-deletion incident: a change must not break *previously-accepted* behavior, not just satisfy its own ACs. LOCKED: both START (pre-code, fail-fast) + END (post-build, fail-closed → `BLOCKED_SYSTEM_INTEGRITY`) gates, shared blast-radius scanner, three-layer shape (agent phase + JS verdict-check + main-loop git backstop). OPEN: START placement + scan mechanics (Q2–Q13). ADR-004 to follow. | Building the integrity gate; resuming the design grill. |
| [evolution-roadmap-2026-07-04.md](evolution-roadmap-2026-07-04.md) | **(PROPOSED, awaiting Gab)** Panel-synthesized evolution roadmap: Phase 1 python-crewai belt (+behavioral AC lane), Phase 2 integrity gate + KTP-677 fixture, Phase 3 headless/gate-as-handoff (gated on autopilot approval), Phase 4 cloud-validation room (NEEDS_CLOUD_VALIDATE). Parks fan-out, BQ floor, FeatureBench, R6. | Picking the next factory build; checking what was approved. |
| [month-learnings-2026-07-04.md](month-learnings-2026-07-04.md) | Stage-3 distillation of a month of operations (17 runs + transcripts): unmet work-kinds (python/CrewAI, BQ, full-stack, cloud e2e), recurring manual interventions, preventable incidents, eval + gcloud gaps, autopilot interface gap. Input to the 2026-07-04 Winston/PO/PM roadmap panel. | Planning any belt/floor/phase expansion; the self-evolve roadmap. |
| [spec-integrity-engine-northstar.md](spec-integrity-engine-northstar.md) | **(NORTH STAR vision, 2026-06-17)** The big sibling of the structural gate: keep a reliable up-to-date *system spec*, compare each ticket's AC against it upstream, discern collision vs additive, drive intentional spec change with human confirmation, update the spec on-branch first, regression-test against it. Prerequisite-gated (needs the spec corpus). Roadmap **R9**. The structural gate (Thread A) is the buildable subset + the room this grows into. | Designing the spec-integrity engine (its own session); understanding the factory North Star. |

## Build order (from seed-spec-v1.md)

1. KTP-728 + backend/Java floor (chosen).
2. Write `dark-factory.workflow.js` skeleton (phases as `agent({schema})`, gates as JS `if`).
3. Harvest phase-contract prompts from v1 `SKILL.md`.
4. Solve the concierge front-gate pause/resume (highest-risk unknown).
5. Run on KTP-728. Measure vs predictions #1 and #3. Write findings.
6. Benchmark v1 vs v2 on KTP-728 in two terminals (optional, post-build).
7. Decide: grow a floor / add rigor / stop.
