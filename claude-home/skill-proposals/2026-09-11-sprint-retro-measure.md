# Skill Proposal: sprint-retro-measure
Date: 2026-09-11
Source: Q3 Sprint 5 retro — built the measurement ad hoc, will be needed every sprint

## Problem

Retro decks are built from Jira board state, which overstates every past sprint permanently (an issue carried forward keeps its old sprint value). The Sprint 5 deck reported Sprint 3 at 47.5% complete; the real at-close figure was 44.4%, and the board now reads 78.2%. Nobody noticed because nothing recomputes it.

The measurement was written from scratch this session. It should not be rewritten next sprint.

## Trigger

At sprint close, or when preparing a retro deck. Phrases: "measure the sprint", "what did we actually complete", "retro numbers", "how did sprint N really do", "is the board telling the truth".

Also on day one of a sprint, for the roster snapshot (see Constraint below — this half is time-sensitive and easy to miss).

## Scope

Org (Klever). The changelog reconstruction is generic Jira; the board id, project key and sprint naming are Klever-specific.

## Draft steps

1. **Day one of the sprint:** freeze the roster (`snapshot_roster.py`). Without this the never-moved metric is not computable at close, because the Thursday board cleanup removes exactly the untouched tickets.
2. At close, pull the sprint plus its two predecessors (membership, points, types, assignee, sprint-history array).
3. Fetch status changelogs; reconstruct status **at the sprint boundary**, not today.
4. Emit: done-at-close vs done-today, finished-after-boundary, carry-in vs fresh with completion rates for each, unpointed share, created-mid-sprint, never-moved against the frozen roster, sprint-ride-count distribution and the longest riders.
5. Emit throughput (issues transitioned to Done inside the window) as the anti-gaming companion metric.
6. Write `metrics.yaml` (committed) and gitignore the raw dumps (stale within days).

## Existing code

Working scripts at `general/sprints/sprint-5-q3-2026/reports/retro-analysis/`: `pull_sprint_data.py`, `at_close.py`, `analyze.py`, `q2_sensemaking.py`, `untouched.py`, `snapshot_roster.py`. These are the skill, minus packaging and parameterisation (sprint ids are currently hardcoded in a `WINDOWS` map).

## Open question — probably a mode, not a new skill

`klever-sprint-exit` and `klever-sprint-mgmt` already exist and both touch sprint close. This may belong as a `measure` mode on one of them rather than a seventh sprint-named skill. The project CLAUDE.md already carries a routing table warning that "several skills carry sprint in the name" and that they get confused. Adding another without checking that table would make the documented problem worse.

Decide the routing before building.

## Constraint to carry into the skill

Do not emit the per-assignee breakdown of never-moved by default. The distribution is even across the team; surfaced as a table it reads as individual performance rather than a process defect. Aggregate only, unless explicitly asked.
