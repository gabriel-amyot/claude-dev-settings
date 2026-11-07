# ADR-002: SessionStart hook lives in the plugin, not global settings

**Date:** 2026-05-29
**Status:** Accepted
**Context:** Session plugin v2.0 design grill

## Context

The v2 plan proposed a SessionStart hook to nudge users toward `/session:init` or `/session:pickup` at conversation start. The original plan placed it at `~/.claude/hooks/session-init-reminder.sh` (global) with a `settings.json` entry.

## Decision

Place the hook in the plugin at `hooks/hooks.json` as a command hook on SessionStart.

## Rationale

1. **Portability.** The hook travels with the plugin. Enabling/disabling the session plugin automatically enables/disables the hook. No orphaned global hooks.
2. **SessionStart is fully supported.** Claude Code's hook-development documentation lists SessionStart as a first-class plugin hook event. Plugin hooks support the same lifecycle events as user settings hooks.
3. **Format constraint.** SessionStart cannot be a prompt hook (prompt hooks only support Stop, SubagentStop, UserPromptSubmit, and PreToolUse). It must be a command hook. This is the only real limitation.
4. **File placement.** Plugin hooks go in `hooks/hooks.json` at the plugin root, not inside `plugin.json` or `.claude-plugin/plugin.json`. The manifest is metadata only.

## Alternatives considered

- **Global settings.json:** Works (user already has 2 SessionStart hooks). But the hook is decoupled from the plugin. If someone disables the session plugin, the hook still fires and nudges about init for a disabled plugin.
- **Both plugin + global:** Redundant. Plugin hook is sufficient.

## Consequences

- No changes to `~/.claude/settings.json`.
- New file: `hooks/hooks.json` in the plugin root.
- New file: the hook script itself, referenced from hooks.json.
- The hook reads `sessions/ledger.yaml`, counts awaiting handoffs, emits a one-line system message.
