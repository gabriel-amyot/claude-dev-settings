# Protected-Module Guardrails — Isolation, Not Restriction

**Trigger:** You write or review a "never touch module X" rule. A guardrail blocks a change the
architecture now requires. You must fence a module other teams depend on.

**Source:** session `bold-newt` — KTP-571 Planning Map, O-06 code-reuse grilling (2026-09-17).

---

## A Blanket "Never Touch X" Becomes Self-Defeating Once Reuse Is Symmetric

KTP-571's decision D-01 said the rewrite never touches `components/map/`. The rule existed to
prevent a mindless refactoring spree on the map that clients depend on. It worked while the new
code only consumed the old.

Once the reuse contract became symmetric, the blanket forbade the five-line additive registration
that the contract needs. A rule written to stop damage now blocked the design it was protecting,
so it had to go.

**How to apply:** A guardrail written under a one-way dependency expires when the dependency
becomes two-way. Re-read every "never touch" rule at the moment the architecture changes
direction, not at the moment it first blocks someone.

## The Obvious Replacement Is Wrong

The tempting fix is a mechanical **shape rule**: permit only source and layer registration, block
anything that touches the store, a handler, or an existing function. It reads like a clean hook
predicate and it is the wrong rule.

Removing duplicated code in order to share it is a refactor by definition. A shape rule therefore
blocks precisely the good case. It confuses "risky" with "touches existing code," and those are
different properties.

## The Working Form Is Isolation

1. **No refactors of the protected module's internals.** The prohibition stays on the class of
   change that caused the original fear.
2. **Every change to the module is isolated in its own merge request**, reviewed alone, never
   bundled with feature work.
3. **The aggregate is visible.** Carry a marker so the running count of such changes is legible at
   a glance.

Isolation judges the **packaging**, not the change. It lets a correct additive change through and
still forces each one to be seen.

Point 3 is the one people skip and it is the one that matters. Thirty individually-fine changes
that add up to an undecided rework is the real failure mode, and per-change review cannot see it.
Only a running total can.

**How to apply:** When you must fence a shared module, write the rule against packaging (one MR,
reviewed alone, counted) plus one narrow prohibition (no internal refactors). Do not write it
against the diff's shape. Add the aggregate marker in the same commit as the rule, because a rule
without a counter is a rule nobody can enforce later.
