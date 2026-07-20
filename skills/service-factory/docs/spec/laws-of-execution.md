# Service Factory — Laws of Execution

```
spec_version: 0.1.0
status: cemented baseline
scope: the non-negotiable substrate + gate + governor rules the orchestrator obeys every run
```

These are the binding execution laws of the Service Factory. SKILL.md is the operating
manual; this file is the law it must not violate. When SKILL.md prose and these laws
disagree, the laws win, and the mismatch is a bug to fix in SKILL.md. Every law here is
carried in the skill and versioned with it (see `../../CHANGELOG.md`).

## Law 1 — Substrate (§1, non-negotiable)

1. **This skill is the orchestrator.** It alone holds gates.
2. **Every [H] gate = a turn boundary.** Light gates → `AskUserQuestion` (PARK is always
   an option; timeout → park, never a silent default). The WALL + bundled EXIT → **crit**
   on `rca.md` / the gate report, with an auto-regenerated mermaid board-state block.
3. **Every parallel box = a gate-free Agent/Workflow burst** that runs to completion and
   writes to disk. No human gate inside a burst. The orchestrator merges results.
4. **Hunch = a user message at a turn boundary.** Append an undroppable board card
   (`origin: hunch`); it jumps the cheapest-first queue, dispatched next cycle. It dies
   only by a REFUTE whose scope covers it (`board_ops.hunch_guard`).
5. **State lives on disk** under the service-area folder. `state.yaml` is rewritten at
   every phase boundary and ledger mutation. Session death → `/session:pickup` re-presents
   the recorded gate from disk.
6. **BOUNCE / PARK** = `/session:handoff` + inbox entry + parked `state.yaml`.
7. **Every output — human-facing AND inter-agent — is `/caveman` register** (D3). Rich
   content goes to files, never chat walls. The gate report (`templates/gate-report.md`) is
   the ONLY relay format at gates.

**Ceremony warning (IFM-14):** this line exists to be FAST. The express path is 2 blocking
human stops, ≤15–30 min. The artifact contract must never become the disease it was built
against. Express uses the ≤10-line RCA card, not the full document.

## Law 2 — Gates are un-skippable Python, honoured by exit code

All gate logic lives under `../../gates/`. Exit 0 = pass/allow, non-zero = reject/withhold.
Every gate is also an eval target in `../../evals/run_evals.py` (registered
`service-factory/gates`). **Never hand-wave past a gate — run it. Narrated ≠ done.**

| Gate | Script | Enforces |
|---|---|---|
| Gate 0 completeness | `gate0_completeness.py <sa-dir>` | intake is files not attestation; [INFERRED] observable withholds auto-pass (SFE-06/47) |
| Express predicate | `express_predicate.py <in.yaml>` | env universe from the fact sheet; decline if any reported env unanchored (SFE-40) |
| Stamp check (WALL pre-gate) | `stamp_check.py <sa-dir>` | every cause cites an OBSERVED row of a fitting method (SFE-01/41) |
| Layer coverage (Phase 3 exit) | `coverage_line.py <sa-dir>` | every in-scope layer carded or explicit N/A (SFE-50) |
| Loop counter (governor) | `loop_counter.py <state> <delta>` | cap resets only on a MATERIAL obs (SFE-46) |
| Exit verify | `exit_verify.py <in.yaml>` | condition parity + conservative N for flaky (SFE-43) |
| Closure matrix (EXIT) | `closure_matrix.py <sa-dir>` | `tracked` needs a real key; no phantom tickets (SFE-51/16) |
| Learning harvest (Phase 9) | `learning_harvest.py <sa-dir>` | knowledge-facts (D4 schema) + playbook +1/proposal materialised + retro scored + lot drained (SFE-56) |
| Board mutation | `board_ops.py` (import) | scope-split, hunch-guard, cross-domain cap, dedupe, revive-bound (SFE-02/03/07/44/54/55) |
| Version guard | `version_guard.py <skill-dir>` | SKILL.md version ↔ CHANGELOG top match; spec carried in `docs/spec/`; zero external spec references (drift guard, SFE-60) |

## Law 3 — Phase order is fixed

The line runs Phase 0 → 9 in order. Phase 2b (express) is the only skip: it either fires
(and jumps to the WALL) or declines to Phase 3. Full per-phase detail is in
`service-factory-spec-0.1.0.md`; the binding order is:

- **P0 Lifecycle [A]** — `/session:init`, scaffold the service-area folder, stamp the clock.
  On resume: staleness recheck (IFM-10) before any falsification if >4h flip or a nightly
  20:00 EDT boundary was crossed.
- **P1 Concierge intake [A; H only on gaps]** — `/jira` fetch persisted to `jira-raw.json`;
  `env-fact-sheet.md` from a mandatory bibliothèque INDEX lookup (F19, carry the `Library:`
  stamp); each observable `[REPORTED]` verbatim or `[OBSERVED O-id]`; run `gate0_completeness.py`.
- **P2 Reproduce [A]** — logs/console FIRST; two-part anchor per env; intermittent = k/N,
  n=1 is INCONCLUSIVE.
- **P2b Express lane [A, 1 try]** — run `express_predicate.py`; fires only on exit 0.
- **P3 Surface map + seed [A]** — narrow by elimination on the reproduced signature per env;
  playbooks seed cards (data, not gates; no single playbook >50%); ≥1 card per in-scope
  layer; run `coverage_line.py`.
- **P4 Falsification [A probes; H only where routed]** — cheapest-and-most-likely first,
  fresh-context, each probe carries a `Library:` line; verdicts attested to
  `observations.yaml`; mutations through `board_ops`; governor runs `loop_counter.py`.
- **P5 The WALL [H, via crit]** — run `stamp_check.py` first; present `rca.md` + board
  mermaid; approve drafts the fix-plan Jira comment BEFORE any code change (F22).
- **P6 Per-cause route [H decision, A execution]** — quick-fix / Leo-gated ticket (separate
  dark-factory session) / owner handoff; multiple dispositions is legal.
- **P7 Fix + exit verify** — worktree, minimal diff; `/verify` reruns the SAME repro
  red→green per env per cause; flaky → `exit_verify.py`.
- **P8 Bundled EXIT [H, ONE turn via crit]** — run `closure_matrix.py`; matrix + closing
  draft + MR link, one reply approves all three.
- **P9 Close + post-mortem [A]** — MR + ONE consolidated Jira comment; produce
  `knowledge-facts.yaml` and run `learning_harvest.py` (close refused until exit 0); append
  one run line to `../../runs/INDEX.md` (the cross-run telemetry ledger).

## Law 4 — Effort governor (§6, numbers flippable)

- CLOCK + SPEND + LOOPS on every gate report.
- 45-min checkpoint pulse without a CONFIRMED cause → caveman pulse, 4 options.
- Loop cap ≤3 board re-entries without a MATERIAL confirmed observation (`loop_counter.py`).
- Express: 1 attempt; acceptance target 2 blocking stops, ≤15–30 min.

## Law 5 — Learning and version are coupled (self-improvement law)

The self-improvement loop is not advisory:

1. **Every run harvests** (Phase 9): `learning_harvest.py` refuses the close until the
   run's knowledge-facts, playbook +1/proposal, retro score, and drained parking lot are
   material on disk. `retro.improvements` feed the next run.
2. **Every run is logged** to `../../runs/INDEX.md` — one line: ticket, date, terminal
   status, `task_confidence`, `factory_fitness`. This is the durable cross-run telemetry
   that motivates changes to the line.
3. **Every change to the line bumps the version.** Any edit to SKILL.md, a gate script, a
   playbook contract, or a `docs/spec/` document bumps `version:` in SKILL.md frontmatter
   AND adds a `../../CHANGELOG.md` entry citing the run(s)/findings that drove it.
   `version_guard.py` enforces the version↔CHANGELOG match mechanically (SFE-60) — the link
   between an improvement and the version it landed in cannot be skipped or narrated.
