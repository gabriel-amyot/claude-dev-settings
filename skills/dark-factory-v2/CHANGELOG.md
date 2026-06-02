# Dark Factory v2 — Changelog

Every SKILL.md / workflow.js / contract change bumps the version and adds an entry.

## 0.4.1 (2026-06-02)

**Stack-agnostic hardening — no Java or ticket specifics in the factory itself.**

- Removed all Java/Spring/Maven specifics from the spine (concierge prompt) and the shared contracts
  (1 concierge, 2 design, 6 QA, 7 ship, 8 validate, 9 retro). They now defer to the run's tool belt.
  Java build/test/execute tooling lives only in `toolcrib/java.md` (multi-module Maven note moved there).
- Concierge now **discovers** belts by reading the new `toolcrib/INDEX.md` + each belt's `detect` rule,
  instead of the spine naming/​describing belts.
- Removed every KTP-728 mention from the operational files (spine, contracts, toolcrib, SKILL, CHANGELOG).
  Only `docs/` (the design archive that documents the build-blind rule) retains historical references.
- Belt ids (`java`, `scripting`) remain named in the registry/catalog — that's the rack's contents, not
  stack logic in a shared room.

## 0.4.0 (2026-06-02)

**Multi-work-type via tool belts (ADR-002). Scripting floor added so the factory can run side-effect
script tickets, not just Java services.**

Triggered by the first live trial (a scripting ticket): it halted honestly at the concierge
because validation was hardwired to `mvn spring-boot:run`. That halt = the anti-fake design working.

- ADR-002: one **blueprint** (the spine) + swappable **tool belts** from a **tool crib**, NOT
  duplicated floors. Corrected vocabulary against the Minions source (blueprint = the state machine;
  tool crib = curated tools per task). Concierge stays; dispatcher + spec/architect-persona loop
  parked to the refining phase (`docs/second-floor-refining-notes.md`).
- `toolcrib/java.md` + `toolcrib/scripting.md`: per-work-type build/tester loadouts.
- Concierge (contract 1 + schema) classifies the work-type and returns `tool_belt`; workflow halts
  `BLOCKED_UNSUPPORTED_FLOOR` when no belt is racked (then rack one + confirm with human).
- Implement (contract 4) + QA (contract 6) rewritten belt-aware: they read the run's tool belt for
  compile/execute-verify/proof instead of assuming Java/Maven. Generalized proof of work =
  "run the deliverable on declared inputs, assert the declared expected output."
- Ship-prep (contract 7) honors the belt's `has_version_file` (skips version bump for repos without
  one). Workflow `readContract` injects the belt path into every phase prompt.
- SKILL.md updated (no longer "backend/Java only"). Syntax verified.

## 0.3.0 (2026-06-02)

**Instrumentation migrated from v1: per-phase confidence + a Retro auto-improve phase.**

- Every phase now returns soft `confidence` (0-100) + `confidence_deductions` (signal, not a gate),
  injected via a shared blurb appended to every phase prompt. Schemas allow the fields.
- New final **Retro** phase (`contracts/9-retro.md`): runs on every terminal outcome (success or
  halt), scores the run twice /100 (task_confidence + factory_fitness) with every lost point
  accounted for, lists red flags, proposes concrete next-run improvements, and writes telemetry to
  `runs/` plus a next-run improvement handoff. AWAITING_HUMAN pauses skip Retro (they resume).
- Pipeline refactored into `runPipeline()` + a `trace` of per-phase status/confidence fed to Retro.
- Added `runs/` directory. Bumped to 0.3.0.

## 0.2.0 (2026-06-02)

**Adversarial-cascade + prompt-specialist fixes; back-half restructure from verified Workflow API.**

Reviews: adversarial-cascade (Quinn + Codex-framed) and an independent prompt-engineering specialist.
API behavior verified via claude-code-guide. Full triage in `docs/review-findings-v0.1.0.md`.

Code (workflow.js):
- Null-guard every `agent()` return (skip → `HALT_AGENT_SKIPPED`).
- Enforce `status:'stuck'` halts for design, grill, implement, ship-prep (previously swallowed).
- Add missing `phase('Design')`.
- `capQaVerdict`: canonicalize `execution_verified` to string, drop dead boolean check, warn on
  unrecognised values. Add `evidenceCappedOverall` (a PASS AC with no code_ref+test_ref caps to PARTIAL).
- `preShipBlockers`: execution gate now explicitly rejects `infra_blocked`/`false`/missing, and
  requires the branch to have been pushed.
- Resume loop guard: `BLOCKED_NEEDS_HUMAN_AGAIN` instead of re-looping the concierge.
- Schema tightening: required `repos`, `ticket_folder`, `summary` (concierge); `minimum:0` on
  `criticals_open`/`ac_count`; `minLength:1` on `branch`; pattern on `execution_verified`; `notes` added
  to PHASE_SCHEMA.
- Remove unused `ticketFolder` arg; concierge now RESOLVES and returns `ticket_folder`; absolute
  contracts path (no `~`).

Structure (from verified API limits):
- Skills not callable inside a workflow agent → **Ship is code-prep only**; MR + Jira + transition move
  to the main loop. New terminal state `READY_TO_SHIP`.
- Sibling agents can't see each other's worktree → **Implement pushes the feature branch**; Review/QA/
  Ship-prep run with `isolation:'worktree'` and fetch+checkout it; Implement also writes a diff artifact.
- Single worktree owner: removed `git worktree add` from contract 4 (runtime owns it).
- No native wait → **Validate removed from the auto-run**; main loop runs it post-merge.

Contracts: all 8 updated — concierge returns `ticket_folder` + example open_question; design/grill add
reason-before-file + artifact paths; implement pushes branch + writes diff + dependent-AC stuck;
review defines `demonstrated` + severity rubric + fetch/checkout; qa adds Inputs + example row +
evidence rule; ship-prep is prep-only; validate is a post-merge main-loop step.

## 0.1.0 (2026-06-01)

Initial seed build: workflow spine + 8 backend-floor contracts + SKILL.md. Never run.
