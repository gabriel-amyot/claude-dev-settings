# Claude Code Harness

The portable half of the Claude Code setup: skills, agents, commands, hooks, the
cross-org library, and the plugins that carry hook-enforced gates.

## Setup on a second machine

```bash
git clone git@github.com:gabriel-amyot/claude-dev-settings.git ~/.claude-shared-config
bash ~/.claude-shared-config/bootstrap.sh
```

`bootstrap.sh` is idempotent. Re-run it after every `git pull`.

It symlinks `agents`, `commands`, `context`, `docs`, `git-hooks`, `hooks`,
`library`, `skills` and `CLAUDE.md` into `~/.claude/`, restores the loose config
from `claude-home/`, restores the plugins, and links the `ledger` helper onto
`~/.claude/bin`.

An existing `~/.claude/settings.json` is never overwritten. Diff it yourself.

## What lives where

| Path | Contents |
|---|---|
| `skills/` | Skills, symlinked to `~/.claude/skills` |
| `agents/` | Subagent definitions, symlinked to `~/.claude/agents` |
| `commands/` | Slash commands |
| `hooks/` | PreToolUse / PostToolUse / SessionStart hook scripts |
| `library/` | Cross-org bibliothèque, entry point `library/INDEX.md` |
| `tools/` | Linters and harness checks (`ste_lint.py`, `claude-md-tier-lint.py`) |
| `plugins/` | `klever-mech-suit`, `klever-wiki`, `sprint-harness`, and `local-marketplace-backup` (the sprint-crawl and session/ledger gates) |
| `claude-home/` | The parts of `~/.claude` that are not symlinked: `crawl-profiles/`, `deploy-identity/`, `harness/`, `settings.json`, `statusline-command.sh`, `pmd-java-gate.json` |
| `CLAUDE.md` | Global instructions, symlinked to `~/.claude/CLAUDE.md` |

## Limits

- Hook commands in `settings.json` use absolute paths under `$HOME`. They work
  only if both machines use the same username.
- `plugins/local-marketplace-backup/` is a copy, not a symlink. After changing a
  plugin on either machine, re-sync it before committing.
- Machine-local state is not in this repo: `projects/`, `todos/`, `sessions/`,
  `tasks/`, `teams/`, `history.jsonl`, credentials.
- MCP servers are configured per machine. Re-add them with `claude mcp add`.

## Keeping both machines in sync

```bash
cd ~/.claude-shared-config && git pull && bash bootstrap.sh
```

Commit and push harness changes before switching machines.
