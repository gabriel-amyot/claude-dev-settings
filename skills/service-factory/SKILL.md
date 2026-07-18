---
name: service-factory
version: "0.1.0"
description: "The Fix Factory — the fast, human-in-the-loop quick-bug-fix line for a SINGLE Klever bug, sibling to dark-factory (the Build Factory). A main-loop skill orchestrates; the un-skippable gates are Python scripts (stamp-check, express predicate, exit-verify, loop counter, Gate-0 completeness, layer coverage, closure matrix, board mutation) proven by an eval suite. One variable is optimized: time to resolution. Reproduce-first, falsify hypotheses on evidence, the WALL is the one guaranteed human touch, exit is same-repro red→green per env per cause. Triggers on: '/service-factory', 'service factory', 'fix factory', 'quick bug fix', 'service area', 'investigate this bug'. Klever."
user_invocable: true
nav:
  bay: fix
  when: "Run a single Klever bug from report to fix through a fast, gated line: reproduce-first, evidence-falsified hypothesis board, human WALL, same-repro exit + Jira comment. Time-to-resolution is the metric."
  when_not: "Building a feature/new interface (use dark-factory). Multi-ticket sets (use sprint-factory). Overnight per-AC autonomous (use sprint-crawl). A spike/research task with no reproducible symptom. project-management repo (never)."
  personas: [quinn, amelia, winston]
  org: [klever]
---

# Service Factory — the Service Area bug-fix line (B-prime)

**dark-factory builds the car; the Service Area fixes it.** A unified falsification
engine. One variable is optimized: **time to resolution.** The agent flies; the human
is pilot-monitoring. Built on the real harness: this skill (the main loop) orchestrates,
human gates are **turn boundaries**, parallel work is **gate-free background bursts**
writing to disk, all state persists to the ticket folder.

**Full spec (source of truth):** `project-management/reports/session-retros/2026-07-16-ktp939-fault-audit/`
— `08-service-factory-v3.md` **as amended by** `14-v4-decisions-changeset.md` (D1–D10).
Acceptance harness: `10-service-factory-evals.md`. Defends against `03-fault-report.md`
(34 faults) + `09-bug-session-catalog.md` (25 modes) + `11-redteam-inferred-failure-modes.md`
(IFM-1..16). Build status: `docs/build-notes.md` (v1 shipped; stage 2/3 pending).

## Division of labor

The **main loop** (this conversational context) orchestrates: it holds the gates, runs
the gate scripts, dispatches probes, writes the artifacts, and stops at each turn
boundary. It does the external actions a background agent can't safely do: `/post-comment`
(bounce / plan / close), `/klever-mr`, Jira transitions. **Background bursts** (Agent /
Workflow) do gate-free probe work and write results to files; the main loop merges them.

## Substrate law (§1 — non-negotiable)

1. **This skill is the orchestrator.** It alone holds gates.
2. **Every [H] gate = a turn boundary.** Light gates → `AskUserQuestion` (PARK is always
   an option; timeout → park, never a silent default). The WALL + bundled EXIT → **crit**
   on `rca.md` / the gate report, with an auto-regenerated mermaid board-state block.
3. **Every parallel box = a gate-free Agent/Workflow burst** that runs to completion and
   writes to disk. No human gate inside a burst. The orchestrator merges results.
4. **Hunch = a user message at a turn boundary.** Append an undroppable board card
   (`origin: hunch`); it jumps the cheapest-first queue, dispatched next cycle. It dies
   only by a REFUTE whose scope covers it (`board_ops.hunch_guard`).
5. **State lives on disk** under the service-area folder (below). `state.yaml` is rewritten
   at every phase boundary and ledger mutation. Session death → `/session:pickup` re-presents
   the recorded gate from disk.
6. **BOUNCE / PARK** = `/session:handoff` + inbox entry + parked `state.yaml`.
7. **Every output — human-facing AND inter-agent — is `/caveman` register** (D3). Rich
   content goes to files, never chat walls. The gate report (`templates/gate-report.md`) is
   the ONLY relay format at gates.

**Ceremony warning (IFM-14):** this line exists to be FAST. The express path is 2 blocking
human stops, ≤15–30 min. Do not let the artifact contract become the disease it was built
against. Express uses the ≤10-line RCA card, not the full document.

## Where state lives

```
tickets/{PREFIX}/{EPIC|no-epic}/{ID}/service-area/
  state.yaml            # phase + gate-state + loops + clock; rewritten every boundary
  intake.yaml  jira-raw.json  env-fact-sheet.md
  board.yaml           # hypothesis cards (schema: docs/schemas.md / §4)
  observations.yaml    # attested observations
  rca.md               # from templates/rca.md
  closure-matrix.yaml  closing-draft.md
  knowledge-facts.yaml # Phase 9 harvest: facts + playbook +1/proposal + retro (D4, gated)
  parking-lot.md       # passive all session, drained ONLY at Phase 9
  evidence/            # drop zone for agent AND human, images/video (D7)
  gate-reports/        # one S14 report per gate touch + probe outputs
```

## The gates (un-skippable Python; run them, honour the exit code)

All under `gates/`. Exit 0 = pass/allow, non-zero = reject/withhold. They are the eval
targets (`evals/run_evals.py`, registered `service-factory/gates`). **Never hand-wave past
a gate — run it.**

| Gate | Script | Enforces |
|---|---|---|
| Gate 0 completeness | `gate0_completeness.py <sa-dir>` | intake is files not attestation; [INFERRED] observable withholds auto-pass (SFE-06/47) |
| Express predicate | `express_predicate.py <in.yaml>` | env universe from the fact sheet; decline if any reported env unanchored (SFE-40) |
| Stamp check (WALL pre-gate) | `stamp_check.py <sa-dir>` | every cause cites an OBSERVED row of a fitting method (SFE-01/41) |
| Layer coverage (Phase 3 exit) | `coverage_line.py <sa-dir>` | every in-scope layer carded or explicit N/A (SFE-50) |
| Loop counter (governor) | `loop_counter.py <state> <delta>` | cap resets only on a MATERIAL obs (SFE-46) |
| Exit verify | `exit_verify.py <in.yaml>` | condition parity + conservative N for flaky (SFE-43) |
| Closure matrix (EXIT) | `closure_matrix.py <sa-dir>` | `tracked` needs a real key; no phantom tickets (SFE-51/16) |
| Learning harvest (Phase 9) | `learning_harvest.py <sa-dir>` | knowledge-facts (D4 schema) + playbook +1/proposal materialised + retro scored + lot drained — harvest narrated ≠ harvest done (SFE-56) |
| Board mutation | `board_ops.py` (import) | scope-split, hunch-guard, cross-domain cap, dedupe, revive-bound (SFE-02/03/07/44/54/55) |

## The flow (phase-by-phase — see §2–3 of the spec for the mermaid + full detail)

**Phase 0 — Lifecycle [A].** `/session:init` + inbox/pickup read. Scaffold the service-area
folder + STATUS_SNAPSHOT.yaml + ac.yaml **before** intake. Stamp the start clock in
state.yaml. On resume: read state.yaml, re-enter the recorded phase. **Staleness recheck
(IFM-10):** if `now − last_observation` > 4h (flip) OR the resume crosses the nightly 20:00
EDT boundary, the FIRST act is to re-validate every load-bearing anchor and CONFIRMED cause
before any falsification or fix — a restored host silently invalidates a CONFIRMED anchor.

**Phase 1 — Concierge intake [A; H only on gaps] (D2).** `/jira` fetch description + ALL
comments; persist raw as `jira-raw.json` (the file is the read record, not a self-claim).
Build `env-fact-sheet.md` from a **mandatory bibliothèque INDEX lookup** (shared-backend /
shared-data notes) — cite the doc(s) or write `Library: silent (checked INDEX/ALIASES for
<topic>)`. This is load-bearing (F19) and hook-backed (`bibliotheque-recall.sh`,
`library-stamp-guard.sh`); **do not exempt your own dispatches** — carry the `Library:`
stamp. Each observable is `[REPORTED …]` verbatim or `[OBSERVED O-id]`; an inferred guess
is not a confirmed observable. Ticketless entry: draft a lightweight bug ticket; its
one-tap creation rides the first human touch. **Run `gate0_completeness.py`** — auto-pass
only when it exits 0; otherwise route proceed-on-candidates (draft the reporter question
via `/post-comment` AND start repro on all candidates) or bounce.

**Phase 2 — Reproduce [A; Gate 1 auto-pass on attested anchor].** Open the failing app in
EACH env on the fact sheet (`ui-probe`). **Logs/console FIRST** — find WHEN it started.
Two-part anchor per env: reported symptom on the reported surface (screenshot) + tech
signature (logs/network/first-error time). Loop until each env has an anchor OR an explicit
`parked-with-comment`. **Intermittent:** N attempts (default 10) under reporter amplifiers;
record k/N; `n=1` is INCONCLUSIVE (`board_ops.intermittent_verdict`). Override (rare)
requires the human to name a proxy exit vector.

**Phase 2b — Express lane [A, 1 try].** Build `express-input.yaml` (env_universe from the
fact sheet, anchored_envs, component_named, recent_change_in_hand, single_cause_all_envs)
and **run `express_predicate.py`**. Fires only if it exits 0. One card, one falsify-test,
anchor doubles as evidence → CONFIRMED → stamp check → WALL with the express RCA card.
Declined → SURFACE, reason recorded in the next gate report.

**Phase 3 — Surface map + seed [A].** All layers in scope (ui/backend/data/db/infra),
narrow by elimination keyed on the reproduced **signature per env**, never the reported
symptom. Playbooks (`playbooks/*.md`) seed cards — data, not gates; recency-weighted; **no
single playbook >50% of cards**, and the assumption audit seeds **≥1 card per in-scope
layer** (a load-bearing premise = a card with a falsify-test). **Run `coverage_line.py`** —
the phase can't exit with an uncarded, non-N/A layer.

**Phase 4 — Falsification [A probes; H only where routed].** Probes cheapest-and-most-
likely first, each fresh-context. Every probe mission carries a `Library:` line (cited docs
or `library silent`). Probes report a narrative, never full context. Attest each verdict →
`observations.yaml` (input {claim, falsify-test, evidence, method}, output {verdict,
strength, verified_against, source}). Board mutations go through `board_ops`: scope-covered
REFUTE only, else auto-split; cross-domain refute capped weak (never drops the card);
duplicate-source evidence never upgrades strength; REVIVE bounded, mutual oscillation
escalates. Contradiction diff on every append against ALL cards incl. REFUTED. COUNT is a
non-blocking heartbeat: zero survivors → requeue weak-falsified FIRST, then brainstorm
scouts. **Governor:** every re-entry runs `loop_counter.py`; a material obs (flips a card /
seeds a new card) resets, a throwaway does not; at cap, or 45 min without a CONFIRMED cause,
fire the caveman pulse (4 options; 5th if a decisive burst is in flight).

**Phase 5 — The WALL [H, via crit — even for a 2-line fix].** **Run `stamp_check.py` first**
(reject → back to the board). Present `rca.md` (from `templates/rca.md`) + auto board mermaid
via crit. The WALL asks: compelling narrative, non-far-fetched how-introduced, and does one
cause explain the anchor in EVERY reported env (env-coverage checklist). Soft on causation —
the no-cause package lives under Open Questions, stamped `[INFERRED]`, never a Verdict.
Options: approve / reject / fix-anyway-mitigate / dig-with-new-budget / park. **On approve,
the "diagnosis approved, fix plan is X" Jira comment is drafted and surfaced AT the gate for
one-click approval BEFORE any code change** (F22).

**Phase 6 — Per-cause route [H decision at WALL, A execution].** Each confirmed cause gets
its own tag + closure criterion: **quick-fix** (default) → green re-repro; **Leo-gated
ticket** (complex/new-feature → SEPARATE dark-factory session, never inline) → ticket +
comment; **owner** (data/infra no access) → owner Jira comment + tracked follow-up. Multiple
dispositions simultaneously is legal and expected (KTP-939 shape).

**Phase 7 — Fix + exit verify.** Quick fix in a worktree (`superpowers:using-git-worktrees`);
minimal diff; prefer logs + red test over speculative code. Exit via `/verify`: rerun the
SAME repro (or proxy vector) red→green **per env per cause**. Flaky: build `exit-input.yaml`
(pre + post k/n/conditions) and **run `exit_verify.py`** — matching conditions + conservative
N required; local if possible, else MR to dev and verify there.

**Phase 8 — Bundled EXIT [H, ONE turn via crit].** **Run `closure_matrix.py`.** The matrix:
every reported env/symptom → green re-repro OR tracked handoff (with a real key). Present
matrix + rendered closing-comment draft + MR link; one reply approves all three. Gap → governor.

**Phase 9 — Close + post-mortem [A].** MR via `/klever-mr`; ONE consolidated Jira comment
covering all dispositions via `/post-comment`. **Learning loop (D4) — gated, not narrated.**
Produce `knowledge-facts.yaml` in the service-area dir, then **run `learning_harvest.py`**;
the close is refused until it exits 0. Its shape (one file, lean — express runs fill the
same ~15 lines):
- `facts:` — each `{fact, provenance: verbatim|inferred, raw_source, rca_link}`. A run with
  a CONFIRMED cause must emit ≥1 fact (`raw_source` resolves to a run-dir file or
  `observations.yaml#Oxx`). This is the bibliothèque-compatible payload.
- `playbook:` — used one → `plus_one: <id>` (a REAL `playbooks/<id>.md`) AND materialise
  the appended source-incident lines as `playbook-append.md` (live runs also append them to
  the real playbook file; the artifact proves the content exists — "+1" said in chat counts
  for nothing). Invented a new signature→checks path → `proposal: <id>` +
  `playbook-proposal-<id>.md`. No confirmed cause → `none_reason`.
- `retro:` — dark-factory pattern, minimal: `task_confidence` + `factory_fitness` (0-100),
  `red_flags[]`, `improvements[{title,detail}]`; a fitness < 100 must be accounted for
  (deductions/red_flags/improvements). Improvements feed the next run.
- Drain `parking-lot.md`: every entry gets a `| drained: proposal|ticket|dropped|noted`
  disposition (ticket proposals Leo-gated if promoted).
Final STATUS_SNAPSHOT/ac.yaml update. Auto-collapses toward a no-op when there is genuinely
nothing to harvest — but the gate, not the agent, decides that.

## Effort governor (§6, numbers flippable)

- CLOCK + SPEND + LOOPS on every gate report.
- 45-min checkpoint pulse without a CONFIRMED cause → caveman pulse, 4 options.
- Loop cap ≤3 board re-entries without a MATERIAL confirmed observation (`loop_counter.py`).
- Express: 1 attempt; acceptance target 2 blocking stops, ≤15–30 min.

## Compatible-from-day-1 (produce payloads; the systems are separate handoffs)

- Knowledge-facts with provenance + playbook proposals → the bibliothèque provenance handoff.
- The Phase 2 repro (red) + Phase 7 exit verify (green) are the **extractable QC-Gate seed
  (D8)** — keep them a shared shape, not a private step, for the future QC Gate / dark-factory.

## REPLAY MODE (paper-replay evals — Tier 2/2b)

The orchestrator runs offline against a **scripted world** so its behaviour can be
graded without live infra. A run is in replay mode when it is given a `world.yaml`
and a run dir. The contract:

1. **The world is the only external truth.** Every external observation — `/jira`
   fetch, `ui-probe`, log/console reads, probe/scout dispatches, `/verify`,
   `/klever-mr`, `/post-comment` — is satisfied from `world.yaml`, never a live tool.
   `world.yaml` maps `missions:` (a mission/probe key or a tool+target) → a canned
   result, plus `jira:`, `memory:`, `prior_session:` blocks. A mission with no entry
   returns `NOT_IN_WORLD` (treat as "probe returned nothing" — do not invent a result;
   that is the confabulation trap, IFM/SFE-15).
2. **Artifacts are real.** Write the full service-area folder (state.yaml, intake.yaml,
   env-fact-sheet.md, board.yaml, observations.yaml, rca.md, closure-matrix.yaml,
   closing-draft.md, gate-reports/, parking-lot.md) into the given run dir. Run the
   real gate scripts against them.
3. **Emit `transcript.jsonl`** — one JSON object per action, in order:
   `{"seq": N, "phase": "...", "action": "repro|probe|rca|dispatch|gate|fix|...",
     "tool": "...", "target": "...", "produces": "...", "note": "..."}`.
   This is what ordering graders read (e.g. "first investigative action is repro,
   before any rca").
4. **Human gates auto-resolve from the world.** `world.yaml` `human:` gives canned
   gate answers (e.g. `wall: approve`). If absent, record the gate report and stop
   (a real WALL would block); the grader inspects the recorded gate.
5. **No live side effects, ever.** Replay writes files only. `/klever-mr`,
   `/post-comment`, Jira transitions are simulated as artifacts (`closing-draft.md`,
   a `gate-reports/mr.md`), never executed.

Nothing in replay mode is told the expected diagnosis — it observes the world and
runs the line. If SKILL.md induces the right behaviour it passes the graders; if not,
it fails. That is the test.

## Acceptance harness

`evals/run_evals.py` (registered `service-factory/gates`, run via `/skill-evals`). Ship bar:
Tier 1 script SFEs green, Tier 2b criticals (SFE-40/41/43/44) green. Paper replays (Tier 2/2b)
+ live drills (Tier 3) are Layer B / deferred to stage 2/3 (`docs/build-notes.md`). A stage
isn't done until its evals pass; every future bug RCA adds or amends at least one eval.
