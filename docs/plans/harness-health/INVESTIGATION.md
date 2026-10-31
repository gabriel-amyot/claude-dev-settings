# Harness health investigation

Observed: 2026-10-31. Scope: the shared harness, installed Claude/Codex surfaces, and Klever project-management. Two investigation agents inspected source and installed metadata. No live eval sweeps, headless model runs, hooks, schedules, catalog writes, or project mutations were performed.

## Existing assets

| Asset | Observed evidence | Reuse boundary |
|---|---|---|
| Eval registry | `~/.claude-shared-config/evals/manifest.yaml`: 48 suites, comprising 32 deterministic A, 9 behavioral B, 7 trigger B′; 10 exclusions | Keep one registry. Historical `last_green` does not establish current compatibility or policy correctness. |
| Sweep runner | `skills/skill-evals/scripts/run_sweep.py` | Executes A suites and writes reports, manifest dates, an old inbox location, and catalog publication. It is not read-only. Its CLI does not implement the B/C/paired-arm workflows described in the skill. |
| Hook fixtures | `hooks/evals/fixtures/`, `run_hook_evals.py` | 17 fixture files, 183 executable cases and 17 wiring checks. Only 15 fixture files, 157 cases and 15 wiring checks are registered. `jira-create-gate` and `library-stamp-guard` are omitted. |
| Behavioral examples | Notion scripted-world runner and per-skill `evals.json` files | Reuse neutral prompts, replay worlds and outcome assertions. Some existing cases target live external services. These need isolated fixtures and connector substitutes before unattended execution. |
| Observatory | `harness/CONTRACT.md`, `schema/001.sql`, `BRIDGES.md`, `producer.py` | Reuse typed domains, immutable observations, artifact links, coverage, producer ownership, backups and retry. Current strict schema lacks episodes, numerical measurements and experiment assignments. |
| Observatory tests | `harness/tests/` | 49 test methods were counted. The dated validation record reports earlier runs; no fresh test result is claimed here. |
| Kev apparatus | Pilot execution worktree, `experiments/kev-pilot/` | Reuse frozen snapshots, source/model/protocol hashes, request receipts, explicit failure accounting, and bounded studies. |

The canonical shared checkout is dirty and contains untracked observatory implementation files. A clean clone of the current remote main branch does not reproduce all inspected capabilities. Preserve and version the intended existing implementation before extending it. Do not copy it blindly or treat the dirty checkout's HEAD as its complete source identity.

## Validity and operational findings

1. The current tool-shell `python3` cannot import PyYAML. That does not prove which interpreter an installed scheduler uses. A qualified, pinned environment is needed.
2. The monthly wrapper echoes the sweep exit status, then ordinarily exits successfully through that final echo. Scheduler exit status can therefore conceal a failed sweep.
3. The sweep writes failure decisions to the obsolete `general/user/inbox/decisions/` path. The current Gabriel inbox index identifies a GitHub-backed queue. Queue routing must be explicit and current, with private local evidence kept out of automatic public posts.
4. Some passing fixtures characterize known defects. Examples include broken allow behavior in config-protect and success exits for invalid links. Characterization is not intended-policy conformance.
5. Hook wiring checks look for a basename substring under an event. They do not establish correct matcher, executable path, host dispatch or effective enforcement.
6. A prior trigger report documents an invalid first-tool heuristic. Trigger declarations, instruction loads and actual skill execution remain different observations.
7. A behavioral canary can remain green after its governing prose is removed. Outcome tests and instruction-value ablations answer different questions.
8. New sweep publications retain `revision: None`, lack per-case timings and omit a complete host/model/configuration fingerprint. Honest unknowns are useful, but cannot establish paired before/after effects.
9. Observatory activity is currently Klever-scoped. Discovery is broader than activity collection. Successful instruction reads and invocations are not completed user tasks.
10. Documentation of a monthly or hourly job does not establish an active installation. No matching local registration was found in the inspected launchd/cron/Codex local stores. Hosted/cloud scheduling was not exhaustively inventoried.
11. The current activity collector enumerates and opens Codex session files before per-event scope filtering. It cannot satisfy the proposed admission-before-read privacy contract unchanged. The eval producer tracer can avoid this collector.

## Installed host inventory

| Surface | Verified installed metadata | Not established by this investigation |
|---|---|---|
| Codex CLI | PATH CLI `0.166.0`; hooks feature enabled; JSON execution interface | Actual hook delivery and complete event/usage coverage |
| Codex desktop | `ChatGPT.app`, bundle `com.openai.codex`, app `26.1027.30824`, bundled CLI `0.166.0-alpha.5.1` | Current conversation engine, trusted hook execution and complete accounting |
| Claude Code CLI | `2.1.280`; headless JSON/stream interfaces; user hooks configured | Actual current-session event completeness |
| Claude desktop | App `4.4212.0`; downloaded Code engine `2.1.309` | Which engine an already-open session uses and actual receipt completeness |

Codex hook support exists. Earlier portability notes must not become a false premise that Codex cannot support hooks. The inspected Codex user/project hook configuration was absent. Claude user hooks and a project-management PostToolUse hook were configured. Configuration presence is not delivery evidence.

## Completed Kev evidence

The existing detached study completed successfully and preserved source integrity:

- 15 authored probe requests, 310 measured benchmark requests and 403 diagnostic requests completed without request failures.
- The diagnostic replay covered 24 authored queries. Neither lexical nor Kev top-five results had complete original relevance judgments on any query. A quality winner remains unknown.
- Controlled whole-query benchmark median: approximately 4.83 seconds for five candidates and 18.61 seconds for twenty, six operations per size.
- Twenty-candidate authored library replay median: approximately 25.30 seconds across fourteen such queries. This is a different workload from the controlled benchmark.
- Kev sees document bodies while the current lexical baseline searches metadata. The next comparison must equalize available information and separate candidate generation from reranking.
- Fresh diagnostic label review covered 127 query-page pairs and found three disagreements among 28 overlapping authored grades. These remain authored cases, not a population holdout.

No operational improvement, calibration guarantee or safe deployment threshold follows from those results. They are reusable measurements and diagnostic fixtures.

## Primary local sources

- [Eval registry](/Users/gamyot/.claude-shared-config/evals/manifest.yaml)
- [Sweep runner](/Users/gamyot/.claude-shared-config/skills/skill-evals/scripts/run_sweep.py)
- [Monthly wrapper](/Users/gamyot/.claude-shared-config/evals/monthly-sweep/run_monthly_sweep.sh)
- [Observatory contract](/Users/gamyot/.claude-shared-config/harness/CONTRACT.md)
- [Producer bridges](/Users/gamyot/.claude-shared-config/harness/BRIDGES.md)
- [Host mapping](/Users/gamyot/.claude-shared-config/docs/skill-host-compatibility.md)
- [Completed study status](/Users/gamyot/.claude-shared-config-worktrees/kev-readonly-pilot/experiments/kev-pilot/.local/studies/20261031T150227.051702Z/status.json)
- [Pilot protocol](/Users/gamyot/.claude-shared-config-worktrees/kev-readonly-pilot/experiments/kev-pilot/protocol.json)

## Official interface references

- [OpenAI: skill evaluations and JSONL execution](https://developers.openai.com/blog/eval-skills)
- [OpenAI: non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode)
- [OpenAI: hooks and limitations](https://learn.chatgpt.com/docs/hooks)
- [OpenAI: plugin hooks and exact-definition trust](https://developers.openai.com/plugins/build/plugins)
- [Claude: hooks](https://code.claude.com/docs/en/hooks)
- [Claude: desktop behavior](https://code.claude.com/docs/en/desktop)
- [Claude: headless execution](https://code.claude.com/docs/en/headless)
- [Claude: native usage monitoring](https://code.claude.com/docs/en/monitoring-usage)

These references document supported interfaces. Installed-version probes and fresh qualified sessions must establish their behavior on this machine.
