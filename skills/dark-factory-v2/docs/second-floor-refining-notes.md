# Second-Floor — Refining-Phase Notes (PARKED, do not build yet)

Captured 2026-06-02 (wise-owl, Winston session). These are Gab's conceptual intentions for the
SECOND-FLOOR REFINING PHASE — deliberately NOT implemented in the fast scripting path. Revisit when
hardening the routing/persona layer.

## Vocabulary (Gab's mental model — the analogy IS the maintenance surface)

- **Blueprint** = the workflow spine (deterministic+agentic state machine; Minions sense). The *class*.
  A run = the *instantiated object* — an agent's **quest** / adventure map. Already built.
- **Tool belt** = the per-run tool loadout an agent wears for the build + tester sockets.
- **Tool crib** = the place/rack where an agent goes to EQUIP its belt before the run, then leaves.
  (NOT "a curated subset" — it's the equipping room. The belt is what's worn.)
- **Concierge** = front desk. Specification + intent gathering, human-in-the-loop. Kept.
- **Dispatcher** = (PARKED) a distinct role the concierge talks to: "here's what we're told — can you
  dispatch this? do you have a tool belt / agent / flow for it?" If no → honest "not tooled" halt.
  Possibly the dispatcher also builds/selects the belt and points the agent down the right map.

## Personas to plug in (PARKED)

- **Spec specialist (Leo)** at the front: a refinement LOOP — input spec → refine → gather intent →
  confirm completeness — before the line runs. This is where the human stays involved.
- **Architect (Winston)** "in another department": the concierge converses with the architect for the
  design phase. The architect doesn't build the full design — he gets his clarifying questions
  answered until satisfied; until then the concierge holds the user. When everything's answered, the
  agent leaves and the pipeline starts.

## Open design thoughts (PARKED)

- Maybe NOT all tools are selected at the concierge stage; the flow can equip more along the way.
- Concierge (front-facing) vs Dispatcher (tooling/routing) as separate agents.
- "Don't see the factory as a physical thing — see it as a quest for an agent." Map + tool belt +
  dispatcher guiding equipment and direction.

## What the FAST path (now) deliberately does instead

One concierge (no separate dispatcher), it classifies the work-type and proposes a tool belt from the
crib; unsupported → honest halt. No architect/spec-persona loop yet. Just enough to run a scripting
(side-effect) ticket. The above is the refining-phase backlog.
