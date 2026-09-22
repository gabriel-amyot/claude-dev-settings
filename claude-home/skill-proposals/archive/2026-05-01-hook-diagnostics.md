# Skill Proposal: hook-diagnostics
Date: 2026-05-01
Source: Mission Control Phase 6 session, stale stop hook investigation

## Trigger
When a hook fires stale or unexpected content repeatedly, or user says "hook is broken", "stop hook won't stop", "stale hook", "why does this keep firing".

## Scope
global

## Draft Steps
1. Read `~/.claude/settings.json` and project `.claude/settings.json` for all hook entries
2. For each hook command path, verify the script exists and read it
3. Check for ralph-loop state files (`.claude/ralph-loop.local.md`) in the project
4. Check plugin cache for hook scripts (`~/.claude/plugins/cache/`)
5. Report: which hooks are registered, which have state files, which might be producing stale output
6. Recommend fix (clear state file, start fresh session, or modify hook script)
