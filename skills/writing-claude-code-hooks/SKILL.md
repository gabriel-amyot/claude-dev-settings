---
name: writing-claude-code-hooks
description: Write or debug a Claude Code hook — PreToolUse, PostToolUse, SessionStart, PreCompact, UserPromptSubmit guard scripts under ~/.claude/hooks/. Use when a hook must block a tool call, when a guard fires on the wrong input or fails to fire at all, when a block reason reaches the agent as "No stderr output", or when adding a matcher to settings.json. Covers stdin JSON extraction, exit codes, command-splitting for Bash matchers, and testing a guard without tripping it.
nav:
  bay: ops
  when: "Building or fixing a hook under ~/.claude/hooks/; a guard misfires, fails silently, or blocks the wrong thing."
  when_not: "Writing a skill (use write-a-skill). Editing settings.json permissions only (use update-config)."
---

# Writing Claude Code Hooks

Hooks are the mechanical layer under the prose rules. A rule in CLAUDE.md is followed most of the time; a hook is followed every time. That is the whole reason to write one, and it is also why a broken hook is worse than no hook — it reads as enforcement while enforcing nothing.

Everything below was learned by getting it wrong in this harness. Twenty-six hooks are live under `~/.claude/hooks/`; read a working one before writing a new one.

## The five mistakes that actually happen

### 1. Reading stdin with a heredoc — the payload vanishes

The hook receives its JSON payload on stdin. This looks reasonable and silently fails:

```bash
python3 - <<'PYEOF'      # WRONG
import json, sys
data = json.load(sys.stdin)
PYEOF
```

The heredoc occupies the `-` program slot, so the piped payload is gone and `json.load` reads the script text. Capture stdin in the shell first, then hand it over through the environment:

```bash
INPUT=$(cat)
RESULT=$(CLAUDE_HOOK_INPUT="$INPUT" python3 -c '
import os, json
raw = os.environ.get("CLAUDE_HOOK_INPUT", "")
data = json.loads(raw) if raw else {}
tool = data.get("tool_name", "")
cmd  = data.get("tool_input", {}).get("command", "")
')
```

`pm-single-trunk-guard.sh` is the reference implementation of this pattern.

### 2. Writing the block reason to stdout

**On `exit 2`, only stderr reaches the agent.** Write the reason with `echo` and the agent sees a block with the message `No stderr output` — it knows it was stopped but not why, so it retries the same call or invents a workaround.

```bash
echo "BLOCKED: reason"   >&2    # correct
exit 2
```

From Python inside the hook, `sys.stderr.write(...)` then `sys.exit(2)`. `library-stamp-guard.sh` does this correctly.

Two live hooks currently get this wrong — `config-protect.sh` and `worktree-guard.sh` both `echo` to stdout before `exit 2`. If you touch either, fix the redirect.

### 3. Substring-matching a command

Never decide a command invokes something by searching the whole string. `rm` matches `charm`, and a guard string quoted inside an unrelated argument trips the guard. Split first, then check the head of each segment:

```python
import re
segments = re.split(r'&&|\|\||;|\||\n|\$\(|`', cmd)
def invokes(binary, segs):
    return any(s.lstrip(" \t(").startswith(binary) for s in segs)
```

Residual false positive: a segment that begins with the binary name inside a quoted argument. Document it in the hook header rather than pretending it is airtight.

This session hit the cost of getting it wrong from the other side. `file-guard.sh` blocked a legitimate `mv` because the *rationale text* in the same command mentioned a protected filename. The fix was to split the write and the move into separate calls, but a narrower matcher would not have fired at all.

### 4. Failing closed on a defense-in-depth guard

Decide which kind of guard you are writing:

| Guard kind | On parse error or unexpected input |
|---|---|
| Defense-in-depth backstop for a prose rule | `exit 0` — fail **open**. A malformed payload must not halt unrelated work. |
| Security or data-loss gate | fail **closed**. Blocking wrongly beats permitting wrongly. |

Most hooks here are the first kind. The prose rule is the primary discipline; the hook catches what slips.

### 5. Testing the hook by typing the trigger

If you test by running a command that contains the trigger string, the harness's own tool call carries that string and the guard fires on your test rather than on the case under test. Put the case in a file and run the file:

```bash
cat > /tmp/hook-test.sh <<'EOF'
echo '{"tool_name":"Bash","tool_input":{"command":"git checkout -b x"}}' \
  | bash ~/.claude/hooks/my-guard.sh
echo "exit=$?"
EOF
bash /tmp/hook-test.sh
```

Assert on the exit code, and assert the reason appears on stderr. A guard that returns 2 with an empty stderr passes a naive test and fails in production.

## Scoping to the right target

A hook sees the tool call, not your intent. For repo-scoped rules, parse the real target out of the command rather than trusting the working directory:

```python
m = re.search(r'git\s+-C\s+(\S+)', cmd)
target = m.group(1) if m else data.get("cwd", "")
```

Otherwise a guard meant for one repo fires in every repo.

## Wiring it up

Add the matcher to `settings.json` under the right event. The matcher selects which tool calls reach the hook — keep it as narrow as the rule requires, because every call that reaches a hook pays its startup cost.

```json
{ "hooks": { "PreToolUse": [
  { "matcher": "Edit|Write",
    "hooks": [{ "type": "command", "command": "~/.claude/hooks/my-guard.sh" }] }
]}}
```

A hook that is written but never registered is the most common false sense of safety. After adding it, trigger the real condition once and confirm the block.

## Checklist

- [ ] `INPUT=$(cat)`, then env-var into `python3 -c`. No heredoc on the payload path.
- [ ] Block reason on **stderr**, `exit 2`.
- [ ] Command split before matching; no bare substring test.
- [ ] Fail open unless it is a security gate.
- [ ] Registered in `settings.json` with the narrowest matcher that works.
- [ ] Tested from a script file; asserted on exit code **and** stderr content.
- [ ] Header comment states the block condition and the known false positive.
