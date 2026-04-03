#!/usr/bin/env bash
# File Guard: PreToolUse hook for Edit|Write
# Blocks edits to protected files (CLAUDE.md, .claude/settings.json, agent-os/sbe/).
# Replaces: config-protect.sh, prompt hook, claude-md-guard.sh
# Toggle with: bash ~/.claude/hooks/toggle-protection.sh

PROTECTION_FLAG="$HOME/.claude/hooks/.protection-enabled"

if [ ! -f "$PROTECTION_FLAG" ]; then
  exit 0
fi

# Read tool input from stdin (correct API)
INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', data)
print(ti.get('file_path', ti.get('filePath', '')))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

PROTECTED=false
REASON=""

# Check CLAUDE.md
BASENAME=$(basename "$FILE_PATH")
if [ "$BASENAME" = "CLAUDE.md" ]; then
  PROTECTED=true
  REASON="CLAUDE.md is a protected configuration file"
fi

# Check .claude/settings.json
if echo "$FILE_PATH" | grep -q '\.claude/settings\.json'; then
  PROTECTED=true
  REASON=".claude/settings.json is a protected configuration file"
fi

# Check agent-os/sbe/
if echo "$FILE_PATH" | grep -q 'agent-os/sbe/'; then
  PROTECTED=true
  REASON="Files under agent-os/sbe/ are spec-controlled"
fi

if [ "$PROTECTED" = "true" ]; then
  cat >&2 <<EOF
BLOCKED: $REASON.
File: $FILE_PATH

To proceed:
1. Read ~/.claude/library/context/claude-md-authoring.md for authoring standards
2. Tell the user what you plan to change and provide a ready-to-run shell command (sed or python one-liner with absolute paths) for the user to execute manually
EOF
  exit 2
fi

exit 0
