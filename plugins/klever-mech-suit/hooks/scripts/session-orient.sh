#!/usr/bin/env bash
# Session orientation hook: reads MY_CONTEXT.md header + last session-log entry.
# Outputs 2-3 lines of context for Claude at session start.

set -euo pipefail

CONTEXT_FILE="MY_CONTEXT.md"
SESSION_LOG="notes/session-log.md"

# If no MY_CONTEXT.md, suggest setup
if [[ ! -f "$CONTEXT_FILE" ]]; then
  echo "No MY_CONTEXT.md found. Say 'help me set up my hivemind' to get started."
  exit 0
fi

# Extract name and role from header (first two comment lines)
NAME=$(head -5 "$CONTEXT_FILE" | grep '^#' | head -1 | sed 's/^# //')
BRANCHES=$(grep -c '^>' "$CONTEXT_FILE" 2>/dev/null || echo "0")

OUTPUT="Workspace: ${NAME}. Hivemind: ${BRANCHES} branches."

# Last session-log entry
if [[ -f "$SESSION_LOG" ]]; then
  LAST_ENTRY=$(grep -v '^#' "$SESSION_LOG" | grep -v '^\s*$' | tail -1)
  if [[ -n "$LAST_ENTRY" ]]; then
    OUTPUT="${OUTPUT} Last session: ${LAST_ENTRY}"
  fi
fi

echo "$OUTPUT"
