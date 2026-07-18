# Hooks Catalog

Shared harness hooks used by Claude Code and Codex. Implementations live here once. Claude maps events in `~/.claude/settings.json`; Codex maps the equivalent events in `~/.codex/hooks.json`. Each hook either injects context (exit 0 with stdout) or blocks actions (exit non-zero with reason).

## Regression Evals (added 2026-07-07)

Hooks have deterministic fixture suites under `evals/` — run
`python3 evals/run_hook_evals.py [--hook <name>]`; fixture schema is in that file's
docstring; git-state fixtures come from `evals/gitfixtures.py` bundles. Suites are
registered in `../evals/manifest.yaml` and swept monthly
(`com.harness.skill-evals-monthly` launchd job; `/skill-evals` runs the sweep on
demand). **When you change a hook, extend its fixture file and re-run its suite** —
every incident and red-team finding becomes a permanent fixture. Dated findings
reports live in `evals/reports/`. Note: `file-guard.sh` and `config-protect.sh` are
currently UNWIRED; their suites carry designed-red wiring assertions pending a
wire-or-retire decision.

## Lifecycle Events

| Event | When it fires | Can block? |
|-------|--------------|------------|
| SessionStart | Session begins | No |
| UserPromptSubmit | User sends a message | No |
| PreToolUse | Before a tool executes | **Yes** (exit 1 = blocked) |
| PostToolUse | After a tool executes | No (advisory only) |
| PreCompact | Before context compaction | No |
| Stop | Session ends | No |

## Hook Registry

### PreToolUse (can block tool calls)

| Script | Matcher | Purpose | Added |
|--------|---------|---------|-------|
| `branch-guard.sh` | Edit\|Write | Blocks edits to files in git repos when branch is protected (dev/main/master) or already merged to origin/dev. Defense-in-depth against wrong-branch incidents. | 2026-05-16 |
| `deploy-identity-guard.sh` | Read\|Grep\|Bash | Blocks deployed-code reasoning from the wrong branch. Supports direct file tools and shell-based reads used by Codex. | 2026-06-29 |
| `library-stamp-guard.sh` | Agent\|Task\|spawn_agent | Blocks investigation dispatches that omit the org-library evidence stamp. Supports Claude and Codex dispatch payloads. | 2026-07-16 |
| `file-guard.sh` | Edit\|Write | Guards specific protected files from modification | — |

### UserPromptSubmit

| Script | Purpose | Added |
|--------|---------|-------|
| `challenge-detect.sh` | Injects fresh-context falsification when the user challenges a factual claim. | 2026-06-29 |
| `bibliotheque-recall.sh` | Injects matching org-library pointers before investigation begins. | 2026-07-16 |
| `rabbit-hole-guard.sh` | Converts additive session tangents into bounded probes or parked handoffs. | 2026-07-17 |

### PostToolUse (advisory context injection)

| Script | Matcher | Purpose | Added |
|--------|---------|---------|-------|
| `spec-guard.sh` | Edit\|Write | Warns when edited file is covered by SBE specs | — |
| `claude-md-guard.sh` | Edit\|Write | Injects authoring standards when CLAUDE.md is edited | — |
| `auto-index.sh` | — | Flags INDEX.md for refresh when docs are modified | — |
| `library-shelving-guard.sh` | — | Reminds agent to follow Librarian Protocol for library/ writes | — |
| `context-monitor.sh` | — | Tracks context health signals | — |

### SessionStart

| Script | Purpose | Added |
|--------|---------|-------|
| `session-init.sh` | Initialize session context | — |
| `proposal-backlog-check.sh` | Check for pending skill proposals | — |

### PreCompact

| Script | Purpose | Added |
|--------|---------|-------|
| `auto-operationalize-cmd.sh` | Inject tribal knowledge capture before compaction | — |
| `pre-compact-guard.sh` | Remind agent to persist state before compaction | — |

### Stop

| Script | Purpose | Added |
|--------|---------|-------|
| `on-exit.sh` | Log session exit for work-assistant | — |

## Troubleshooting

### branch-guard.sh

**False negatives** (doesn't block when it should):
- `origin/dev` ref is stale. Fix: `git fetch origin` in the target repo.
- File is under project-management/ (excluded by design).
- File is under /tmp/ (worktrees, excluded by design).

**False positives** (blocks when it shouldn't):
- Branch appears merged but you want to add fixup commits. Escape hatch: the agent cannot bypass this. Ask Gabriel to run the edit manually or delete the local branch and recreate it.
- `origin/dev` is ahead of what you expect. Run `git fetch origin` to update refs.

**Performance:** Sub-second. Uses local refs only (no network calls). Python invocation for JSON parsing adds ~100ms.

**RCA origin:** Created from Dexter diagnosis of KTP-669 wrong-branch incident (2026-05-16). Full report: `tickets/KTP/KTP-559/KTP-669/reports/reviews/rca-wrong-branch-2026-05-16.md`

## Adding New Hooks

1. Write the implementation in `~/.claude/hooks/`
2. `chmod +x` it
3. Register the Claude mapping in `~/.claude/settings.json`
4. Register the Codex mapping in `~/.codex/hooks.json`, including any driver-specific matcher aliases
5. Add an entry to this INDEX.md
6. Add or extend a deterministic fixture under `evals/fixtures/`
7. Run `python3 evals/run_hook_evals.py --hook <name>`
