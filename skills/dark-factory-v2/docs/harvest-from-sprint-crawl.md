# Harvest from sprint-crawl → dark-factory-v2

**Status:** Reference (2026-06-03, session deft-heron). Captures what the `sprint-crawl` agent + `sprint-harness`
plugin do, and which mechanisms are worth porting into v2 vs. which are substrate-bound and can't transfer.

**Decision context:** sprint-crawl is NOT being deleted (it stays as the overnight-autonomous, context-death-resilient
per-AC executor — the role v2 does not fill). The likely future is that sprint-crawl becomes a thin ralph-loop
wrapper that drives `/dark-factory-v2`. This doc exists so the *ideas* are in v2's orbit regardless.

## The three tools are different modes, not three versions

| Tool | Substrate | Mode it owns |
|------|-----------|--------------|
| **sprint-crawl** | Agent + sprint-harness Bash hooks | Overnight-autonomous, resumable-across-context-death, per-AC |
| **dark-factory v1** (→ "Sprint Factory") | Prose orchestration, agent dispatch | Multi-ticket / epic DAG with tiered parallelism |
| **dark-factory-v2** | Workflow-tool script, JS gates | Single-ticket, human-gated, interactive |

## sprint-crawl mechanism inventory

| Mechanism | How it works | Problem it solves |
|-----------|-------------|-------------------|
| Spec gate (Leo) | Validates each AC is observable/implementable/assertable; writes `spec-gate-report.yaml` (pass / proceed-with-assumptions / abort) | No token waste on vague ACs |
| Context gate (Curator) | Checks repo sync, bibliothèque coverage, dependency completion, ADRs/contracts, tool auth (gcloud/BQ); writes `context-manifest.yaml` (ready / ready-with-gaps / not-ready) | No mid-sprint discovery of missing context |
| Phase-gate hook (`phase-gate.sh`, PreToolUse) | Blocks Edit/Write/Bash by phase; always blocks protected paths (`.env`, lockfiles) in any phase | Phase discipline + fail-safe, enforced *below* the agent |
| Stop-guard hook (Stop) | Blocks exit unless phase is `done`/aborted/shipped; coexists with ralph-loop's stop hook | No context death mid-phase |
| Context-reinject hook (SessionStart) | On resume/compact, injects harness state (phase, AC, completed, assumptions, gate status) as additionalContext | Survives compaction with no re-reads |
| Pre-compact hook (PreCompact) | Reminds to sync `ac.yaml`/reports before compaction | Catch unsaved progress |
| Audit-trail hook (PostToolUse) | Logs every Edit/Write: `timestamp | phase | AC | tool | file` | Forensic trail across context deaths |
| ac.yaml save-point + `/harness ac` | Per-AC switching; completed ACs tracked; new AC resets phase | Per-AC granular resume |
| advance state-machine | Validates gate conditions, increments phase; reverts review→implement on CRITICAL | Gate-skip prevention + auto loop-back |

## What ports into v2 (concepts) vs. what doesn't (substrate)

**Substrate-bound — does NOT transfer.** v2 is a single Workflow run with no PreToolUse/SessionStart/Stop/PreCompact
hook API. So: phase-gate hook, stop-guard, context-reinject, pre-compact, audit-trail hook. v2 already solves the
same intents differently: JS gates that can't be skipped (vs phase-gate hook), segregated worktrees (vs protected
paths), `resumeFromRunId` (vs context-reinject), structured `review/findings.json` + `qa/result.yaml` (vs audit log).

**Ports as a concept — worth adding to v2:**

1. **Curator context-readiness checklist** → enrich Contract 1 (concierge). v2's concierge does spec-quality +
   prereqs but not the full sweep: repo-sync-clean, bibliothèque coverage for domain terms, dependency-completion,
   tool-auth (gcloud/BQ). Fold these in as concierge checks.
2. **Per-AC iterate + loop-back on review CRITICAL** → the v1 "Quinn attacks, Amelia fixes" loop and sprint-crawl's
   review→implement revert. v2 is single-pass and HALTs at `HALT_PRESHIP`/`BLOCKED_REVIEW_CRITICAL` instead of
   bouncing back to a bounded fix attempt. This is v2's "added rigor" roadmap item. (See proposal below.)
3. **Per-AC progress as a resume save-point** → v2 has `resumeFromRunId`, but it resumes at agent-call granularity,
   not AC granularity. Persisting per-AC verdicts would let a resumed run skip already-passed ACs.

**Overnight persistence** is NOT a v2 feature to build — it's sprint-crawl's job (ralph-loop + state file). The
intended convergence: sprint-crawl becomes the ralph-loop wrapper that invokes `/dark-factory-v2` and resumes via
`resumeFromRunId`.

## Open design question for per-AC loop-back (before implementing in workflow.js)

v2's review/QA are single segregated agents over the *whole* branch diff, not per-AC. A true per-AC loop needs
either (a) a bounded implement→review→QA retry over the whole ticket when review finds a CRITICAL (fix → re-review,
max N rounds) — small, spine-safe; or (b) restructuring review/QA to iterate per-AC — larger, changes the segregated-
review model. (a) captures most of the resilience value without breaking the ADR-002 spine boundary. Recommended: (a).
