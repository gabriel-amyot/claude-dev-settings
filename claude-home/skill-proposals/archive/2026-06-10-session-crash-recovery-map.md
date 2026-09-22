# Skill Proposal: session-crash-recovery-map
Date: 2026-06-10
Source: brave-ibis (recovering ~10 in-flight Claude Code sessions after a reboot)

## Trigger
User's machine rebooted/crashed with multiple Claude Code sessions open and wants to find and resume the important ones. Phrases: "my computer restarted", "lost my sessions", "recover my sessions", "which sessions were open", "what was I working on across tabs", "resume the crashed sessions".

## Scope
Global (works in any project — resolves the project-slug from cwd).

## Draft Steps
1. Resolve the project session dir: `~/.claude/projects/{cwd-with-slashes-as-dashes}/`.
2. Script-mine the N most-recent `*.jsonl` (NEVER bulk-read into context — output to /tmp). Per session extract: first real user msg (skip isMeta, strip system-reminder/command-message), last user msg, `type:"summary"` title, mtime, line count, and done-signals (`/clear` in last ~12 entries; last-assistant close-recommendation language).
3. Flag done/excludable vs open. Verify done-flags against actual last-message content (avoid false positives like `ksprint:close` keyword matches; a session ending on an assistant question is OPEN).
4. Rank open candidates against the user's described topics; for ambiguous topics, run a discriminating keyword sweep across ALL sessions (use absolute paths + /tmp redirect — `cd` into the projects dir triggers a chpwd auto-ls that pollutes output).
5. Present a ranked table: topic → session-id → main intent → latest worked intent → `claude --resume <id>`. Recommend resume for live mid-task work; recommend fresh + `/session:pickup <handoff>` for wrapped/distilled sessions.

## Notes / gotchas to bake in
- SpecStory `.md` is read-only (not resumable); JSONL is the resumable source.
- `cd ~/.claude/projects/<slug>/` → zsh chpwd auto-`ls` dumps the huge dir into stdout. Don't cd; absolute paths + /tmp.
- `find .` catches per-session UUID subdirs — use `-maxdepth 1 -name '*.jsonl' -type f`.
- PATH can be lost in piped `while read` subshells; call `/usr/bin/stat`, `/usr/bin/awk` by absolute path or use stat's built-in time formatting.
