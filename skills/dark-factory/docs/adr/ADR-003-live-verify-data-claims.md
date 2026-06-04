# ADR-003: Live-verify data-layer claims; stale local checkouts are not evidence

**Status:** Accepted (2026-06-02, Gab + Winston)
**Session:** wise-owl · **Source:** KTP-728 first live trial (session bright-otter)

---

## Context

The first live trial surfaced the dominant failure mode, and it was NOT a compliance failure (the JS
gates all fired correctly — `HALT_PRESHIP` on 728, `BLOCKED_SPEC_QUALITY` on 699). It was a
**reasoning/staleness failure**, exactly the limit pre-registered in prediction #2:

- The concierge raised a **false data-layer blocker twice** — "BQ view `v_prox_state_performance` is
  missing, blocks the province choropleth" — premised on a **stale local checkout**. Live BQ disproved
  it (advertiser 835 colours Ontario+Quebec from the base tables via `StatePerformanceBigQueryAdapter`,
  no view). The concierge's own confidence deduction admitted its facts "predate the country feature…
  not a fresh local trace."
- Result: **two abandoned runs** (three run-IDs for one ticket). The cost story of the whole trial.
- Same class as the KTP-130 B1 false blocker (21-day delay from a wrong premise) and the
  project-management CLAUDE.md adversarial assumption-audit rule. Recurring, high-cost.

The substrate (un-skippable JS gates) cannot catch this — a confidently-wrong premise sails through a
gate that only checks "did you do the step," not "was your input true."

## Decision

**Any assertion about a data-layer fact must be verified against the LIVE source before it is emitted
as a blocker or pinned as a design assumption. Stale local working trees are not evidence.**

Applies to claims about: a table/view existing or missing, a column being present/absent, a column
count, or a serving/wiring path.

- **Data facts** → verify with `bq show --schema` / `bq ls` / `bq query` against live dev.
- **Code/wiring facts** → verify with `git show origin/dev:<path>` (not the local working tree).
- **Every blocker carries a one-line assumption audit:** "what established this, and could the premise
  be false?" (mirrors CLAUDE.md's rule).

This is realized concretely in the 0.5.0 hardening (see `docs/hardening-spec-0.5.0.md`):
the concierge live-verify rule (Contract 1) and the live-schema preflight feeding analyst/design
(pins VERIFIED column names/counts into `assumptions.json`).

## Consequences

- **+** Collapses the false-blocker re-run waste (three runs → one). Kills the F4 "no COUNTRY column"
  and "22-vs-20 columns" errors mechanically. Brings the factory in line with the org's
  assumption-audit doctrine.
- **+** Front-loads truth at the human gate — the one phase where a human is already in the loop.
- **−** The concierge/analyst do more live calls (slightly slower front gate; acceptable — correctness
  beats speed at the gate, and re-runs are far more expensive).
- **−** Requires live access (bq, git fetch) at concierge time; if unavailable, the blocker is marked
  *unverified* and explicitly flagged to the human rather than asserted as fact.

## Status of the principle

This is a **big, look-back-worthy decision** (why the concierge got slower + more rigorous): false
premises are the highest-cost failure the factory has produced, and the substrate cannot catch them —
only live verification can.
