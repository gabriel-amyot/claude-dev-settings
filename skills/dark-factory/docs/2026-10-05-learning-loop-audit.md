# Is the auto-improve loop closing? — audit, 2026-10-05

**Question asked:** are the learning frameworks still working, and is there a backlog of learnings to apply?

**Answer: the loop half-closes.** It observes well and writes well. It does not land. The observation
half has been working for four months and produces genuinely sharp diagnoses. The landing half has no
mechanism at all, so a proposal's only route into the product is a human reading it and writing gate code.

Method: `tools/mine-telemetry.py` over all 54 `runs/*.yaml`, plus a count of the improvement handoffs on disk.

---

## The evidence

### Terminal states, 54 runs (2026-06-02 → 2026-10-02)

| n | state |
|---|---|
| 19 | `HALT_PRESHIP` |
| 9 | `READY_TO_SHIP` |
| 9 | `HALT_AGENT_SKIPPED` |
| 6 | `BLOCKED_SPEC_QUALITY` |
| 4 | `HALT_TDD_GATE` |
| 4 | `NEEDS_VISUAL_VERIFY` |
| 2 | `BLOCKED_NEEDS_HUMAN_AGAIN` |
| 1 | `HALT_FIX_NOT_PUSHED` |

**17% of runs reach `READY_TO_SHIP`.** `HALT_PRESHIP` alone is 35%.

### Scores by month

| month | n | task_confidence | factory_fitness |
|---|---|---|---|
| 2026-06 | 29 | 53.8 | 72.8 |
| 2026-07 | 5 | 59.0 | 81.4 |
| 2026-08 | 9 | 46.2 | 69.8 |
| 2026-09 | 4 | 71.5 | 76.8 |
| 2026-10 | 5 | **42.0** | **59.2** |

October is the worst month on both axes. Note the confound: four of October's five runs are the same
ticket (KTP-1272) retried, so this is partly one hard ticket, not a clean trend. It is still the lowest
fitness ever recorded.

### Self-declared repeats — the system reporting its own failure

**13 of 54 retros explicitly state their finding is a repeat of an earlier one.** Not inferred by
keyword matching; written in the retro's own words:

- `2026-08-19` — "a verbatim repeat of an improvement filed by the KTP-1129 retro. Two runs, two retros, two disk searches."
- `2026-07-07` — "the SAME improvement proposed in the 2026-06-11 KTP-739 retro and never landed; the identical failure recurred."
- `2026-06-16` — "already proposed promoting this to a workflow.js gate and it did not stick."
- `2026-06-16` — "Still not applied across three retros."
- `2026-06-08` — "track the recurring root cause as a meta-item, so the improvement actually lands instead of being perpetually re-proposed."

That last one is the loop asking, in June, for the thing this audit is doing in October.

### Recurring themes (improvement titles only, 54 runs)

| runs | theme | span | status |
|---|---|---|---|
| 32 (62%) | qa-blind-spot | 06-02 → 10-02 | open |
| 24 (46%) | artifact-on-disk | 06-02 → 09-30 | open |
| 14 (27%) | branch-state-truth | 06-04 → 10-02 | open |
| 13 (25%) | visual-proof | 06-03 → 10-02 | open |
| 13 (25%) | tdd-ledger | 06-11 → 10-01 | open |
| 13 (25%) | scope-slicing | 06-02 → 10-01 | open |
| 10 (19%) | agent-null-dispatch | 06-09 → **08-04** | **absorbed** |
| 9 (17%) | review-severity-gate | 06-22 → 10-02 | **fixed in 0.10.1** |
| 8 (15%) | spec-gate-upstream | 06-02 → **08-19** | **absorbed** |
| 7 (13%) | confidence-is-inert | 06-02 → 10-02 | open |

Treat the percentages as indicative, not precise — they come from keyword matching over
improvement titles. The ordering and the open/absorbed split are the reliable part.

**The two absorbed themes are the proof of the mechanism.** `agent-null-dispatch` and
`spec-gate-upstream` both stop dead. Both were fixed in 0.9.3 by adding a **schema-required field or a
JS gate**. Every theme still open was addressed only in **prose** — a contract paragraph telling an
agent to behave better.

This is not a new discovery. The 0.9.3 CHANGELOG already says it: *"the pattern that sticks =
schema-required fields + JS gates."* The factory diagnosed its own cure thirteen months of runs ago and
then kept writing prose.

---

## Why it does not close

The Retro writes two artifacts. One is telemetry (`runs/*.yaml`) — written, and until today partly
unreadable. The other is a next-run improvement handoff.

**There are 26 `dark-factory-improvements-*.md` handoffs on disk**, scattered across
`sessions/active/*/prompts/`, `sessions/archive/`, and a stray `sessions/active/prompts/`. The session
ledger reports 66 pending handoffs overall. Nothing reads them on the way into a run.

So the loop is: run → diagnose → write a file → nobody reads the file → same failure next run →
diagnose again. The diagnosis quality is high and rising. The landing rate is near zero.

**Two silent data losses made it worse:**

1. Two of 54 run files did not parse (literal ESC bytes; an unquoted `: ` in a commit subject). Every
   prior analysis silently ran on 52 of 54 and said nothing. Fixed, plus a parse-check now required in
   contract 9.
2. Eight run files were sitting untracked in git. One `git clean` would have deleted them. Committed.

---

## What changed today

- **0.10.1** fixed the top open theme (`review-severity-gate`) the way the absorbed ones were fixed: a
  derived JS predicate + a tightened contract, not prose. 27 test cases, 8 mutations, all detected.
- Telemetry repaired and the write path guarded.
- `tools/mine-telemetry.py` added, so this question can be asked again for the cost of one command.

## What is still open

Ranked by recurrence × how mechanical the fix is.

| # | Theme | Fix shape | Size |
|---|---|---|---|
| 1 | **confidence-is-inert** (7 runs) | The soft `confidence` has never gated anything — SKILL.md admits it. Every run self-reports it and nothing reads it. Either feed a sub-75 phase's stated uncertainty into the next phase's prompt, or drop the field. Collecting a number nobody consumes is theatre. | S |
| 2 | **visual-proof** (13 runs) | The concierge already classifies `ac_kind`. The workflow does not read it to equip the QA socket, so an all-visual ticket reaches contract 6 before anyone notices nothing can prove it. Gate at the front instead. | M |
| 3 | **qa-blind-spot** (32 runs) | Biggest by count but broad — several distinct asks share the vocabulary. Needs decomposition before it is actionable; the count alone overstates it. | L |
| 4 | **improvement landing** | The meta-fix: a retro improvement should land in a tracked queue the next run reads, not a file in a session folder. This is the one that makes every other row self-closing. | M |

**Recommendation: #4, then #1.** #4 is the only one that changes the loop's shape rather than
patching one more hole in it, and the loop asked for it itself in June.

## Caveat

Everything above is read off telemetry the factory wrote about itself. A retro agent scoring its own
run is not an independent measurement, and the `factory_fitness` numbers in particular are self-graded.
The terminal-state distribution and the self-declared-repeat count are the hard numbers here; the
scores are soft signal.
