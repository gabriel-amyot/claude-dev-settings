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

## `~/.claude/library/` and `~/.claude/plugins/local-marketplace/**` are real directories, not git-tracked

These paths persist on disk across sessions but sit outside every git repo on the machine. Two
consequences:

- An edit to a file under `~/.claude/library/context/` needs no commit, and running `git add` from
  inside `~/.claude-shared-config` will not see it (it is a different filesystem location entirely,
  not a symlink target).
- The local-marketplace session-plugin skills (`init`, `pickup`, `check`, …) are the same: real
  files, no rollback via git if something goes wrong there.

**How to apply:** a single harness change can span two tracked repos
(`~/.claude-shared-config` for CLAUDE.md/hooks/skills, and the target project's own repo) plus
untracked-but-persistent library or plugin files. Track each piece by where it actually lives, not
by assuming one commit covers "the harness."

---

**Source:** harness-proposals triage session gotchas, bold-jackal handoff N1 pickup, 2026-08-27.
