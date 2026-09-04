# Claude Config Filesystem Topology — Symlinks and Tracking

On-demand context: load before editing any file under `~/.claude/`, or when a harness change spans
more than one location and you need to know what gets committed where.

## `~/.claude/CLAUDE.md`, `hooks/`, `skills/` are symlinks into `~/.claude-shared-config/`

The Edit and Write tools refuse to write through a symlink: "Refusing to write through symlink:
resolve the symlink and pass the real target path explicitly." This fires on `~/.claude/CLAUDE.md`
and any other dir-level symlink into `~/.claude-shared-config/`.

**How to apply:** run `readlink -f ~/.claude/CLAUDE.md` first (resolves to
`~/.claude-shared-config/CLAUDE.md`), then edit the real target path directly. A commit against
that edit lands in the `~/.claude-shared-config` git repo, not a `~/.claude` repo (there is none).

## `~/.claude/library/` IS a symlink and IS git-tracked. `~/.claude/plugins/` is real and is NOT

These two were previously documented together as "real directories, not git-tracked." That was
wrong for `library/` and it misled both an orchestrator and a subagent on 2026-09-03. Verified:

| Path | Kind | Tracked in `~/.claude-shared-config`? |
|---|---|---|
| `~/.claude/library/` | symlink → `~/.claude-shared-config/library` | **Yes** — `git ls-files library/` returns 164 |
| `~/.claude/plugins/` | real directory | **No** — `git ls-files 'plugins/local-marketplace'` returns 0 |

- An edit under `~/.claude/library/context/` **does** need a commit, and it lands in the
  `~/.claude-shared-config` repo. Resolve the symlink before editing (see the section above).
- `~/.claude/plugins/local-marketplace/**` genuinely has no git backup. That includes the
  session-plugin skills (`init`, `pickup`, `check`, …) **and `session/bin/ledger.py`**, the helper
  that project instructions make the only sanctioned writer of `sessions/ledger.yaml`. A
  load-bearing tool with no rollback and no second-machine copy.

**How to apply:** verify tracking with `git -C ~/.claude-shared-config ls-files <subpath>` before
claiming any `~/.claude` path is or is not backed up. Do not infer it from whether the path looks
like a real directory.

**How to apply:** a single harness change can span two tracked repos
(`~/.claude-shared-config` for CLAUDE.md/hooks/skills, and the target project's own repo) plus
untracked-but-persistent library or plugin files. Track each piece by where it actually lives, not
by assuming one commit covers "the harness."

---

**Source:** harness-proposals triage session gotchas, bold-jackal handoff N1 pickup, 2026-08-27.
