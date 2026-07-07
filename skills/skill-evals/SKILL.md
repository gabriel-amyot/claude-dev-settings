---
name: skill-evals
description: Run the harness's eval suites — the single entry point for regression-testing skills, gates, and hooks. Fast path runs every deterministic Layer A suite from the eval manifest in seconds; --target runs one; --behavioral routes Layer B suites through the skill-creator grader. Use when upgrading any skill/hook/gate ("run the evals", "eval sweep", "did my change break a gate", "test the hooks"), after editing anything under hooks/ or a skill's scripts, or when the monthly sweep flags failures.
nav:
  bay: ops
  when: "Regression-test skills, gates, and hooks; run the eval sweep; verify a harness change."
  when_not: "Creating a brand-new skill's evals from scratch (use skill-creator). Testing app code (use the repo's test suite)."
---

# Skill Evals — one entry point for harness regression suites

Every ≥1/month skill and every wired hook has (or is excluded from) a regression suite,
registered in **`~/.claude-shared-config/evals/manifest.yaml`**. Read that manifest first;
it is the source of truth for what exists, how to run it, and what is deliberately excluded.

## Fast path — Layer A sweep (default)

```bash
python3 ~/.claude-shared-config/skills/skill-evals/scripts/run_sweep.py
```

Runs every Layer A (deterministic fixture) suite. Seconds, no model calls, safe anywhere.
On failure it writes a dated report to `evals/reports/` AND a decision item to the Mission
Control inbox (`general/user/inbox/decisions/`) — so unattended runs surface failures.

Single suite: `run_sweep.py --target <target-name-from-manifest>`.

Hook suites can also be run directly, which gives per-case detail:

```bash
python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py [--hook <name>] [-v]
```

## Layer B — behavioral evals (`--behavioral`, on-demand only)

Layer B suites are `evals/evals.json` files in skill-creator schema, listed in the manifest
with `layer: B`. They spawn headless claude runs — never run them from the monthly sweep.

To run one: invoke the **skill-creator** skill in benchmark mode against the skill's
directory (it uses `scripts/run_eval.py` + the grader agent, n=3 runs per eval). Judge the
result against the suite's documented pass-rate threshold (default ≥0.75 expectation pass
rate). Record the outcome by updating `last_green` for that suite in the manifest.

## Layer B′ — trigger evals

Flat `[{query, should_trigger}]` files (`evals/trigger-evals.json`), run via skill-creator's
`run_eval.py` trigger mode, 3× per query. Should-trigger queries need ≥0.5 trigger rate;
should-not-trigger queries need 0.

## Adding a suite (when you change a gate or ship a new skill)

1. **Hooks** → add/extend `~/.claude-shared-config/hooks/evals/fixtures/<hook>.yaml`
   (schema documented in `run_hook_evals.py`'s docstring). Git-state cases use the
   bundles in `fixtures/repos/` (`gitfixtures.py --build` regenerates them).
2. **Skill scripts** → self-contained `evals/run_evals.py` beside the skill, cloned from
   the post-comment pattern (`skills/post-comment/evals/run_causal_evals.py`).
3. **Prompt-only skills** → `evals/evals.json` (skill-creator schema).
4. Register in `evals/manifest.yaml` (or add an exclusion with a rationale).
5. Write a dated `evals/<date>-eval-report.md` beside the suite on creation.
6. **Every incident and red-team finding becomes a permanent fixture.** That is the point.

## Failure triage

A failing suite means one of exactly three things — pick deliberately, never silently re-pin:

| Cause | Action |
|---|---|
| Real regression in the gate/script | Fix the target, re-run to green |
| Intentional behavior change | Update the fixture, note why in the fixture file |
| Wiring assertion (hook not registered in settings.json) | Human decision — surface via inbox-writer, do NOT edit settings.json unilaterally |

If a sweep failure needs Gabriel's decision and the sweep's auto-inbox item is not enough
context, write a richer item via the **inbox-writer** skill.

## Monthly schedule

`launchd` job `com.harness.skill-evals-monthly` runs the Layer A sweep on the 1st of each
month (wrapper: `~/.claude-shared-config/evals/monthly-sweep/run_monthly_sweep.sh`).
Layer B/B′ stay on-demand.
