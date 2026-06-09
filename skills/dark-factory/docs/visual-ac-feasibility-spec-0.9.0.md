# Visual-AC Feasibility Gate — spec (0.9.0)

**Origin:** deft-falcon session, from the 0.8.0 TDD-gate real-run feedback (KTP-728/758/759/788).
**Status:** SPEC (implementation-ready, not yet built).

## Problem (evidenced, recurring)

Four runs — KTP-728, KTP-758, KTP-759, KTP-788 — all terminated `HALT_PRESHIP` for the **same** root
cause, discovered late (at QA) every time:

> The factory cannot self-verify rendered-UI ACs in an autonomous run. `ui-probe` needs Gab's
> authenticated Chrome (not drivable from a QA subagent); dev is often past its 20:00 EDT nightly-off
> (IAP 302); and data-conditional ACs (e.g. KTP-788's Canadian FSA panel) have no renderable fixture.
> So every rendered-UI AC caps at PARTIAL → `HALT_PRESHIP`, *after* burning implement + review + QA.

Two run quotes:
- KTP-759: *"the factory walked into UI work it could not finish tonight."*
- KTP-788: *"Recurring pattern: KTP-728/758/759/788 all HALT_PRESHIP on the same root cause... keeps re-discovering this instead of gating on it up front."*

The 0.8.0 TDD gate itself is **validated and working** in both runs (`trustworthy: true`, same-test
red→green defeated vacuous-RED, frontend `not_applicable` exemptions QA-verified on the diff). This spec
addresses the *different* gap the TDD runs surfaced.

## The reframe (core idea)

"Couldn't auto-verify the UI" is **not** "failed." A frontend ticket whose **logic is TDD-proven, build
is clean, review is clean, execution verified**, and whose *only* remaining gap is a human eyeballing the
rendered output, is **code-complete and needs human visual sign-off** — exactly what an MR review is for.
Blocking its branch push (`HALT_PRESHIP`) is backwards. It should ship to a new state that pushes + opens
the MR with a "visual QA pending" flag.

## Two mechanisms (decisions locked)

### A. Concierge front-gate feasibility check (decision: concierge, not a new phase)

The concierge already classifies the belt and extracts ACs, and the frontend belt already distinguishes
rendered-UI ACs from extractable-pure-logic ACs (the TDD `not_applicable` rule). Extend the concierge to:

1. **Classify each AC** `visual` (rendered-UI: proof is a live screenshot) vs `logic` (unit-testable /
   `not_applicable`). Reuse the belt's existing rule.
2. **Probe visual feasibility** for the run: is a drivable authenticated browser available (autonomous
   run ⇒ effectively no, `ui-probe` needs Gab's Chrome)? is dev reachable (IAP not 302)? does a renderable
   fixture exist for any data-conditional `visual` AC (e.g. a CA-FSA store)?
3. **If `visual` ACs exist AND aren't auto-verifiable this run → raise a `needs_human` open_question UP
   FRONT** (not at QA): *"This ticket has N rendered-UI ACs (AC-1, AC-3) that can't be auto-verified this
   run (dev nightly-off / no drivable authed browser / no CA fixture). Proceed (a) code-only → ship to
   READY_FOR_VISUAL_QA for your eyeball, (b) defer, or (c) local-stack fallback [follow-up]?"* The human
   answers once via `humanDecisions`; the run no longer discovers the wall at QA.

**Schema:** `CONCIERGE_SCHEMA` gains a per-AC `ac_kind` (`visual` | `logic`) classification (or a
`visual_acs: [ac]` list) and a `visual_feasibility` verdict (`auto_verifiable` | `needs_human`). When
`needs_human`, the existing open_question / AWAITING_HUMAN machinery carries the up-front decision.

### B. `READY_FOR_VISUAL_QA` terminal state (decision: yes, add it)

A precise, **safe** relaxation of `HALT_PRESHIP` — only when visual sign-off is the *sole* gap.

**QA schema:** `per_ac` gains `visual_pending: bool` — `true` means this AC's logic + wiring are proven
(code_ref present, any pure-logic RED green) and the ONLY missing thing is the live visual screenshot.
QA already says this in free text; this formalizes it.

**Spine readiness logic** (replaces the single `qaCapped !== 'ALL_PASS' → HALT` path). Compute real
blockers first (unchanged: execution not verified, branch not pushed, open CRITICAL, TDD gate violation,
**or any non-PASS AC that is NOT `visual_pending`** — e.g. a failed logic AC). Then:

| Condition | Terminal state |
|---|---|
| real blockers present | `HALT_PRESHIP` (unchanged) |
| `qaCapped === ALL_PASS` | `READY_TO_SHIP` (unchanged) |
| no real blockers, and **every** non-PASS AC is `visual_pending` | **`READY_FOR_VISUAL_QA`** (new) |

`READY_FOR_VISUAL_QA` still runs **ShipPrep** (version bump + push — the branch must exist for the MR).
The difference is in the main-loop `next_steps`: the MR + Jira comment **flag "Visual QA pending: AC-X,
AC-Y — needs a human eyeball on the running app"**, and the ticket sits at the In Review/Testing ceiling
(already the cap) with that note. The human does the final visual QA on the MR / running app.

**Guardrail:** `READY_FOR_VISUAL_QA` is impossible to reach with a real blocker. A failed logic AC, an
open CRITICAL, an unverified execution, or a TDD violation all keep it at `HALT_PRESHIP`. It is strictly
"everything a machine can prove is green; only the human-eye step remains."

## What this is NOT (kept honest)

- It does **not** lower the bar. Visual ACs are still not PASS; they are explicitly `visual_pending` and
  the MR says so. A human must still sign off.
- It does **not** let unverified *logic* ship. Only rendered-UI ACs with proven logic qualify.
- It does **not** auto-merge. It opens an MR (human-gated), at the existing transition ceiling.

## Deferred to follow-ups (not in 0.9.0)

1. **Local-stack fallback for true autonomous UI PASS** (the real fix for the gap): `klever-local-stack` +
   a seeded fixture + `ui-probe` against `localhost:3000` (auth works on :3000, no IAP). Lets rendered-UI
   ACs reach a genuine PASS without dev/Gab's Chrome. Bigger lift (stack orchestration + fixture seeding);
   spec it as its own ticket.
2. **Separate pre-existing typecheck noise from run signal** (both runs lost a fitness point to this): QA
   diffs the changed-file set against the tsc error set, emits `run_introduced` vs `pre_existing` counts,
   fails only on run-introduced.
3. **Auto-capture undemonstrated LOW/MEDIUM review findings as "deferred hardening"** in the ticket reports
   (KTP-759 `Number.isFinite` no-coercion; KTP-788 `origins[0].granularity` mislabel) so latent fragilities
   aren't silently dropped.
4. **Gate AC-vs-implementation mechanism drift before ship** (KTP-788 AC-3 shipped modeled-hue instead of
   the AC's dashed style): when the implementor deviates from a written AC mechanism, flag it as a
   PO-confirmation item (ADR-draft → inbox/Jira) before the ship loop.

## Implementation order (when built)

1. `CONCIERGE_SCHEMA` + concierge contract: per-AC `ac_kind`, `visual_feasibility`, up-front open_question.
2. `QA_SCHEMA.per_ac.visual_pending` + `6-qa.md`: QA sets it for proven-logic/visual-only ACs.
3. Spine readiness function: add `READY_FOR_VISUAL_QA`, the "all non-PASS are visual_pending" computation,
   and the main-loop next_steps for it. Keep `HALT_PRESHIP` for any real blocker.
4. `SKILL.md` "How to run it": handle the new terminal status (MR + Jira flag "visual QA pending").
5. Test: extend `tests/` with readiness-logic cases (real-blocker → HALT; all-visual-pending →
   READY_FOR_VISUAL_QA; mixed → HALT; all-pass → READY_TO_SHIP). Mutation-check as with the TDD gate.
6. Bump 0.9.0 + CHANGELOG.
