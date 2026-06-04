# Tooling & Loadouts — dark-factory

How the factory equips an agent with the right tools for a run. The analogy, the mechanics, who does
what, and the future direction (skills-as-loadouts). This is the canonical tooling doc; the
tool-belt mechanics referenced in ADR-002 and the parked notes point here.

**Status:** the *mandatory* layer (build/tester belts) is built (0.4.x). The *optional* layer
(abilities / skills-as-loadouts, plugins-as-crib, use-case library) is **future** — documented here,
not yet wired.

---

## The analogy (the maintenance surface)

- **Blueprint** = the workflow spine (the deterministic+agentic state machine). The *class*; a run is
  the instantiated *quest*. Built.
- **Tool belt** = the loadout an agent equips for a run.
- **Tool crib** (`toolcrib/`) = the rack you equip from; one file per work-type.
- **Concierge** = front desk: gathers spec/intent/context, and **proposes** the loadout.
- **Dispatcher** (future) = the one who actually equips the belt / confirms a loadout exists and points
  the agent down the right map. For now the concierge does this.

## Two LOADOUTS — do not conflate them

This is the key distinction (Gab's call): there are two different kinds of tooling, and they must not
be mixed.

| | **Mandatory: the tool belt** | **Optional: abilities** ⚑ |
|---|---|---|
| What | build + tester tools for the two work-type sockets | discretionary skills the agent MAY equip (mapping, adtech, klever-data, …) |
| Required? | yes — the spine's JS gates enforce the proof | no — situational, composed per the work |
| Who picks | concierge proposes belt id; gate halts if unsupported | concierge/dispatcher suggests a curated set at the start |
| Where it lives | `toolcrib/<belt>.md` | plugins + a use-case library (future) |
| Naming | "tool belt" / "build + tester loadout" | ⚑ "abilities" vs "tools" — TBD |

The mandatory belt is about *proving the deliverable*. Abilities are about *getting the work done
faster with the right domain skills*. Keep them in separate buckets so a flexible ability can never
weaken a mandatory proof gate.

## Who does the loadout, who uses it

1. **Concierge** reads the ticket + repo signals + (future) the use-case library, and proposes: the
   **belt** (mandatory) and a curated set of **abilities** (optional). Human confirms.
2. **Dispatcher** (future) equips the agent and points it at the right map/context.
3. The **phase agents** use the equipped tools through the run.

## Principle: boxed-in, predetermined, visualizable

Today, tools are scattered and Claude Code auto-discovers them ad hoc. The intent here is the
opposite at the *start* of a run: a **predetermined, curated, visible loadout** chosen at the
concierge/dispatcher step, so you can see exactly what the agent will carry before it runs. The agent
may still go find more mid-run, but it begins well-equipped, not improvising from a scattered pile.

## Repos & context are part of the loadout

Which repos a run touches is known upfront (concierge/dispatcher) and is itself context the loadout
carries. Repo signals help *infer* the work-type but not 1:1 (a frontend repo can hold TypeScript AND
Python scripts), so belt/ability selection keys off the *deliverable*, not just repo file types.
Context (where to fetch domain knowledge) should come via the **use-case library** (below), not be
carried wholesale — progressive disclosure.

---

## Future: skills-as-loadouts, plugins-as-crib, the use-case library

The direction (from a parallel planning session — names still being decided there, not here):

- **Plugins become the crib's stock.** Domain skills get boxed into plugins instead of scattered:
  a **mapping** plugin (geocode, tileset, mapbox, crosswalk, location-scrape), an **adtech/vendors**
  plugin (placer, goldfish), loose **klever-data** skills (bq-store-lookup, geocode-bq-locations),
  plus existing **session** and **floor-manager** machinery.
- **A use-case library is the bridge.** A bibliothèque section (⚑ `use-cases/` vs `playbooks/` vs
  `runbooks/`) where each page maps a *goal* → the layers/skills it composes → bridges (keywords,
  tables, IDs) → gaps → SOP steps. The concierge consults it to assemble the right ability loadout for
  a goal (e.g. "onboard advertiser stores" → geocode → BQ → sheet). Seed page: the proven KTP-755
  onboarding workflow.
- **An explicit map of loadouts.** Our own curated map of which abilities serve which use-cases — so
  selection is deliberate and visible, complementing (not replacing) Claude Code's native discovery.
- **Migration discipline (the other session's plan):** stand up the new plugins + skills → build the
  use-case-library bridge → retire the old scattered skills last. New up before old down; nothing
  orphaned mid-flight.

See `docs/second-floor-refining-notes.md` for the concierge/dispatcher/persona-loop parking lot, and
`docs/roadmap.md` R5 + R8 for the staged plan. **None of this is wired yet** — the factory currently
ships with the two mandatory belts (`java`, `scripting`) only.
