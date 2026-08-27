#!/usr/bin/env bash
# AGENTS.md Mirror: PostToolUse hook for Edit and Write.
# When a mirrored CLAUDE.md changes, regenerate its sibling AGENTS.md so Codex,
# Cursor, Copilot and Gemini CLI stay on the same rules as Claude Code.
#
# Source of truth is CLAUDE.md. AGENTS.md is generated and must never be hand-edited.
# Mirror pairs live in the SYNC script, not here.

SYNC="$HOME/.claude-shared-config/tools/sync-agents-md.py"

FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('file_path', data.get('filePath', '')))" 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0
[ "$(basename "$FILE_PATH")" != "CLAUDE.md" ] && exit 0
[ -f "$SYNC" ] || exit 0

OUT=$(python3 "$SYNC" --hook 2>&1)
RC=$?

if [ $RC -eq 2 ]; then
  echo ""
  echo "AGENTS.MD MIRROR: refused to overwrite a hand-written AGENTS.md."
  echo "$OUT"
  echo "Resolve before relying on the mirror."
  exit 0
fi

if [ -n "$OUT" ]; then
  echo ""
  echo "AGENTS.MD MIRROR: regenerated from your CLAUDE.md edit."
  echo "$OUT"
fi

exit 0
