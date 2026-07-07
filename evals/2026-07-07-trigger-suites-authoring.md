# Trigger eval suites — authoring pass (Wave 4, Layer B')

Date: 2026-07-07
Scope: authoring only. No headless `claude -p` runs were executed against these suites in this pass — the lead spot-checks one later.

## Format confirmed from run_eval.py

Read `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/scripts/run_eval.py`.

- `--eval-set` takes an arbitrary path to a JSON file; the script does not hardcode a filename, so `evals/trigger-evals.json` (the convention used by the existing `klever-sprint-exit` suite) is followed here for consistency across the harness.
- The file content is a flat JSON array: `[{"query": "<string>", "should_trigger": <bool>}, ...]`. No wrapper object, no metadata keys — confirmed exactly, no deviation from the brief.
- `skill_name` and `description` are read from the target skill's own `SKILL.md` frontmatter at run time (`parse_skill_md`), not from the eval file — so these files carry only query/expectation pairs, nothing skill-identifying.
- Default `trigger_threshold=0.5`, default `runs_per_query=3` (i.e. should-trigger passes at ≥2/3, should-not-trigger passes only at 0/3 — trigger_rate < 0.5 means 0 or occasionally 1/3 depending on threshold; brief's stated threshold of "should-trigger ≥0.5 over 3 runs; should-not = 0" is the stricter, correct read and is what's used below).

## Files written

| Suite | Skill | Path | Queries (true/false) |
|---|---|---|---|
| 1 | klever-sprint-mgmt | `~/Developer/grp-beklever-com/project-management/.claude/skills/klever-sprint-mgmt/evals/trigger-evals.json` | 10 (6/4) |
| 1 | klever-sprint-exit | *(already existed, git-tracked, committed with the skill — left untouched)* `~/Developer/grp-beklever-com/project-management/.claude/skills/klever-sprint-exit/evals/trigger-evals.json` | 20 (9/11) pre-existing |
| 2 | ui-probe | `~/.claude-shared-config/skills/ui-probe/evals/trigger-evals.json` | 10 (6/4) |
| 2 | klever-test | `~/.claude-shared-config/skills/klever-test/evals/trigger-evals.json` | 10 (6/4) |
| 3 | investigate | `~/.claude-shared-config/skills/investigate/evals/trigger-evals.json` | 10 (6/4) |
| 4 | challenge | `~/.claude-shared-config/skills/challenge/evals/trigger-evals.json` | 8 (4/4) |
| 4 | adversarial-cascade | `~/.claude-shared-config/skills/adversarial-cascade/evals/trigger-evals.json` | 8 (4/4) |

`superpowers:brainstorming` (Suite 4, plugin) — not written. Plugin dir is out of scope per constraints ("do not modify SKILL.md files or plugin files"); registered here as rationale-only, mirroring the `exclusions` pattern already used in `manifest.yaml` for other plugin skills (mapping:mapbox, adtech:goldfish/placer). If a suite is wanted later, it belongs in a harness-owned overlay, not the plugin's own tree.

## Note on klever-sprint-exit

`klever-sprint-exit/evals/trigger-evals.json` already existed (committed in `133aeac Add klever-sprint-exit skill: overnight sprint close-out orchestrator`) with 20 well-crafted queries that already cover the exact trap phrasings from the SKILL.md description (deadline-pressured "finish and ship" language) plus should_trigger=false mirrors for sprint-mgmt, dark-factory, klever-mr, sprint-estimation, klever-test, and deploy asks. It meets and exceeds this task's bar. Left as-is rather than overwritten — Write tool correctly refused the overwrite attempt (untracked-read guard), which is what surfaced that it already existed.

## Per-suite thresholds (uniform across all files above)

- should_trigger=true: PASS requires trigger_rate ≥ 0.5 over `runs_per_query=3` (i.e. ≥2/3 runs invoke the skill).
- should_trigger=false: PASS requires trigger_rate < 0.5 over 3 runs, i.e. 0/3 (any single false-positive trigger in 3 runs should be treated as a finding worth investigating, not just a marginal fail).

## Proposed manifest.yaml entries (NOT applied — constraint was "only write eval files + this note")

```yaml
  - target: klever-sprint-mgmt/trigger
    layer: B'
    runner: python3 -m scripts.run_eval --eval-set ~/Developer/grp-beklever-com/project-management/.claude/skills/klever-sprint-mgmt/evals/trigger-evals.json --skill-path ~/Developer/grp-beklever-com/project-management/.claude/skills/klever-sprint-mgmt
    owner_skill: klever-sprint-mgmt

  - target: klever-sprint-exit/trigger
    layer: B'
    runner: python3 -m scripts.run_eval --eval-set ~/Developer/grp-beklever-com/project-management/.claude/skills/klever-sprint-exit/evals/trigger-evals.json --skill-path ~/Developer/grp-beklever-com/project-management/.claude/skills/klever-sprint-exit
    owner_skill: klever-sprint-exit

  - target: ui-probe/trigger
    layer: B'
    runner: python3 -m scripts.run_eval --eval-set ~/.claude-shared-config/skills/ui-probe/evals/trigger-evals.json --skill-path ~/.claude-shared-config/skills/ui-probe
    owner_skill: ui-probe

  - target: klever-test/trigger
    layer: B'
    runner: python3 -m scripts.run_eval --eval-set ~/.claude-shared-config/skills/klever-test/evals/trigger-evals.json --skill-path ~/.claude-shared-config/skills/klever-test
    owner_skill: klever-test

  - target: investigate/trigger
    layer: B'
    runner: python3 -m scripts.run_eval --eval-set ~/.claude-shared-config/skills/investigate/evals/trigger-evals.json --skill-path ~/.claude-shared-config/skills/investigate
    owner_skill: investigate

  - target: challenge/trigger
    layer: B'
    runner: python3 -m scripts.run_eval --eval-set ~/.claude-shared-config/skills/challenge/evals/trigger-evals.json --skill-path ~/.claude-shared-config/skills/challenge
    owner_skill: challenge

  - target: adversarial-cascade/trigger
    layer: B'
    runner: python3 -m scripts.run_eval --eval-set ~/.claude-shared-config/skills/adversarial-cascade/evals/trigger-evals.json --skill-path ~/.claude-shared-config/skills/adversarial-cascade
    owner_skill: adversarial-cascade
```

(`python3 -m scripts.run_eval` assumes invocation from the skill-creator skill dir per its own module layout — `run_eval.py` imports `from scripts.utils import parse_skill_md`, i.e. it must be run with the skill-creator dir as CWD/on the path, or invoked as `python3 <path-to>/run_eval.py ...` from within that dir. Confirm the exact invocation convention already used elsewhere in the manifest before registering — no existing suite in the current manifest calls this script, so there's no established precedent to match yet.)

## Skills not located / not writable

None. All six target skills (klever-sprint-exit, klever-sprint-mgmt, ui-probe, klever-test, investigate, challenge, adversarial-cascade) were found and writable. `~/.claude/skills/{ui-probe,klever-test,investigate,challenge,adversarial-cascade}` are symlinks into `~/.claude-shared-config/skills/`, confirmed via `readlink -f`, so writing once under `~/.claude-shared-config/skills/` covers both locations named in the brief — no duplicate files needed.
