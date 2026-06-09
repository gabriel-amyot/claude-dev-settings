# Visual-AC Verification — spec (0.9.0)

**Origin:** deft-falcon session, from the 0.8.0 TDD-gate real-run feedback (KTP-728/758/759/788).
**Status:** BUILT in 0.9.0 (spine + contracts + tests). Local-stack fallback follow-ups still deferred.
**Revision note:** v2 of this spec. v1 deferred the local-stack path and leaned on a "visual proof is
structurally impossible autonomously" premise. That premise was wrong — it conflated *dev* verification
(IAP + nightly-off) with *all* verification. Corrected below: local-stack + browser is the **primary**
path; the human-eyeball state is the **fallback**.

## Problem (evidenced, recurring)

Four runs — KTP-728, KTP-758, KTP-759, KTP-788 — all terminated `HALT_PRESHIP` for the **same** root
cause, discovered late (at QA) every time: rendered-UI ACs capped at PARTIAL because the QA subagent
could not get live visual proof, *after* burning implement + review + QA.

The 0.8.0 TDD gate itself is **validated and working** in both post-gate runs (`trustworthy: true`,
same-test red→green defeated vacuous-RED, frontend `not_applicable` exemptions QA-verified on the diff).
This spec addresses the *different* gap the TDD runs surfaced.

## Why the runs got stuck (corrected diagnosis)

The runs concluded "ui-probe needs Gab's authenticated Chrome / dev is past nightly-off." True — **for
dev**. `portal.dev.beklever.com` has the IAP + Auth0 wall and the 20:00 EDT off-window. But:

- **Localhost has neither.** ui-probe targets `localhost` too, and the local stack on `:3000` uses the
  local auth mock (no IAP). The Playwright e2e suite already drives the local stack headlessly. So
  visual proof against a **running local stack** is a solved capability the factory simply wasn't using.
- **The real substrate constraint is *where* it runs.** `klever-local-stack` and `ui-probe` are *skills*,
  and skills are unreliable inside Workflow subagents (the factory's own ADR — it's why the **main loop**,
  not the workflow, does `/klever-mr` + `/post-comment`). So visual verification must run in the **main
  loop**, not the QA subagent.
- **The irreducible blocker is fixtures, not browsers.** KTP-788 needed a Canadian FSA store that does
  not exist even locally. No stack conjures unseeded data. Fixture availability is the thing worth gating
  on up front.

## Terminal states (the model)

| State | When | Who acts |
|---|---|---|
| `HALT_PRESHIP` | a *real* blocker (failed execution, open CRITICAL, TDD violation, a non-visual AC failed) | nobody ships |
| `NEEDS_VISUAL_VERIFY` *(new)* | machine-provable work all green; only rendered-UI ACs remain (`visual_pending`) | **main loop** runs the visual step |
| `READY_TO_SHIP` | all ACs PASS (incl. visual, after the main-loop step promotes them) | main loop → MR |
| `READY_FOR_VISUAL_QA` *(new, fallback)* | visual ACs can't be auto-verified (stack won't start / no fixture / no browser) | main loop → MR flagged "human eyeball needed" |

## Mechanism A — Concierge front gate (fixture + visual feasibility)

The concierge already classifies the belt and extracts ACs; the frontend belt already separates
rendered-UI ACs from extractable-pure-logic ACs (the TDD `not_applicable` rule). Extend the concierge to:

1. **Classify each AC** `visual` (rendered-UI: proof is a live screenshot) vs `logic` (unit-testable /
   `not_applicable`).
2. **Fixture-feasibility check** for each `visual` AC gated on a data condition (`country===CA`,
   `granularity===fsa`, a specific advertiser): does a seedable/local fixture exist to render it? This is
   the constraint a stack can't fix.
3. **If a `visual` AC's data condition has no seedable fixture → raise a `needs_human` open_question UP
   FRONT** (defer, or accept logic-only this run), instead of discovering at QA that the panel can't be
   rendered against real data. Browser access is *not* a front-gate blocker (the main loop handles it via
   the local stack); missing **data** is.

**Schema:** `CONCIERGE_SCHEMA` gains per-AC `ac_kind` (`visual` | `logic`) and, for `visual` ACs, a
`fixture` verdict (`available` | `seedable` | `missing`). A `missing` fixture on a visual AC drives the
up-front `needs_human` question.

## Mechanism B — Workflow marks, main loop verifies

**Workflow (subagents)** proves everything without a browser: logic TDD, build, review, wiring. QA marks
each rendered-UI AC `visual_pending: true` (logic + wiring proven via code_ref + any pure-logic RED green;
the only missing thing is the live screenshot). Spine readiness logic:

- compute real blockers (execution / pushed / open CRITICAL / TDD violation / any non-PASS AC that is NOT
  `visual_pending`). If any → `HALT_PRESHIP`.
- else if `ALL_PASS` → `READY_TO_SHIP`.
- else if every non-PASS AC is `visual_pending` → **`NEEDS_VISUAL_VERIFY`** (hand the visual step to the
  main loop). ShipPrep still runs (version bump + push) so the branch exists.

**Main loop (skills work here)**, on `NEEDS_VISUAL_VERIFY`:

1. Start the local stack: `/klever-local-stack` (or `klever-local-stack-real-bq` when the AC needs real
   data). Seed the fixture if the concierge marked it `seedable`.
2. Drive the browser against `localhost:3000` for each `visual` AC: **`ui-probe`** when Gab's Chrome is
   available (richer, reuses his session), else the headless Playwright path (`/klever-test` AC-validation
   — localhost has no IAP wall, so headless works). Capture a screenshot per AC.
3. Decide:
   - every visual AC renders correctly → promote to `READY_TO_SHIP`, open the MR with the screenshots as
     evidence. **True autonomous visual PASS.**
   - a visual AC renders wrong → report it as a real gap (back to a fix, or HALT).
   - stack won't start / fixture truly unavailable / no drivable browser → **`READY_FOR_VISUAL_QA`**: push
     + open the MR flagged "visual QA pending: AC-X — needs a human eyeball on the running app." The
     original fallback, now genuinely last-resort.

**Guardrail (unchanged from v1):** none of the new states can be reached with a real blocker. A failed
logic AC, open CRITICAL, unverified execution, or TDD violation all stay `HALT_PRESHIP`.

## What this is NOT (kept honest)

- It does not lower the bar: a visual AC is PASS only after an actual screenshot shows it rendering right
  (auto via the local stack, or human via `READY_FOR_VISUAL_QA`). It is never PASS on code-reading.
- It does not let unverified *logic* ship.
- It does not auto-merge: it opens an MR (human-gated) at the existing transition ceiling.
- It does not pretend a stack can fix missing data: a `missing` fixture is gated up front, not papered over.

## Deferred to follow-ups (not in 0.9.0)

1. **Separate pre-existing typecheck noise from run signal** (both runs lost a fitness point): QA diffs the
   changed-file set against the tsc error set, emits `run_introduced` vs `pre_existing`, fails only on
   run-introduced.
2. **Auto-capture undemonstrated LOW/MEDIUM review findings as "deferred hardening"** in ticket reports
   (KTP-759 `Number.isFinite` no-coercion; KTP-788 `origins[0].granularity` mislabel).
3. **Gate AC-vs-implementation mechanism drift before ship** (KTP-788 AC-3 modeled-hue vs dashed): flag a
   PO-confirmation item (ADR-draft → inbox/Jira) before the ship loop.
4. **Auto-seed library for common fixture conditions** (a reusable CA-FSA store, a multi-advertiser set) so
   `missing` fixtures become `seedable` over time.

## Implementation order (when built)

1. `CONCIERGE_SCHEMA` + `1-concierge.md`: per-AC `ac_kind`, `visual` `fixture` verdict, up-front
   `needs_human` on a `missing` fixture.
2. `QA_SCHEMA.per_ac.visual_pending` + `6-qa.md`: QA sets it for proven-logic/visual-only ACs.
3. Spine readiness function: add `NEEDS_VISUAL_VERIFY` + `READY_FOR_VISUAL_QA`, the "all non-PASS are
   visual_pending" computation, ShipPrep-still-runs, and the result payload the main loop needs
   (`visual_acs`, `fixture` info, branch).
4. `SKILL.md` "How to run it": the `NEEDS_VISUAL_VERIFY` main-loop step (start stack → ui-probe/Playwright
   on `:3000` → promote to READY_TO_SHIP with screenshots, or fall to READY_FOR_VISUAL_QA). Handle the new
   terminal states.
5. Tests in `tests/`: readiness-logic cases (real-blocker → HALT; all-visual-pending → NEEDS_VISUAL_VERIFY;
   mixed → HALT; all-pass → READY_TO_SHIP). Mutation-check as with the TDD gate.
6. Bump 0.9.0 + CHANGELOG.
