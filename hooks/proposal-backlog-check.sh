#!/usr/bin/env bash
# Proposal Backlog Check (SessionStart hook)
# Nudges if: proposals > 5 AND last audit > 7 days ago.
# Non-blocking. Just injects a system message reminder.

PROPOSALS_DIR="$HOME/.claude/skill-proposals"
LAST_AUDIT_FILE="$HOME/.claude/skill-proposals/.last-audit"
THRESHOLD=5
MAX_DAYS=7

# Count pending proposals (only .md files, exclude processed/)
count=0
if [ -d "$PROPOSALS_DIR" ]; then
    count=$(find "$PROPOSALS_DIR" -maxdepth 1 -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
fi

# Skip if under threshold
if [ "$count" -le "$THRESHOLD" ]; then
    exit 0
fi

# Check last audit date
days_since=999
if [ -f "$LAST_AUDIT_FILE" ]; then
    last_epoch=$(date -r "$LAST_AUDIT_FILE" +%s 2>/dev/null || echo 0)
    now_epoch=$(date +%s)
    days_since=$(( (now_epoch - last_epoch) / 86400 ))
fi

# Skip if audited recently
if [ "$days_since" -lt "$MAX_DAYS" ]; then
    exit 0
fi

# Output system message as JSON
python3 -c "
import json
msg = 'PROPOSAL BACKLOG: ${count} skill proposals pending (last audit: ${days_since} days ago). Run /operationalize-audit to review, or /batch-skill-pipeline to build approved ones. Drift risk increases with backlog size.'
print(json.dumps({'systemMessage': msg}))
"
