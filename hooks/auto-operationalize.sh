#!/usr/bin/env bash
# Auto-operationalize: inject tribal knowledge capture instructions before Stop/PreCompact.
# Pattern: same as pre-compact-guard.sh — outputs additionalContext for Claude to act on.

PROMPT_FILE="$HOME/.claude/hooks/auto-operationalize-prompt.md"
CAPTURE_DIR="$HOME/.claude/knowledge-capture"
PROPOSALS_DIR="$HOME/.claude/skill-proposals"

mkdir -p "$CAPTURE_DIR" "$PROPOSALS_DIR"

if [ ! -f "$PROMPT_FILE" ]; then
    exit 0
fi

PROMPT=$(cat "$PROMPT_FILE")
PROMPT=$(echo "$PROMPT" | sed "s|{CAPTURE_DIR}|$CAPTURE_DIR|g; s|{PROPOSALS_DIR}|$PROPOSALS_DIR|g")

python3 -c "
import json, sys
prompt = sys.stdin.read()
print(json.dumps({'hookSpecificOutput': {'additionalContext': prompt}}))" <<< "$PROMPT"
