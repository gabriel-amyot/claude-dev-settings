# Service Factory — Changelog

The version↔improvement law: **every change to SKILL.md, a gate script, a playbook
contract, or a `docs/spec/` document bumps the version here and adds an entry.** Each entry
cites the run(s) or findings that drove it. `version:` in SKILL.md frontmatter must match
the top entry's version — `gates/version_guard.py` enforces this mechanically (SFE-60).

Versions are semver. The self-improvement telemetry that motivates changes lives in
`runs/INDEX.md` (one line per run). Spec baselines are carried, version-stamped, in
`docs/spec/` (`service-factory-spec-<version>.md`).

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
