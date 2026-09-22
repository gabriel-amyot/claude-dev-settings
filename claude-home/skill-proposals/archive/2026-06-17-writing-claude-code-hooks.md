# Skill Proposal: writing-claude-code-hooks
Date: 2026-06-17
Source: Session steady-mole — building pm-single-trunk-guard.sh PreToolUse hook

## Trigger
When creating or debugging a Claude Code hook (PreToolUse/PostToolUse/SessionStart guard scripts under `~/.claude/hooks/`), especially Bash-matcher guards that inspect `tool_input`.

## Scope
global (cross-org — these are Claude Code platform mechanics, not Klever-specific)

## Draft Steps
1. Read input from stdin as JSON; extract via env-var + `python3 -c`, NEVER `python3 - <<HEREDOC` with a piped payload (heredoc consumes the `-` program slot; piped stdin is lost).
2. Fail OPEN on parse error for defense-in-depth guards (`exit 0`); fail closed only for security gates.
3. To BLOCK: write the human reason to **stderr**, then `exit 2`. stdout-on-exit-2 shows "No stderr output" and hides the reason.
4. Never substring-match a shell command to detect an invocation. Split on `&&|\|\||;|\||\n|$(|backtick`, then only treat a segment as a real invocation if it starts with the binary name after `lstrip(" \t(")`. Document the residual false-positive (quoted args).
5. Test the hook from a **script file** (`bash test.sh`) so the harness's embedded trigger strings don't trip the guard via the outer command the hook sees.
6. Scope by target repo: parse `git -C <path>` for the real target; fall back to the hook's `cwd`.
