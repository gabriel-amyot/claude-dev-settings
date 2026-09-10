#!/usr/bin/env bash
# Wayfinder Close Guard: PreToolUse hook for Bash. WARN ONLY, never blocks.
#
# WHY
#     A wayfinder ticket is resolved by posting an answer comment and closing the
#     issue. `wayfinder_runs.py resolve` does both AND appends the run trailer that
#     makes the session traceable, so the wayfinder spec can be improved from
#     evidence. A bare `gh issue close` does the work and loses the evidence.
#     `harvest` will later report that ticket as a GAP, but by then the session
#     that knew what happened is gone. This nudge fires at the only moment the
#     information still exists.
#
# WHAT IT IS NOT
#     Not a wall. It cannot see a close made in the GitHub web UI, through
#     `gh api --method PATCH`, from another machine, or from any tool other than
#     Bash. It deliberately makes NO network call, so it also cannot know whether
#     the issue carries a wayfinder label or already has a trailer — it matches on
#     the command string alone and accepts the resulting false positives (a
#     non-wayfinder issue in the same repo gets the same reminder).
#     A hook that does not fire is not permission. `harvest` is the detector.
#
# SCOPE
#     `gh issue close` naming gabriel-amyot/klever-project-management. Nothing else.
#
# KILL SWITCHES
#     export WAYFINDER_CLOSE_GUARD_OFF=1
#     touch ~/.claude/.wayfinder-close-guard-off
#
# Exit 0 always. Stdout is shown to the agent. FAILS OPEN on any internal error.

[ -n "$WAYFINDER_CLOSE_GUARD_OFF" ] && exit 0
[ -f "$HOME/.claude/.wayfinder-close-guard-off" ] && exit 0

input="$(cat)"
[ -z "$input" ] && exit 0

hit="$(printf '%s' "$input" | python3 -c '
import json, re, sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

ti = data.get("tool_input") or data
cmd = ti.get("command") or ""
if "gh" not in cmd or "klever-project-management" not in cmd:
    sys.exit(0)

# `gh issue close <n>` with the wayfinder tracker named anywhere in the same
# command word run. Order-insensitive: --repo may precede or follow the number.
close = re.compile(r"\bgh\s+(?:--\S+\s+)*issue\s+close\b")
repo = re.compile(r"gabriel-amyot/klever-project-management")

for segment in re.split(r"&&|\|\||;|\n", cmd):
    if close.search(segment) and repo.search(segment):
        m = re.search(r"\bissue\s+close\s+(?:--\S+(?:[= ]\S+)?\s+)*(\d+)", segment)
        print(m.group(1) if m else "?")
        break
' 2>/dev/null)"

[ -z "$hit" ] && exit 0

cat <<EOF

WAYFINDER CLOSE GUARD: closing #${hit} directly leaves the run untraced.

If this is a wayfinder ticket, resolve it through the tool instead, which posts the
answer, appends the run trailer, and closes the issue in one step:

  python3 ~/.claude-shared-config/skills/wayfinder/tools/wayfinder_runs.py resolve \\
      --ticket ${hit} --body-file <answer.md> --outcome resolved \\
      [--friction spec-wrong:"what in SKILL.md was actually incorrect"]

A bare close is not blocked and sometimes correct (an issue that is not a wayfinder
ticket, or one being withdrawn rather than resolved). It will show up as a GAP in
\`wayfinder_runs.py harvest\`, which is the record that this run was never traced.
EOF

exit 0
