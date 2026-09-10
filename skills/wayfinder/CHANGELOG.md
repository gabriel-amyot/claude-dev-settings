# wayfinder — Changelog

Every change to `SKILL.md` bumps `version:` here and adds an entry. The coupling is
checked by `tools/wayfinder_runs.py check`, which `harvest` and `reflect` run for you.

Why it matters: every run trailer records the `spec_version` it ran under. If the spec
changes without a bump, runs are attributed to a spec that no longer exists and the
evidence for the next improvement is quietly wrong.

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
