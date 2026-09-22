# wayfinder — Changelog

Every change to `SKILL.md` bumps `version:` here and adds an entry. The coupling is
checked by `tools/wayfinder_runs.py check`, which `harvest` and `reflect` run for you.

Why it matters: every run trailer records the `spec_version` it ran under. If the spec
changes without a bump, runs are attributed to a spec that no longer exists and the
evidence for the next improvement is quietly wrong.

## 0.3.0 (2026-09-12)

**A finding from outside the route had no typed way onto the map.** The loop was outbound: a route
session claims a ticket, resolves it, records it. A session that learned something without owning a
ticket had two options, and both lose information. A bare `gh issue comment` leaves no trailer, so
`harvest` never counts the run. The `wayfinder-feedback:` convention *is* harvested, but it carries
to the reflection brief, which is the retro on the vehicle, not to the next route session that needs
to act on the finding.

Adds a third option, typed and addressed to the route:

- **`wayfinder_runs.py report`**, with `mode: report` and a `reported` outcome. Both were required:
  `validate_run` whitelisted mode to `chart|resolve|reflect` and outcome to the six terminal states,
  so a report trailer parsed as valid YAML and was then bucketed as `malformed_trailers` — traced,
  but reported as broken telemetry. `--source` is required, because an outside run is only
  trustworthy if it says what produced it.
- **`## Report back` on every ticket.** The moment a ticket is written is the only moment the map
  knows what it will be waiting for. Named facts when the shape is known, an open question when it
  is not.
- **A `Report back` section**, defining the inbound path and splitting it on whether the reporting
  session owned a ticket.

**What this does NOT change.** `resolve` already closed any ticket carrying a `wayfinder:` label,
including types outside the taxonomy, and `--force` already bypassed the foreign-assignee guard. A
session that owned a ticket could always close it traceably. The `--ticket` shape of `report` is a
telemetry-fidelity improvement over that, not a new capability: it records `mode: report` with a
`--source` instead of `mode: resolve`, which would attribute the run to a route session that never
happened, and it avoids overloading `--force`, which also suppresses the duplicate-comment guard.

The skill is `wayfinder-report-back`, a sibling. Deposit and dispose stay separate: a reporting
session never graduates fog, creates tickets, or edits the map body.

## 0.2.3 (2026-09-10)

**The frontier query counted closed blockers.** `select((.blockedBy.totalCount // 0) == 0)` filtered
on `totalCount`, which counts every dependency edge regardless of state. A ticket that was *ever*
blocked therefore never returned to the frontier, even after every blocker closed — contradicting
the definition one paragraph above it ("A ticket is unblocked when every ticket blocking it is
closed"). The query could only ever surface tickets that were never blocked at all, which defeats
the point of wiring dependencies.

Measured on a live map while resolving a ticket: the spec's query reported a 2-ticket frontier; the
real frontier was 6. Three takeable tickets were invisible, including one whose decision was due
that same day.

- **Fix:** `select(([.blockedBy.nodes[] | select(.state == "OPEN")] | length) == 0)`.
- **Second trap documented** under the existing `blockedBy` trap. The file already warned about the
  object-vs-array shape; that warning caught one instance and missed this one in the very query it
  was written to protect. The generalisable lesson, now recorded: a hand-written `jq` filter over a
  GitHub payload needs a check against a known-good case before it is trusted, and the spec's own
  suggested verification (`gh api .../dependencies/blocked_by`) would have caught it.

## 0.2.2 (2026-09-10)

**Orient the human before the first claim.** Work mode gained step 2: before any write,
post the map's linked name, where the route stands, the intended ticket, and the session's
planned steps in a few lines. A read-back, not a permission request. Source: Gabriel's
feedback on map 38 — the session claimed and ran the first frontier ticket while he
expected an overview of the map and the plan first. Matches the `spec-missing` friction
logged on that map's run trailers (run 920290db).

## 0.2.1 (2026-09-10)

**The Horizon.** The map could say a thing was in scope but unclear (**Not yet specified**) or
ruled out for good (**Out of scope**). It had no way to say the third thing: work we **will**
do, deliberately not now. Moving this MCP off laptop-installed bundles onto a hosted server is
the shape of it. Not rejected, just the next stage.

The cost of the gap was real. Deferred work had to live in the fog, where it re-surfaced as a
ticket candidate every session, or under Out of scope, where the next reader took an obvious
improvement for a rejection and re-opened the argument. Either way a later grilling burned a
session re-deciding what was already decided.

- **New `## Horizon` section in the map body**, between *Not yet specified* and *Out of scope*.
- **Prose defining it against both neighbours.** The three sections split on two axes (in scope
  or not, sharp or not), which is why they cannot collapse into two. A table states it, and each
  boundary reduces to one question: *could I write the ticket today?* against the fog, and
  *rejected, or queued?* against out of scope.
- **The graduation rule.** A horizon item never graduates inside its own map: the frontier stops
  at the destination and the item sits past it. If a resolution makes one urgent, the destination
  is wrong, and redrawing it is an open decision on the map, not a quiet promotion.
- **On map close**, the Horizon is the seed of the next map, carried into the next charting
  session as its loose idea. Not deleted, and never folded into *Decisions so far*.
- **New `horizon` outcome** in `wayfinder_runs.py`, for a live ticket that turns out to be
  deferred rather than rejected. Kept distinct from `out_of_scope` so a retro cannot read a
  deferral as a scoping mistake. Purely additive: trailers written under 0.2.0 still validate.
- **`## This skill's own Horizon`** at the foot of `SKILL.md`, whose first entry is a per-type
  ticket quality bar with a deterministic closeable check, deferred on 2026-09-10 with its
  reasons recorded. The section demonstrates the feature it documents.

The map body is not parsed by any tool (`chart`, `resolve`, `harvest` and `reflect` read issue
titles, labels, state and comments only), so the new section cannot break them.

## 0.2.0 (2026-09-10)

**Self-improvement telemetry.** The spec had no version, runs left no trace, and nothing
fed a session's experience back into the spec. Adapted from `dark-factory`'s Retro +
`runs/` + CHANGELOG pattern, reshaped for a GitHub-Issues substrate and for prose (no
orchestrator, so no un-skippable gate — see the honesty note below).

- **`version:` frontmatter + this changelog.** `0.1.0` is the pre-telemetry spec.
- **The run trailer.** Every session appends one collapsed `wayfinder_run` YAML block to
  a comment it already had to post: the charting comment on the map, or the resolution
  comment on a ticket. It records `run_id`, `spec_version`, mode, outcome, tickets
  created, fog graduated, and `friction[]` over a closed tag vocabulary.
- **`tools/wayfinder_runs.py`.** `chart`, `resolve`, `reflect`, `harvest`, `check`.
  `resolve` replaces the comment-then-close pair the spec already prescribed, so the
  telemetry is the same action as the work rather than a step after it.
- **The reflection ticket** (`wayfinder:reflection`), planted at charting time as the
  map's terminal act and excluded from the frontier query by label. Its resolution must
  produce a SKILL.md diff plus a version bump, or record that it produces neither.
  Reflection is repeatable: `reflect --interim` when RECURRING friction says the spec is
  costing you now.
- **`runs/`** — a derived cross-map cache. `harvest` is the only writer, so concurrent
  sessions cannot interleave a write. GitHub is the source of truth.
- **`hooks/wayfinder-close-guard.sh`** — a warn-only, network-free nudge when a wayfinder
  issue is closed outside the traced path.
- **Frontier query** gains a `wayfinder:reflection` exclusion clause.

**Honesty note.** This telemetry is best-effort by placement, not mandatory. Nothing can
stop a session closing an issue in the GitHub UI and leaving no trace. What the design
buys is that the traced path is the easy path, and an untraced run is *detected* by
`harvest` as a GAP instead of vanishing. dark-factory can enforce its Retro because a JS
orchestrator runs its loop. Wayfinder is prose, and prose does not enforce.

## 0.1.0 (2026-09-04)

Baseline: the spec as first adopted, at commit `55803b2`, plus the `blockedBy.totalCount`
frontier fix. No version, no telemetry, no changelog — this entry is retroactive and
names what the run trailers call "version 0".

- The map as a single GitHub issue on `gabriel-amyot/klever-project-management`, labelled
  `wayfinder:map`, with child decision tickets.
- Four ticket types: `research`, `prototype`, `grilling`, `task`. HITL versus AFK.
- Fog of war, **Not yet specified**, and **Out of scope** as distinct sections.
- Two invocation modes: chart the map, work through the map. One ticket per session.
- Native GitHub issue dependencies for blocking; the frontier is open + unblocked +
  unassigned.
- The `blockedBy` object-not-array trap, which had made the frontier read as permanently
  empty.
