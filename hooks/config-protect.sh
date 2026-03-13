#!/usr/bin/env bash
# Config Protect: PreToolUse hook for Edit and Write
# Blocks autonomous edits to CLAUDE.md and .claude/settings.json.
# Forces user approval via hook denial (cannot be bypassed by permission mode).

FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('file_path', data.get('filePath', '')))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

BASENAME=$(basename "$FILE_PATH")

# Protected files
PROTECTED=false
case "$BASENAME" in
  CLAUDE.md) PROTECTED=true ;;
  settings.json)
    # Only protect .claude/settings.json, not any settings.json
    echo "$FILE_PATH" | grep -q '\.claude/settings\.json' && PROTECTED=true
    ;;
esac

if [ "$PROTECTED" = "true" ]; then
  echo "BLOCKED: $BASENAME is a protected configuration file."
  echo "Claude cannot edit its own configuration without explicit user approval."
  echo "Review the proposed change and approve or deny it."
  exit 2
fi

exit 0
