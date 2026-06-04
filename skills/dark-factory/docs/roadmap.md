# Dark Factory v2 — Roadmap (post-seed)

**Session:** wise-owl · **Date:** 2026-06-01 · **Status:** Future scope. Explicitly NOT in the first version.

The first version is: **one workflow spine + one floor (backend/Java) + one real ticket,
like-for-like, human concierge front gate.** Everything below is deferred until that seed proves
out and is measured. Ordered roughly by when it likely makes sense, not strict priority.

Governing rule still applies: **seed, ship, build on — no monument.** Each item ships only after
the previous layer has earned trust.

---

## R1 — Targeted design rigor: redesign + compare + judge

**What:** When a *specific step's design* (not the overall architecture) is flagged "unworkable,"
spawn a fresh zero-context agent to redesign that step from scratch, then a judge agent compares
the blocked design vs. the new one. Only if both fail does it escalate to the human.
**Why later:** Costs N× tokens *per flagged decision*. Only worth it once the spine is proven and
we can aim it at genuinely high-risk steps. Self-healing before human interrupt = less interruption,
but earn it first.
**Trigger threshold:** "likelihood we'd have to re-run everything if this assumption is wrong."

## R2 — Blind implementation ("two buildings")

**What:** Test-writer agent and implementer agent both receive the spec, in parallel; the
implementer never sees the test code and must pass tests it didn't write.
**Why later:** Quality gate against "test suite gaming" (brief Risk #3). Adds parallel agents =
cost (and the caching trade from fresh contexts). Add after the single-pass spine is measured.

## R3 — Multi-gate verification + segregation + model diversity

**What:** Independent gates (build, lint/Semgrep, blind unit, integration, spec-compliance), each
its own agent/tool; code-writer ≠ test-writer ≠ reviewer; mix models to break monoculture.
**Why later:** Each gate needs external tooling wired (Semgrep/CodeQL/mutation/Signadot-style).
Substantial. Sequence them onto the proven spine one gate at a time.

## R4 — Multi-floor expansion

**What:** Add floors beyond backend/Java: frontend/Node, SQL/Dataform (4-phase BQ harness),
scripting, fullstack (compose floors), meta-harness. Per the `2026-05-27-dark-factory-floor-
specialization.md` handoff. Shared front (spec/context/grill), forked verify/QA per floor.
**Why later:** Each floor = its own verification contract. The KTP-680 session proved the SQL
floor needs BQ assertions, not "start the server." Grow one floor at a time after backend is solid.

## R5 — Floor-manager as tool-crib / dispatcher

**What:** A router that reads a ticket, picks the floor, sets the default autonomy tier, and hands
each spawned agent a *curated tool surface* (per-role tool profiles via ToolSearch / deferred
tools — implementer gets these ~15 tools, tester gets those).
**Why later:** This is a *different job* from today's `/floor-manager` (a human-facing recommender).
Reuse the name/metaphor, not the code. Needs the floors (R4) to exist first.

## R6 — Lights-out per floor (progressive autonomy) + the infra it requires

**What:** Per-floor autonomy tiers — **dark** (auto-merge, monitor only), **cautious** (auto-merge +
log), **hold** (human review). "Turning off the lights" on a low-risk floor = promoting it to dark.
**Why this is gated on infra:** you cannot responsibly auto-merge with no human unless a rogue or
wrong agent is *contained* and *governed*. That requires:

- **Firecracker microVMs / CodeSandbox** — per-agent sandboxes that boot in <1s with VM-level
  isolation (read-only filesystem except workspace, allowlisted network). *Why:* prerequisite for
  any dark floor — contain a compromised/runaway agent so it can't damage the broader system.
- **Leash + Cedar** — kernel-level permission policy (governance enforced by the OS, not by asking
  the agent nicely). *Why:* "governance as infrastructure, not hope." Lets you trust a dark floor.
- **Confidence scoring (weighted avg → Dempster-Shafer) + immutable audit log.** *Why:* evidence-
  based routing into dark/cautious/hold, and an explainable trail for any production issue.
- **Temporal.io** — a durable workflow *server*. *Why future-option:* if the factory ever outgrows
  single-operator Claude Code workflows (multi-day, multi-user, must survive machine restarts), a
  durable backend becomes worth it. The Workflow tool covers us until then. Option, not need.

**Until R6 exists, the ceiling stays Cautious/Hold — human at the bookends.** This matches intent.

## R7 — Reasoning-class failure tracking → Supervisr.ai

**What:** The substrate fixes *compliance*, not *reasoning* (hallucinated fields, false-positive
reviews, bad assumptions — lessons L8, L10). Track each reasoning-class failure type separately;
feed the corpus to Supervisr.ai for analysis and future mitigation.
**Why later:** Known accepted gap (see ADR-001). Needs the factory running first to generate the
failure corpus worth analyzing.

## R8 — Abilities: skills-as-loadouts, plugins-as-crib, use-case library

**What:** a SECOND loadout layer alongside the mandatory build/tester belt — *optional* domain skills
("abilities" ⚑) the concierge/dispatcher curates at the start of a run. Full concept in
`docs/tooling.md`. Components:
- **Plugins as the crib's stock:** box scattered skills into plugins — `mapping` (geocode, tileset,
  mapbox, crosswalk, location-scrape), `adtech`/vendors (placer, goldfish), loose `klever-data`
  (bq-store-lookup, geocode-bq-locations), plus existing `session` + `floor-manager`.
- **Use-case library** (bibliothèque ⚑ `use-cases/`): goal → composed skills + context bridges + SOP
  steps; concierge consults it to assemble the ability loadout. Seed page: KTP-755 store onboarding.
- **Explicit loadout map:** curated ability-per-use-case map; deliberate + visible selection at the
  front, complementing Claude Code's native discovery.

**Why later:** needs the plugins + library to exist first, and the mandatory belt layer proven first.
**Hard rule:** an optional ability can NEVER weaken a mandatory proof gate — keep the two loadouts
separate (see tooling.md). Relates to R5 (floor-manager as dispatcher/tool-crib).
**Migration discipline:** new plugins/skills up → use-case-library bridge → retire old scattered
skills last. (Plan + naming owned by a parallel planning session, not here.)

---

## Brainstorm hooks (future sessions)

- "Which floor goes dark first?" — needs R3 + R6 + a confidence baseline from real runs.
- "When does dim become dark?" — the central progressive-autonomy policy question (brief Open Q#4).
- Tie-in to the federated knowledge architecture (Layer 2 domain knowledge) for cross-repo context.
