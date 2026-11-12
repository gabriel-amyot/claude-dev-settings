# Implementation state

Approved goal: SQLite harness catalog, separate typed domains, preserve/bridge existing producer outputs, progressive static HTML/CSS. No server/framework/JavaScript.

Implemented and installed under ~/.claude-shared-config/harness. Existing user edits were preserved. The three actual ~/.claude/skill-proposals scanners were preserved as .before-harness-2026-10-26 and now symlink to shared canonical scanner files. Other producer bridges: eval run_sweep.py, dark-factory telemetry miner and write-scorecard.sh.

Live entry: /Users/gamyot/.claude-shared-config/harness/view/index.html.
Refresh: python3 ~/.claude-shared-config/harness/catalog.py refresh.
Schema/operations: harness/INDEX.md and CONTRACT.md.

Validation: 49 tests pass in the installed source, no skips with the existing PyYAML venv; Python/shell syntax and git diff --check pass. Static preview internal links/anchors and absence of scripts/network resources verified. A live producer bridge delivered without changing the original report hash. Repeat import preserved usage/eval/outcome/decision counts. Pending queue empty; three consistent database backups exist. Independent adversarial findings have regression tests.

Current data: 289 capability records (285 discovered sources plus unresolved referenced owners), 48 eval suite definitions, 49 existing per-skill eval artifacts, 54 factory assessment records and 37 selection decisions. Historical activity is partial: unsupported Codex receipts are unverified, not fabricated instruction loads. Do not treat missing evidence as non-use or a historical last_green as current validation.

BrowserQA: CUA rejected file:// URLs and forbids workarounds. No browser workaround used. HTML was checked programmatically; visual browser inspection is not claimed. The user can open the local static file normally.

Recovery: local branch harness-catalog commit b7af5dc contains tested implementation. Isolated worktree /Users/gamyot/.config/superpowers/worktrees/claude-dev-settings/harness-catalog retained for review. Installation is in the live shared source; no push or merge performed. No real eval suite, factory, deployment, external post or session-ledger mutation ran. Broader factory portability remains in its separate backlog.
