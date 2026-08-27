#!/usr/bin/env bash
# CLAUDE.md Tier Lint: PostToolUse hook for Edit and Write.
# CLAUDE.md is the always-on RULE layer. Facts belong in gold library pages, locators in
# silver indexes, raw origins in bronze (_archive/). Warns when an edit leaves an inline
# incident narrative or an unlinked ticket key behind, and when a file grows past its
# high-water mark.
#
# Warn-only, by design. A bad rule in an over-budget file must stay fixable.

LINT="$HOME/.claude-shared-config/tools/claude-md-tier-lint.py"

FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('file_path', data.get('filePath', '')))" 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0
[ "$(basename "$FILE_PATH")" != "CLAUDE.md" ] && exit 0
[ -f "$LINT" ] || exit 0

OUT=$(python3 "$LINT" --file "$FILE_PATH" --hook 2>&1)
if [ -n "$OUT" ]; then
  echo ""
  echo "CLAUDE.MD TIER LINT"
  echo "$OUT"
  echo ""
  echo "Rules stay. Origins go to _archive/ (bronze), lessons to a gold page, and the"
  echo "rule line cites the page. Never block on this; fix when you are next in the file."
fi
exit 0
