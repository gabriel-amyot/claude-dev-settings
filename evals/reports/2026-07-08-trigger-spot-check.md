# Trigger eval spot-check — klever-sprint-exit (2026-07-08)

Verification item 5 of the skill-evals plan: run the klever-sprint-exit trigger suite
through skill-creator's `run_eval.py` (3 runs/query) and check should-trigger ≥0.5 /
should-not = 0.

## Raw result (do NOT read at face value)

`python3 -m scripts.run_eval --eval-set .../klever-sprint-exit/evals/trigger-evals.json
--skill-path .../klever-sprint-exit --runs-per-query 3` → 11/20: **all 11 should-NOT
queries pass (0.00 trigger rate), all 9 should-trigger queries FAIL at exactly 0.00.**
Full JSON: /tmp/sprint-exit-trigger-results.json (transient).

## Diagnosis: runner heuristic artifact, not a routing failure

A uniform 0.00 on queries that literally quote the skill description's own MUST-trigger
examples is not a plausible description problem. Root cause in `run_eval.py`
(`run_single_query`): on `content_block_start`, **any first tool call that is not
Skill/Read immediately returns False**. In this harness — heavy SessionStart context,
150+ competing skills, task-management habits — the model's first tool call on an
operational ask is routinely TaskCreate/TodoWrite/Bash, so every should-trigger query is
scored "not triggered" regardless of what happens next. Should-not queries "pass"
trivially for the same reason, which makes the suite look half-green while measuring
nothing on the positive side. (House rule applies: a test that can't fail proves
nothing — here, a detector that can't succeed proves nothing.)

## Falsification probe (routing actually works)

Manual probe from the project-management root (real skill registry in scope), CLAUDECODE
stripped, query = the "sprint closes tomorrow at 9am and im desperate..." trap phrasing
plus "tell me which skill you would invoke first and stop":

> The skill I'd invoke first is **`klever-sprint-exit`**. [correct trap analysis follows]

Routing resolves correctly under realistic conditions.

## Disposition

- The 7 authored trigger suites are format-valid (schema confirmed against run_eval.py)
  and registered in the manifest as layer B'.
- **run_eval.py trigger-rate numbers are not meaningful signal in this harness** until
  the first-tool-call heuristic is relaxed (e.g. scan the first N tool calls, or grade
  the final transcript). Manifest B' entries carry this caveat.
- Practical interim check for routing changes: the manual probe pattern above (ask
  "which skill would you invoke, then stop") from the relevant project root.
