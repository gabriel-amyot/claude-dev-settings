# Service Factory — Changelog

The version↔improvement law: **every change to SKILL.md, a gate script, a playbook
contract, or a `docs/spec/` document bumps the version here and adds an entry.** Each entry
cites the run(s) or findings that drove it. `version:` in SKILL.md frontmatter must match
the top entry's version — `gates/version_guard.py` enforces this mechanically (SFE-60).

Versions are semver. The self-improvement telemetry that motivates changes lives in
`runs/INDEX.md` (one line per run). Spec baselines are carried, version-stamped, in
`docs/spec/` (`service-factory-spec-<version>.md`).

## 0.3.0 (2026-07-24)

**Five additive learnings from the market-research /marketResearch mid-stream
investigation, 2026-07-24.** All additive — no phase removed, no existing behavior
changed, no restructure. The line gains capability, not a rewrite.

- **Codex external adversarial review — Phase 4b (NEW).** A standard, named, reproducible
  step just before the WALL: after the agent's own falsification bursts + its own
  two-context adversarial pass, dispatch 2+ fresh-context Codex CLI reviewers
  (`codex exec --sandbox read-only`, output to `gate-reports/`) with DISTINCT lenses
  (mechanism/timeline math; ruled-out items + fix framing), each mandated to PROVE THE RCA
  WRONG. A broken load-bearing claim → back to the board; the WALL cannot be crossed on any
  claim a reviewer broke. Additive to (not a replacement for) the agent's own pass. Protocol:
  `docs/codex-external-review.md`; referenced from SKILL Phase 4b + Phase 5 precondition.
- **Round dynamic codified (Phase 4).** The refute → SHELVE → REVIVE lifecycle across rounds
  is now stated as expected/healthy (the mechanics already lived in `board_ops`), plus a
  when-stuck rule: on zero survivors, re-read the board and seed NEW theories informed by the
  prior REFUTED disproofs — never regenerate an already-refuted card.
- **Log-first + time-anchor intake (Phase 1/2).** Intake now MUST capture a time anchor
  (`reported_at`/observed window + timezone); a symptom with no anchor is a surfaced gap.
  Principle made explicit: look at logs + recent changes (`git log`) FIRST before reading
  code; ask the human for the cheap thing they HAVE (time + on-screen text), self-serve logs
  via `gcloud`, never ask for a HAR they don't have.
- **Theory-map precision (Phase 3/4 + schema).** `board.yaml` is stated explicitly as THE
  durable, schema-validated living theory map (retained as an artifact); any mermaid tree is
  only a render of it, never hand-authored. New per-card `how_killed`/lineage note surfaces
  the refute→shelve→revive trail in the render.
- **Two schema/contract additions (`docs/schemas.md`, enforced in `board_ops.py`).**
  (a) *Justify every non-trivial status transition* — REFUTED/CONFIRMED/REVIVED/INCONCLUSIVE
  cards carry inline `justification.why`+`.how` (+ optional `evidence_ref`); UNTESTED exempt;
  a bare status is a gate reject (`board_ops.justify_transition`, backward-compatible pure
  function, self-tested). (b) *EXIT output contract* — at the factory EXIT (terminal state,
  not every turn) the run must emit the RCA + `board.yaml` theory-map + exactly ONE of
  {targeted-fix handoff | Jira ticket draft}.

Version bumped 0.2.0 → 0.3.0.

## 0.2.0 (2026-07-20)

**Self-containment + explicit version↔self-improvement wiring.** The spec was documented
but hosted outside the skill (in the KTP-939 fault-audit session retro), and the
self-improvement loop had no link to a version. Both are closed here, mirroring
dark-factory's model.

- **Spec carried into the skill.** The authoritative spec now lives only in `docs/spec/`:
  `service-factory-spec-0.1.0.md` (v3 consolidated with the v4 decisions D1–D10),
  `evals-spec-0.1.0.md` (the acceptance harness), `threat-model.md` (the distilled
  fault→gate/eval mapping), and `laws-of-execution.md` (the binding substrate/gate/governor
  laws). No second copy; the external retro docs are reduced to pointer stubs. Removes the
  specification-drift risk of two live copies.
- **`CHANGELOG.md` + the version-bump law** (this file). The explicit hinge linking a
  self-improvement to the version it landed in.
- **`runs/INDEX.md` telemetry ledger.** Phase 9 now appends one line per run (ticket, date,
  terminal status, task_confidence, factory_fitness) — the cross-run aggregation that was
  previously deferred to stage 2 and stranded per-ticket.
- **`gates/version_guard.py` (SFE-60).** New un-skippable gate: SKILL.md `version:` must
  match the CHANGELOG top entry; a version-stamped spec must be carried in `docs/spec/`; and
  the authoritative spec surface must contain zero external (project-management/session-retro)
  references. The mechanical enforcement of both the version law and the no-drift law.
- **SKILL.md rewired** — the spec pointer resolves to local `docs/spec/` paths; new
  `spec_source` frontmatter field; Phase 9 gains the runs-ledger append step; version bumped
  0.1.0 → 0.2.0.

## 0.1.0 (2026-07-17) — v1 spine baseline

Initial build from the KTP-939 fault audit (spec v3 + v4 decisions D1–D10; acceptance
harness = the eval suite; defends against 34 faults + 25 bug modes + 16 inferred failure
modes).

- The nine un-skippable gate scripts (`gates/`), pure functions + CLI, each an eval target.
  `lib.py` self-tests pass (Clopper-Pearson p_lower(3/10)=0.0873 → required N=33).
- Layer A eval suite green: T1 5/5 · T2b 10/10 (Tier 2b criticals SFE-40/41/43/44 green,
  the ship bar). Registered `service-factory/gates`.
- Tier 2 paper-replay harness + graders (`service-factory/paper-replays`); Tier 2 criticals
  5/5 green.
- Phase 9 learning harvest gated (`learning_harvest.py`, SFE-56) so the self-learning loop
  cannot be narrated without being done. T1 → 6/6.
- SKILL.md orchestrator spine, templates (`rca.md`, `gate-report.md`), playbooks
  (`config-drift`, `data-gap`, `fe-state`), schemas (`docs/schemas.md`).
- Deferred to later stages: remaining Tier 2/2b paper replays, Tier 3 live drills,
  effort-governor SPEND wiring, cross-run telemetry aggregation (shipped in 0.2.0).
