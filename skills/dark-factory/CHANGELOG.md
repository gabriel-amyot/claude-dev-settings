# Dark Factory — Changelog

Every SKILL.md modification bumps the version in frontmatter and adds an entry here.

Versioning: `MAJOR.MINOR.PATCH`
- **MAJOR**: New phases, mode changes, or breaking behavioral shifts
- **MINOR**: New enforcement rules, anti-patterns, sections, or structural changes
- **PATCH**: Wording fixes, table updates, reference corrections

---

## 1.7.0 (2026-06-03)

**Reframe begins: Dark Factory v1 → "Sprint Factory" (multi-ticket conductor).**

Now that dark-factory-v2 owns the single-ticket lifecycle, v1's role is being reframed to the multi-ticket
*conductor*: compute the dependency DAG, fan out one handoff per startable ticket (each runs through
`/dark-factory-v2`), unlock the next tier on report-back. Idempotent + rerunnable: reconciles from Jira
ticket status + the handoff ledger so a re-run skips in-flight handoffs and unlocks children of closed
tickets; persists a board to `tickets/sprints/{Sprint}/`.

- Frontmatter: description + nav reframed to multi-ticket conductor; `when` = multi-ticket/epic,
  `when_not` = single ticket (→ v2) / overnight per-AC (→ sprint-crawl). Version 1.6.0 → 1.7.0.
- Added a reframe banner at the top of SKILL.md; the 8-phase prose is now **legacy reference** until the
  orchestration rewrite lands.
- New design doc: `docs/sprint-factory-orchestration-model.md` — Mode 1 (handoff orchestration, build now),
  Mode 2 (autonomous concierge question-packs, future), idempotency/rerun via Jira+ledger reconcile, and
  the caveman question-pack format (per doubt: 2-3 assumptions → pick best → propose action).
- **Not yet done (scoped follow-up):** the hard rename (skill id `dark-factory` → `sprint-factory` + dir +
  reference sweep) and the actual orchestration-section rewrite to the handoff model. Kept `/dark-factory`
  working for now to avoid breaking references.

## 1.6.0 (2026-05-28)

**QA enforcement, pre-ship artifact gate, brownfield awareness, eval reasoning.**

- Eval schema: all dimension scores now require a `missing` list explaining what the gap points represent. Applies to both pre-run fitness prediction and post-run confidence assessment. Every prediction and every point should have a reasons list. (Gabriel's feedback from KTP-685)
- Phase 2: added brownfield gate. Before proposing new routes/pages/endpoints, search codebase for existing implementations. Ties into ticket-to-pr-analyst Step 4.5 `modification` vs `creation` classification.
- Phase 6: QA agent segregation. QA now dispatched to a separate agent (same pattern as Phase 5 review). QA agent receives AC list + file paths + tech adaptation table. Does NOT receive implementation plan or rationale.
- Phase 6: QA Technology Adaptation table. Per-stack QA requirements (browser verification for frontend, integration tests for backend, BQ assertions for SQL). Removed "if browser tools available" conditional. Missing verification = `PARTIAL`, never `PASS`.
- Phase 7: Pre-Ship Artifact Gate. Mandatory checks before any shipping action: qa-report exists, review artifacts exist, execution_verified populated, frontend screenshots present (if frontend ticket). Agent cannot self-certify past this gate.
- Guardrail #11: No phase collapsing. Each phase is a separate task. Merging phases removes enforcement points. (KTP-713 lesson)
- Skill Delegation Map: Phase 6 changed from inline to external QA agent dispatch.
- ticket-to-pr-analyst v1.1: Step 4.5 Existing Implementation Audit (brownfield awareness). Assumption schema gains `evidence_searched` and `classification` fields. (KTP-713 RCA Fix 6)
- Lessons 8-10 shelved: grill catches React hook timing bugs (KTP-684), adversarial false positive on ref tracking (KTP-684), AC referencing non-existent data fields (KTP-684).
- Lesson 11: QA self-certification (KTP-713). Adding more instructional text to a self-certified pipeline does not improve compliance. Fixed by Phase 6 agent segregation + Phase 7 pre-ship artifact gate.
- Lesson 12: Greenfield bias in spec (KTP-713). Analyst invents scope when ticket describes behavior without specifying UI placement. Fixed by ticket-to-pr-analyst Step 4.5 + Phase 2 brownfield gate.

## 1.5.0 (2026-05-27)

**Execution verification enforcement + external adversarial review + confidence eval bookends.**

- Phase 4 step 5: removed rationalization escape hatches. Execution attempt is now unconditional for Java/Maven and Node/NPM. Infra failures are logged as `infra_blocked({reason})`, not skipped. Only Terraform qualifies for `not_applicable`.
- Phase 6: hard enforcement via pipeline-state.yaml `execution_verified` field. Missing/false = INCOMPLETE cap. `infra_blocked` = PARTIAL cap. Advisory language replaced with structural gate table.
- Phase 5: review dispatched to a fresh Agent with no implementation context. Receives diff + ACs + repo CLAUDE.md only. "Try to break it" framing with mandatory test-your-findings. Produces `review/external-adversarial-report.vN.md`.
- Confidence Eval Bookends: pre-run fitness prediction (after Phase 1, logged to pipeline-state.yaml, non-blocking) + post-run assessment (after Phase 8, before retrospective). Same 5 dimensions scored before and after. Delta analysis detects over/under-confidence. Post-run proposes `/handoff` for low-scoring dimensions.
- Pipeline-state.yaml schema: added `execution_verified` per-ticket field (required), `eval.pre_run` and `eval.post_run` sections.
- Failure Handling: execution verification row updated from advisory to structural gate.
- Skill Delegation Map: Phase 5 changed from `/adversarial-cascade` Skill invocation to Agent tool dispatch.
- Lesson 8: Same agent cannot build and review. Advocacy bias missed null-country regression in 10 adapters (KTP-682).
- Lesson 9: "Mandatory" without structural enforcement is advisory. Agent rationalizes around escape hatches (KTP-682).

## 1.4.0 (2026-05-27)

**TDD integration into Phase 4 from KTP-682 null-country bug.**

- Phase 4 rewritten with TDD: baseline tests (hard gate on failure), RED-GREEN-REFACTOR per AC, adversarial edge-case tests as final sub-step
- Phase 2 extended with mandatory test specifications in impl-plan output (method signatures, expected assertions, baseline vs new-behavior classification)
- Added 3 Failure Handling rows: baseline test failure, tautological RED test, adversarial edge-case failure
- ADR-001: TDD as inline steps, not sub-phases (baseline interleaving constraint prevents separation)
- Lesson 7: Tests after code confirm, they don't specify (KTP-682)

## 1.3.0 (2026-05-26)

**Convergence escalation and advocacy bias guard.**

- Added Phase 5b: Convergence Escalation (cross-reference grill gaps with review findings, invalidate prior "accepted" labels, require resolution)
- Added preamble behavioral rule: "analysis over advocacy" with pointer to Phase 5b
- Added anti-pattern block for 4 advocacy behaviors
- Added Failure Handling row for convergence signals
- Added versioning system (this file) and `version` field in frontmatter
- Lesson 6: Accepted risk becomes inertia (KTP-681 post-merge review)

## 1.2.0 (2026-05-26)

**Testing depth enforcement from KTP-681 gap closure.**

- Added Phase 4 step 5: Mandatory execution verification checkpoint (stack-specific commands, success signals, timeouts, infra vs code error classification)
- Added Phase 4 step 6: Mandatory integration test requirements (MockMvc/Supertest/TestClient when validators/DTOs/controllers change)
- Added Phase 6 verification level enforcement (COMPILE_ONLY requires attempted execution, 3 valid exemptions only)
- Added anti-pattern block for 4 execution-skip rationalizations
- Added 2 Failure Handling rows (execution skipped, integration tests missing)
- Lesson 5: Unit tests alone insufficient (KTP-681)

## 1.1.0 (2026-05-25)

**Prerequisite integrity and verdict propagation from KTP-676 v2.**

- Added Phase 2 data prerequisite escalation ladder (search → download → HALT)
- Added anti-pattern block for 5 synthetic data workaround behaviors
- Added Verdict Propagation section (taint rules between Phase 2 and Phase 3)
- Added Failure Handling row for blocked_prerequisites
- Replaced /grill-me with /grill-with-docs across all 5 references
- Restructured lessons: monolith LESSONS.md → individual files in bibliothèque + catalog pointer
- Lesson 4 status: Open → Fixed

## 1.0.0 (2026-05-22)

**Initial release with execution verification from KTP-676 v1.**

- 8-phase pipeline: analyze, design, grill, implement, review, QA, ship, validate
- Single ticket, flat list, and plan-file modes
- Technology Adaptation table with Local Exec column
- Prerequisites gate in Phase 2
- /klever-mr auto-merge changed to opt-in
- Observability protocol with telemetry and run journals
- Lessons 1-3: Syntax checks, URL rot, spec assumptions
