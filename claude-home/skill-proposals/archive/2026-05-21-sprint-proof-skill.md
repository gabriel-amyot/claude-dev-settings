# Skill Proposal: sprint-proof

Date: 2026-05-21
Source: Proof System plan execution session

## Trigger
"run proof", "proof run", "sprint proof", "verify ACs", "run the proof system", or `/klever-test` option 6.

## Scope
org (Klever) — wraps `tools/proof/run-proof.sh` in project-management

## Draft Steps
1. **Preflight:** Check which layers are possible (grep always, e2e if localhost:3000 + UM:8098, api if backend:8097)
2. **Layer selection:** `--layer grep` (default first pass), `--layer e2e`, `--layer all`
3. **Execute:** Run `run-proof.sh` with selected flags, capture output
4. **Triage:** Classify failures (auth blocker, stale selector, data-dependent, genuine regression)
5. **Report:** Generate per-ticket proof files in `reports/proof/`, summarize pass/fail/skip

## Notes
- `/klever-test` option 6 already references this runner. The skill should be the wrapper that option 6 calls.
- Consider auto-detecting whether Docker/local stack is available and falling back to grep-only with a warning.
- The Playwright MCP path (interactive dev testing) is separate and complementary. The skill wraps the automated runner, not the MCP.
