#!/usr/bin/env bash
# AGENTS.md Mirror — SessionStart resync.
#
# The PostToolUse mirror only fires on Edit|Write. A CLAUDE.md changed by Bash, by
# `git checkout`/`pull`, or by an external editor leaves AGENTS.md stale, and a tool that
# reads only AGENTS.md would then operate under superseded rules. Resync once per session
# so staleness cannot outlive a restart.
#
# Silent when already current. Never blocks.

SYNC="$HOME/.claude-shared-config/tools/sync-agents-md.py"
[ -f "$SYNC" ] || exit 0

OUT=$(python3 "$SYNC" --hook 2>&1)
RC=$?

if [ $RC -eq 2 ]; then
  echo "AGENTS.MD MIRROR: refused to overwrite a hand-written AGENTS.md."
  echo "$OUT"
elif [ -n "$OUT" ]; then
  echo "AGENTS.MD MIRROR: resynced a stale mirror at session start."
  echo "$OUT"
fi
exit 0
