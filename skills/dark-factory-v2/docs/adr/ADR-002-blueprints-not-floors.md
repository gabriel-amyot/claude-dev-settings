# ADR-002: One blueprint, swappable tool belts (not duplicated floors)

**Status:** Accepted (2026-06-02, Gab + Winston)
**Session:** wise-owl
**Origin:** Stripe Minions — "Blueprint" (deterministic+agentic state machine) + "Toolshed/tool crib"
(curated tools per task). Source: `dark-software-factory/research/analysis/03-stripe-minions-analysis.md`.
Ties to roadmap R5 (floor-manager as dispatcher/tool-crib).

---

## Context

dark-factory-v2 0.3.0 hardwired its build + validation to a Java/Spring service (`mvn spring-boot:run`).
The first live trial (KTP-728) halted **honestly** at the concierge because the ticket is a *scripting
/ side-effect* deliverable, not a service — the Java boot gate could only be skipped or faked, and the
factory refused. We need more work-types without duplicating the pipeline or letting copies drift.

## Vocabulary (corrected against the source — the analogy is the maintenance surface)

- **Blueprint** = the workflow spine itself (the deterministic+agentic state machine). The *class*; a
  run is the instantiated *quest*. **Already built** (`dark-factory-v2.workflow.js`). There is one.
- **Tool belt** = the per-run tool loadout an agent equips for the two work-type-specific sockets:
  the **build station** (Implement) and the **tester station** (execution-verify + QA).
- **Tool crib** (`toolcrib/`) = the rack of tool belts; one file per work-type (`java`, `scripting`).
- **Concierge** = front desk (kept): spec + intent + prereqs, human-in-the-loop; it **proposes** the
  tool belt and halts for confirmation.
- **Dispatcher** + spec/architect-persona loop = **parked** for the second-floor refining phase
  (`docs/second-floor-refining-notes.md`). For now the concierge does the proposing.

## Decision

1. **One blueprint, permanent rooms.** Phases are built once and shared — nothing to duplicate, so
   nothing to drift.
2. **Two sockets only** are work-type-specific: build (Implement) + tester (execution-verify, QA).
3. **A tool belt is a thin card** in the crib: `{ detect, compile/lint, unit test, integration rule,
   execute-verify cmd + success signal, proof shape, has_version_file }`. Pre-racked, **never generated
   on demand** (on-demand = inconsistent; the factory's value is repeatability). The room stays generic;
   the belt is sharp — that's how prompts stay specific without copying rooms.
4. **Concierge proposes + human confirms; unsupported → honest halt** (`BLOCKED_UNSUPPORTED_FLOOR`).
5. **Generalized proof of work:** "run the deliverable on declared inputs, assert the declared expected
   output." Service-boot is one belt's special case; scripting = run-on-fixtures + assert output. The
   `execution_verified` field + JS gates are unchanged; only the belt's tool + meaning differ.

## The hard boundary (the one trade-off)

A tool belt may swap **tools in the two sockets only.** If a work-type needs different *room logic*
(e.g. SQL wanting a JOIN-direction review lens), that is a rare, deliberate **new floor**, not a belt.
Keep belts thin; that discipline is what prevents the drift that duplicated floors would cause. For
Gab's stack (Python, Java, NextJS) it is pure tool swaps — same rooms.

## Consequences

- **+** Zero pipeline duplication / drift. Add a capability = rack a belt + its tester. Specific prompts
  ride in the belt, not the room. Honest halt on unsupported work (demonstrated on KTP-728). The
  analogy = the on-disk structure (`toolcrib/`, named sockets), so the maintainer's model matches code.
- **−** Concierge must classify + the human confirms (more front-door touch; matches intent). Requires
  discipline to keep belts thin (the boundary above).

## Implemented in 0.4.0

Concierge returns `tool_belt`; workflow halts `BLOCKED_UNSUPPORTED_FLOOR` on an unracked belt; Implement
+ QA read the belt for build/execute/proof; `java` + `scripting` belts racked in `toolcrib/`. Realizes
the 2026-05-27 floor-specialization handoff as tool belts, not copied floors. Supersedes v1's prose
tech-adaptation table.
