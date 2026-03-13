#!/usr/bin/env bash
# CLAUDE.md Authoring Guard: PostToolUse hook for Edit and Write
# When a CLAUDE.md file is being edited, injects authoring standards as context.

FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('file_path', data.get('filePath', '')))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Only trigger on CLAUDE.md files
BASENAME=$(basename "$FILE_PATH")
if [ "$BASENAME" != "CLAUDE.md" ]; then
  exit 0
fi

STANDARDS="$HOME/.claude/context/claude-md-authoring.md"
if [ -f "$STANDARDS" ]; then
  echo ""
  echo "CLAUDE.MD GUARD: You just edited a CLAUDE.md file."
  echo "Review your change against these standards before proceeding:"
  echo ""
  cat "$STANDARDS"
  echo ""
fi
