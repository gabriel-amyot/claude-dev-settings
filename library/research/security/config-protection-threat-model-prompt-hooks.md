# Config Protection Security Research

## Protected Paths
- `~/.claude/CLAUDE.md`
- `~/.claude/settings.json`
- `agent-os/sbe/**` (planned, not yet enforced via deny rules)

## Threat Model

| Level | Threat | Severity |
|---|---|---|
| 1 | User asks Claude to edit config carelessly in bypassPermissions | Low |
| 2 | Headless/overnight agent modifies own config to bypass constraints | Medium |
| 3 | Prompt injection from external content modifies config | High |

## Non-Solutions (Already Tried)

- **Command hook exit 2:** `bypassPermissions` swallows exit code silently. No block.
- **PostToolUse guard:** Fires after the edit. Useless for prevention.
- **Write to /tmp + Bash execute:** Bypasses Edit/Write hooks entirely. Confirmed working bypass.
- **Asymmetric crypto:** Agent has filesystem access, can read its own private key. Self-defeating.
- **CLI --config-file:** Flag does not exist.
- **Nested agent with bypassPermissions to escalate:** Subagents do not have the Agent tool by default. Chain broken.

## What Works

**Prompt hook on PreToolUse matcher `Edit|Write`:** Injected by runtime before tool call evaluates. Fires regardless of permission mode including bypassPermissions. Confirmed working in: direct session, subagent default mode, subagent bypassPermissions mode.

Behavior: model stops, reads authoring guide (CLAUDE.md edits), asks explicit approval, outputs ready-to-run shell command for user to execute instead.

## Remaining Gap

Bash tool is unhooked. Model could write via `cat >`, `sed -i`, `tee`, `python3`. Adding Bash prompt hook costs tokens on every Bash call. Marginal security gain low because: (a) still model-compliance not hard block, (b) subagent escalation chain already broken.

## Decision

Prompt hook on Edit/Write is the right balance. Covers threats 1 and 2. Partially covers 3. Full coverage of threat 3 requires platform sandboxing not available in Claude Code today.

## Permission Modes

| Mode | Behavior | Hook behavior |
|---|---|---|
| `bypassPermissions` | All calls auto-approved | Prompt hooks fire, command exit 2 swallowed |
| `default` | Prompts on sensitive ops | Both hook types work |
| `acceptEdits` | Auto-accepts file edits, prompts Bash | Untested with hooks |
| `plan` | Read-only | N/A |

**Subagent permissions:** Inherit parent hooks. Mode settable per spawn. Do NOT inherit Agent tool by default — prevents privilege escalation chains.

**`--settings` flag:** Merges with global settings.json. `--settings '{"permissions":{"deny":[]}}'` untested for override behavior.

## Next Steps

1. Test `permissions.deny` glob syntax (e.g. `"Edit(~/.claude/**)"`). If working, add as hard runtime enforcement beneath prompt hook.
2. Test whether `--settings` can override global deny rules to enable meta-edit mode.
3. Once deny rules validated, implement three shell aliases: `claude` (default+protected), `claude-meta` (config editing), `claude-sbe` (SBE only).
