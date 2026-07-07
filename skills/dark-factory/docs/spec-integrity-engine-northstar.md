# Dark Factory — Spec-Integrity Engine (NORTH STAR vision)

**Status:** VISION / North Star. Captured 2026-06-17 from Gab's brain-dump during the
system-integrity-gate grill. **Not yet designed — needs its own dedicated design session.**
Prerequisite-gated (see below). This is the **big sibling** of the structural integrity gate
(`system-integrity-gate-design.md`): that gate is **Thread A (build now)**, this is **Thread B
(design later)**.

## Two threads (the distinction that matters)

- **Thread A — structural integrity gate (building now).** Question: *"does removing/changing this
  symbol break an existing CONSUMER?"* Code-level (grep consumers + scan in-flight branches). Catches
  the KTP-677 over-deletion. Skips `additive`. Does **NOT** catch behavioral regression or spec drift.
  Low-hanging fruit precisely because it sidesteps any need for a system spec.
- **Thread B — spec-integrity engine (this doc).** Question: *"does this ticket's intent COLLIDE with
  the system's specification — and if the system spec must change, is that change INTENTIONAL (a human
  confirmed it) or an accident?"* Semantic, not mechanical. This is where `additive` and behavioral
  changes are handled (Thread A intentionally punts both here).

## The premise

There is a **reliable, up-to-date specification of the whole system.** Today that is the agent-OS
corpus — and it is **incomplete**. Making it reliable + complete, across repos, is itself the
foundational prerequisite (this is "Gap 2" in the gate design).

## The flow Gab described

1. A new ticket arrives with its AC + the ticket's own spec.
2. Compare the ticket's AC/spec against the **system's overall spec**.
3. **Discernment:** is this a COLLISION with the system, or purely ADDITIVE?
   - **Additive** → add the new capability to the system spec.
   - **Collision** → the ticket changes/breaks existing spec. Resolve it:
     - Back to the stakeholder/developer: *"you asked for X; the system currently specifies Y. Is
       changing/breaking the existing spec INTENTIONAL, or a mistake?"*
     - Heuristic (but never assume): a ticket explicitly about modifying feature F probably intends to
       change F's spec — but still **require human confirmation** from someone who understands the
       context (the dev) or owns it (the stakeholder).
4. This discernment happens **UPSTREAM** (early — at/near the start of the build).
5. Result: the system's overall specification is **updated intentionally** to reflect the post-ticket
   world.
6. **The inversion Gab proposes:** the **first part of the factory UPDATES the spec** (on the same
   branch/worktree) to the intended end-state. Then **downstream — implementation, tests, and
   especially REGRESSION testing — run against the up-to-date spec.** The spec becomes the source of
   truth the tests assert against, and it always reflects current intent.

## Where it lives (Gab's instinct)

- **NOT a tool belt. NOT a floor.** It is **structural — "in the veins of the system."**
- Probably a new **room / step** (likely two: an upstream spec-collision + spec-update step, and a
  downstream regression-against-spec step), woven into the spine — not a per-work-type belt.

## Relationship to Thread A (the fit — so A is not reworked)

- A introduces the **Integrity room** (a new phase + the `BLOCKED_SYSTEM_INTEGRITY` terminal + a
  blast-radius scanner).
- B grows in that room: it enriches the integrity check to also consult the **system spec corpus**,
  and adds the upstream spec-collision/spec-update step.
- So A is the **first tenant** of the room B expands into. **Build A leaving that seam clean.**

## Why B cannot be built now (prerequisites — the honest blockers)

1. A reliable, complete, **machine-comparable system specification** (agent-OS backfill across repos).
   Without it, "compare AC to system spec" has nothing to compare against. Large work item on its own.
2. A **semantic collision-detection** design (AC-vs-spec is discernment, not a grep).
3. A **stakeholder/dev confirmation loop** design (who confirms an intentional spec change, and how).
4. The **update-spec-first / test-against-spec inversion** must be designed against the existing TDD +
   QA gates without breaking them.

## Hard open questions (for the dedicated session)

- What **format** is the system spec, so it's both human-readable and machine-comparable — agent-OS, or
  something new?
- How is it **kept reliable/current**, and how do we trust it? (Recall the fetch-before-read lesson:
  derived knowledge docs lie when stale — the spec corpus must not become another unreliable doc.)
- How does **AC-vs-system-spec collision detection** actually work (semantic compare + LLM discernment
  + evidence)?
- **Who confirms** an intentional spec change, and at what gate? (Upstream human gate; crit on the spec
  diff — ties to the cautious-mode crit idea in the gate design.)
- The **inversion**: does the factory really update the spec FIRST, on-branch, before code? How do
  downstream tests consume it?
- **Org reality:** stakeholder-in-the-loop for collisions (Klever: Amal/PO, Marc-André/tech-lead).
- Does B eventually **subsume** Thread A, or stay a richer layer above it?

## Scope call (2026-06-17)

**B = its own dedicated design session.** Gab's lean, and I concur — not as reflexive agreement but
because B is **prerequisite-gated** (needs the spec corpus, which doesn't exist yet) and carries
**unresolved hard design** (semantic collision, the confirmation loop, the inversion). It is **not** a
low-hanging fruit. **A continues and ships now; A's room is built to be B's future home.** This doc is
the warm-start so the B session opens with full context instead of a cold page.
