# pre-ship-gate.sh — eval report (2026-07-07)

Target: `~/.claude-shared-config/skills/sprint-factory/resources/pre-ship-gate.sh` (Dark Factory
Phase 7 artifact gate — HALTs shipping if QA report / review artifacts / execution_verified /
frontend screenshots are missing).

## Results

`run_preship_evals.py` — **13/13 passing**.

Run: `python3 ~/.claude-shared-config/skills/sprint-factory/evals/run_preship_evals.py`
(`-v` for full gate output per case).

Coverage: happy path (backend-only), missing/empty/stub QA report, missing/empty review/, missing
pipeline-state.yaml, pipeline-state.yaml present but no `execution_verified:` field, frontend
ticket with no screenshots and no documented exemption, frontend ticket with screenshots, frontend
ticket documented as "no UI change" in the QA report, usage errors (no arg / dir not found — exit
2), and a multi-version QA report case that pins the `sort -V | tail -1` "pick the latest" logic
(a stub v1 + a real v2 must still PASS).

## Notes

- Existing `evals.json` + `fixtures/` in this same `evals/` dir are untouched — those are a
  different (plan-file) test surface; this runner is additive, targeting the bash gate script
  only.
- No bugs found in `pre-ship-gate.sh` itself. The script's exit-code contract (0/1/2) and its
  glob-and-sort-by-version pattern for picking the latest QA report both behave exactly as the
  header comments describe.
