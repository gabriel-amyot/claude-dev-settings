#!/usr/bin/env bash
# Git Pipe Guard: PreToolUse hook for Bash.
#
# A shell pipe reports the LAST command's exit status, so `git push | tee log` looks
# successful even when the push failed. That turns a failed mutation into a false
# "done" conclusion. Read-only queries are unaffected: `git log | head` is fine.
#
# Replaces the old blanket "never pipe git commands" rule, which was measured as
# violated in 431 of 1,642 sessions with no demonstrable harm, and whose stated
# example (`git fetch && git status`) prohibited chaining rather than piping.
#
# Scope: only a MUTATING git subcommand followed by a pipe. Warn-only.
# Promote to blocking once observed with no false positives.

FILE_INPUT=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get('command', ''))" 2>/dev/null)

[ -z "$FILE_INPUT" ] && exit 0

HIT=$(printf '%s' "$FILE_INPUT" | python3 -c "
import re, sys
cmd = sys.stdin.read()
MUT = r'push|commit|tag|fetch|pull|merge|rebase|reset|revert|cherry-pick|am|apply|stash|clean|worktree\s+add|remote\s+(add|remove|set-url)|config'
# git as a real command word, a mutating subcommand, then a pipe before any separator.
pat = re.compile(r'(?:^|\||&&|;|\bthen\b|\bdo\b)\s*(?:sudo\s+)?git\s+(?:-C\s+\S+\s+|--\S+\s+)*(' + MUT + r')\b[^|&;\n]*\|')
m = pat.search(cmd)
if m:
    print(m.group(1))
" 2>/dev/null)

[ -z "$HIT" ] && exit 0

echo ""
echo "GIT PIPE GUARD: a piped \`git $HIT\` hides its own failure."
echo "A pipe reports the LAST command's exit status, so this reads as success even if"
echo "\`git $HIT\` fails. Run the mutation unpiped, then inspect the result separately."
echo "Read-only queries (log, diff, status, show) may be piped freely."
echo ""
exit 0
