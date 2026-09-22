#!/bin/bash
# PostToolUse hook (matcher: Edit|Write): Logs every file modification for post-crawl review.
# Format: timestamp | phase | AC | tool | file_path
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/read-state.sh"

# If harness is not active, skip
is_harness_active 2>/dev/null || exit 0

INPUT="$(cat)"
TOOL_NAME="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")"
FILE_PATH="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")"

[ -z "$FILE_PATH" ] && exit 0

PHASE="$(get_state "phase" || echo "unknown")"
CURRENT_AC="$(get_state "current_ac" || echo "unknown")"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Find the audit log location
if [ -n "$CLAUDE_PROJECT_DIR" ]; then
  LOG_DIR="$CLAUDE_PROJECT_DIR/.claude"
else
  LOG_DIR=".claude"
fi
mkdir -p "$LOG_DIR"

echo "$TIMESTAMP | $PHASE | $CURRENT_AC | $TOOL_NAME | $FILE_PATH" >> "$LOG_DIR/sprint-harness-audit.log"

exit 0
