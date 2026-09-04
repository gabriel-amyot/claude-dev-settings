# Backup of ~/.claude/plugins/local-marketplace

This is a BACKUP, not the live location. Claude Code and Codex both read the live copy at
`~/.claude/plugins/local-marketplace/`, which is a real directory outside every git repo and
therefore has no rollback and would be absent on a fresh machine.

Why it matters: `session/bin/ledger.py` lives here. Project instructions make it the only
sanctioned writer of `sessions/ledger.yaml` (it takes an flock that raw writes skip) and warn
agents not to rebuild it. It had zero git coverage before 2026-09-04.

This copy drifts the moment the live tree changes. Either promote the live tree into git
properly, or stop `settings.json` hardcoding this path — see the harness consolidation plan,
`general/harness/2026-09-03-harness-consolidation-plan.md`, Step 9.

## Deliberate gap in this backup

`session/bin/evals/` is EXCLUDED. Its `test_ledger.py` trips the gitleaks pre-commit hook with
5 `generic-api-key` findings, all false positives: the rule matches ledger status strings like
`awaiting_initiation` and filename keys like `2026-07-30-eval.md`. There are no secrets in it.

It was excluded rather than allowlisted because this repo has no `.gitleaks.toml`, and adding a
root-level scanner config is a harness-wide security change that should be a deliberate decision,
not a side effect of taking a backup. The alternative (`GITLEAKS_SKIP=1`) was not used.

So the ledger eval suite still has no git backup. To close that, add a `.gitleaks.toml` with
`[extend] useDefault = true` plus a path-scoped allowlist for this one file, then re-add the
directory.
