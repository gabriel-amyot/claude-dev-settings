#!/bin/bash
# Auto-index hook: flags INDEX.md for refresh when documentation/ or agent-os/ files are modified
# Triggered by PostToolUse on Write/Edit

# Get the modified file path from the tool result
FILE_PATH="$CLAUDE_FILE_PATH"

# Only act on documentation/ or agent-os/ paths
if [[ "$FILE_PATH" != *"/documentation/"* && "$FILE_PATH" != *"/agent-os/"* ]]; then
    exit 0
fi

# Skip if the modified file IS an INDEX.md (avoid infinite loop)
if [[ "$(basename "$FILE_PATH")" == "INDEX.md" ]]; then
    exit 0
fi

# Find the nearest parent directory containing an INDEX.md
DIR="$(dirname "$FILE_PATH")"
while [[ "$DIR" != "/" && "$DIR" != "." ]]; do
    if [[ -f "$DIR/INDEX.md" ]]; then
        # Touch a stale marker so the next /index-context invocation knows what to refresh
        touch "$DIR/.index-stale"
        echo "Auto-index: flagged $DIR/INDEX.md as stale"
        exit 0
    fi
    DIR="$(dirname "$DIR")"
done

# No INDEX.md found in parents — flag the immediate parent
DIR="$(dirname "$FILE_PATH")"
touch "$DIR/.index-stale"
echo "Auto-index: flagged $DIR for INDEX.md creation"
