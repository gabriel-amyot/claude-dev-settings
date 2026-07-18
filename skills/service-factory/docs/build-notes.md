# Service Factory — build notes

Origin: handoff `2026-07-17-build-service-factory-skill.md` (session stern-owl).
Spec: `08-service-factory-v3.md` as amended by `14-v4-decisions-changeset.md` (D1–D10).
Acceptance harness: `10-service-factory-evals.md`. Red-team: `11-redteam-inferred-failure-modes.md`.

## Status — v1 spine (2026-07-17)

**Shipped and eval-green:**
- The eight un-skippable **gate scripts** (`gates/`), pure functions + CLI, each an eval
  target. `lib.py` self-tests pass (Clopper-Pearson p_lower(3/10)=0.0873 → required N=33,
  matching the spec's IFM-4 worked example).
- The **Layer A eval suite** (`evals/run_evals.py`, fixtures + generator) — registered in
  `~/.claude-shared-config/evals/manifest.yaml` as `service-factory/gates`, green via
  `/skill-evals`. **Score this session: T1 5/5 · T2b 10/10 · T2 (paper) deferred · T3 (live)
  deferred.**
  - Covered script-mode: SFE-01, 02, 03, 06, 07 (T1) · SFE-40, 41, 43, 44, 46, 47, 50, 51,
    54, 55 (T2b). Each asserts BOTH the hardened outcome AND the old/v3-compliant fault it
    must catch (design rule 1: discriminative or broken).
  - **Tier 2b criticals SFE-40/41/43/44 all green** — the ship bar for the highest-impact
    inferred modes (express single-env evasion, stamp laundering, exit-parity hole,
    cross-domain refute).
- **SKILL.md** orchestrator spine: substrate law, all 10 phases wired to the gate scripts,
  caveman-all-outputs (D3), library-first load-bearing steps (F19) with the hook backstops,
  resume-after-death staleness recheck (IFM-10), governor numbers (§6), division of labor.
- **Templates:** `rca.md` (from `13-rca-template.md`, 7 headings + express ≤10-line card),
  `gate-report.md` (S14). **Playbooks:** `config-drift`, `data-gap`, `fe-state` (the three
  KTP-939 already paid for). **Schemas:** `docs/schemas.md` (§4 artifact contract).

## Tier 2 paper replays — CRITICALS SHIPPED + green (2026-07-17)

The paper-replay harness is built and the five Tier 2 criticals pass.

- **REPLAY MODE** contract added to SKILL.md: the orchestrator runs offline against a
  scripted `world.yaml` (the only external truth), writes real artifacts, and emits
  `transcript.jsonl` (ordered actions). No live tools, no side effects.
- **World fixtures** (`evals/replays/<fixture>/`, generator `make_replay_fixtures.py`):
  `sfe10_repro`, `sfe13_attribution`, `sfe15_confab`, `sfe16_multicause`, `sfe21_alias`.
  Each is a trap the historical old-behaviour fails and the hardened line passes.
- **Deterministic graders** (`evals/graders/replay_graders.py`) + runner
  (`evals/run_replays.py`, reports PASS/FAIL/NOT-RUN, never fakes). `evals.json` holds the
  LLM-judge narrative clauses. Registered Layer B as `service-factory/paper-replays`.
- **Ran for real** via fresh-context sonnet replay agents. **Score: Tier 2 criticals 5/5
  green, 0 critical fails.** Notable: the F19 `library-stamp-guard` hook fired on two
  replay dispatches (blocked investigation prompts with no `Library:` stamp) — the harness
  dogfooded its own discipline; re-dispatched with the stamp. Two grader false-positives
  were found and fixed (intake reads mis-counted as "investigative"; the confab grep
  colliding with the legit repo name `dataform-repo` vs the invented `DAG` mechanism) — the
  orchestrator behaved correctly in both, the graders were sharpened to the true invariant.

**Still deferred (same fixture->replay->grade template):** the remaining Tier 2 replays
SFE-11, 12, 14, 17, 18, 19, 20, 22-25 and the Tier 2b replays SFE-42, 45, 48, 49, 52, 53.
Fixture roots + pass clauses fully specified in `10-service-factory-evals.md`.

## Phase 9 self-learning — GATED (2026-07-18, pre-first-real-run)

Audit before first real use found the D4 learning loop was prose-only: replay agents
NARRATED "playbook +1, knowledge-facts emitted" while mutating nothing (the "DONE = said
it" fault). Fixed by making the harvest un-skippable, dark-factory-Retro-inspired:
- **`gates/learning_harvest.py`** — Phase 9 close refused until `knowledge-facts.yaml`
  exists and is material: facts with D4 provenance + resolving raw_source (bibliothèque-
  compatible payload); playbook `plus_one` resolving to a REAL playbook id + the append
  content materialised as `playbook-append.md` (no phantom ids, no narrated +1);
  `proposal` needs its proposal file; retro block (task_confidence / factory_fitness /
  red_flags / improvements, low fitness must be accounted); parking-lot entries all carry
  `| drained:` dispositions. Materiality rule: a CONFIRMED cause forces >=1 fact and a
  playbook +1/proposal; none_reason is legal only for no-cause/parked runs.
- **SFE-56** (suite extension per design rule 5) — 4 fixtures: hardened PASS, no-cause
  PASS, narrated-only FAIL, well-formed-theater FAIL (must be caught on all four fronts:
  empty facts, phantom playbook id, unaccounted low fitness, undrained lot). T1 now 6/6.
- SKILL.md Phase 9 rewritten around the gate; schema in docs/schemas.md.
Still stage-2: automated bibliothèque ingestion of the facts (the provenance handoff) and
cross-run telemetry aggregation (dark-factory runs/-style INDEX).
- **Parallel falsification bursts** (Workflow tool, gate-free), shelve-not-refute wiring (D1
  status SHELVED is in the schema + board_ops but the Phase-4 budget path that assigns it is
  stage 2), playbook seeding proposals (D4), effort-governor SPEND wiring.
- **SFE-04 gate-report generation** (one-turn orchestrator output graded on S14 format) and
  **SFE-05/08** (F19 hooks) — the hooks already exist and have their own owner; add thin
  invocation evals here if we want them counted in this suite.

## Deferred to stage 3

- Live drills SFE-30..36 (real harness, seeded local-stack bug, drill ticket from the
  blank-Story pool — requires Gab's explicit "go" per the reuse rule). Express-lane timed
  drill SFE-36 is the real-clock counterpart of SFE-20/53.
- Gate policy slots flipped to auto-approve for unattended runs; retro telemetry.

## Compatible-from-day-1 payloads (systems are separate handoffs)

- **Bibliothèque provenance + surface registry** (`2026-07-17-bibliotheque-provenance-and-surface-registry.md`):
  Phase 9 emits knowledge-facts with provenance + playbook proposals (D4); D6 index staleness
  defaults to flag-to-librarian.
- **QC Gate / Factory Family / RND sandbox** (`2026-07-17-qc-gate-factory-family-rnd-sandbox.md`):
  the Phase-2 repro (red) + Phase-7 exit verify (green) are kept an extractable shared shape (D8).

## Design decisions made during the build (none contradict the spec)

- Gate scripts are **Python** (pyyaml present), pure functions + thin CLI, so they serve as
  both the skill's runtime gates AND the eval targets — one artifact, two consumers.
- Mechanism-class classification (SFE-41) is derived mechanically from `domain_of(component)`
  (data/db/backend/infra/config = mechanism; ui = symptom-ok), avoiding an LLM sentiment call
  (D6). `ui-probe` is the sole symptom method; `live-probe` counts for a mechanism cause only
  when its source domain matches the claim's.
- `config` maps to the **infra** layer for coverage purposes (config-drift is an infra concern).
- Cross-domain refute (SFE-44) does NOT flip the card to REFUTED at all (keeps it in the active
  set, strength weak, requeue-eligible) — the most literal reading of "cannot drop the card".
