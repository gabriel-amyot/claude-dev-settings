# Pre-run Readiness Checks

A **soft** pre-flight check: would this ticket survive a dark-factory run, and if not, whose fault is it — the ticket's or the factory's?

Run before launching, typically from `/sprint-estimation`. It never blocks anything. Some tickets are expected to fail permanently, and recording *that* is the point.

## Why it exists

The factory already emits `BLOCKED_UNSUPPORTED_FLOOR` when no belt matches, and the documented remedy is "rack a new belt." But that signal only appears *after* a run is spent, one ticket at a time, with no memory across runs. A single ticket with no belt is noise. Six tickets of the same shape over a quarter is a belt-investment case.

This folder is that memory.

## The distinction that matters

Two failures look alike and are not:

| Class | Whose problem | Remedy |
|---|---|---|
| `SPEC_GAP` | The ticket's | Refine outside the factory, then launch |
| `BELT_GAP` | The factory's | Rack a belt — or decide never to |
| `STRUCTURAL_GAP` | The factory's | Sequential single-belt split; a floor if it recurs |
| `POLICY_GATE` | Neither | Human gate is correct. Make the handoff clean |
| `READY` | — | Launch |

Every check records `spec_quality` independently of `verdict`. That decoupling carries the whole argument: **a ticket with good spec quality that still fails proves the factory is the limiter, not the writing.** Without that field, belt gaps and thin tickets are indistinguishable in aggregate.

## Layout

```
readiness/
  README.md                        this file — the contract
  totals.yaml                      aggregates ONLY, grows with categories not checks
  check-{date}-{TICKET}.yaml       one per check, full detail
```

`totals.yaml` never gets a per-check row. Recompute its counters from the `check-*` files; do not hand-increment. The per-check files are the source of truth.

## Verdict vocabulary

Mirrors the factory's own terminal states so predictions can be scored against outcomes later.

- `READY` → predicts `READY_TO_SHIP`
- `SPEC_GAP` → predicts `BLOCKED_SPEC_QUALITY`
- `BELT_GAP` → predicts `BLOCKED_UNSUPPORTED_FLOOR`
- `STRUCTURAL_GAP` → predicts `BLOCKED_UNSUPPORTED_FLOOR` (multi-repo, not missing belt)
- `POLICY_GATE` → predicts `GATE_REQUIRED`

## Gate dimensions

Drawn from the concierge's real pause conditions and the lessons catalog:

| Dimension | Fails when |
|---|---|
| `ac_available` | AC text is not in Jira or an `AC-LOCAL.md` |
| `placement_resolved` | UI placement, routes or structure unspecified |
| `fixtures_seeded` | A `visual` AC with `fixture:missing`, or a needed artifact lives outside the repo |
| `no_open_forks` | Spec or AC text leaves a decision open |
| `single_repo_single_belt` | Full-stack multi-repo — one-shot not built |
| `data_availability` | AC references fields absent from the data model (lesson 009) |
| `belt_match` | No `toolcrib` detect rule matches the deliverable |

A frontend ticket that will halt at `HALT_PRESHIP` for lack of live visual proof is **not** a readiness failure (lesson 010). It is the belt being honest, and resolves through the post-merge validate model. Record it under `expected_run_shape`, not as a gate failure.

## Promotion

When a `gap_categories` entry crosses its `threshold` while the tickets in it are mostly `spec_quality: good`, write it up as a lesson in `documentation/bibliotheque/development/dark-factory/lessons/` and update that catalog's INDEX. Same path `runs/` already uses to feed `lessons/`.

Thresholds are deliberately unequal. A missing belt is cheap to rack, so 5. A new floor is expensive, so 8.
