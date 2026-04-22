#!/usr/bin/env bash
# Auto-operationalize (PreCompact): inject tribal knowledge capture instructions as systemMessage.
# Writes to the org's bibliotheque inbox (same destination as /operationalize skill).
# Falls back to ~/.claude/knowledge-capture/ for personal/undetected sessions.

PROMPT_FILE="$HOME/.claude/hooks/auto-operationalize-prompt.md"
PROPOSALS_DIR="$HOME/.claude/skill-proposals"

# Detect org bibliotheque inbox from $PWD (longest-prefix match)
INBOX_DIR=$(python3 -c "
import os
cwd = os.getcwd()
orgs = {
    os.path.expanduser('~/Developer/grp-beklever-com'): os.path.expanduser('~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/inbox'),
    os.path.expanduser('~/Developer/supervisr-ai'):     os.path.expanduser('~/Developer/supervisr-ai/project-management/documentation/bibliotheque/inbox'),
}
best, best_len = None, 0
for path, inbox in orgs.items():
    if cwd.startswith(path) and len(path) > best_len:
        best, best_len = inbox, len(path)
print(best or os.path.expanduser('~/.claude/knowledge-capture'))
")

mkdir -p "$INBOX_DIR" "$PROPOSALS_DIR"

if [ ! -f "$PROMPT_FILE" ]; then
    exit 0
fi

PROMPT=$(cat "$PROMPT_FILE")
PROMPT=$(echo "$PROMPT" | sed "s|{INBOX_DIR}|$INBOX_DIR|g; s|{PROPOSALS_DIR}|$PROPOSALS_DIR|g")

python3 -c "
import json, sys
prompt = sys.stdin.read()
print(json.dumps({'systemMessage': prompt}))" <<< "$PROMPT"
