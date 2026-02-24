#!/bin/bash
# Update Claude Code usage cache
# This runs BEFORE a Claude Code session starts to capture usage data

CACHE_FILE="$HOME/.claude/usage-cache.json"
CACHE_DIR="$(dirname "$CACHE_FILE")"

# Create cache directory if it doesn't exist
mkdir -p "$CACHE_DIR"

# Capture usage data
# Note: This runs outside of a Claude Code session, so it can execute claude commands
if command -v claude &> /dev/null; then
    USAGE_OUTPUT=$(claude usage 2>&1)

    # Extract key information using regex
    # Example output: "Current week: 24% used | Resets Feb 21 at 10am America/Toronto"

    if echo "$USAGE_OUTPUT" | grep -q "Current week"; then
        # Parse the usage percentage
        USAGE_PCT=$(echo "$USAGE_OUTPUT" | grep -oE '[0-9]+%' | head -1 | tr -d '%')

        # Parse reset date/time
        RESET_INFO=$(echo "$USAGE_OUTPUT" | grep -oE 'Resets.*$' | sed 's/Resets //')

        # Create JSON cache
        cat > "$CACHE_FILE" << EOF
{
  "usage_percent": ${USAGE_PCT:-0},
  "reset_info": "${RESET_INFO:-unknown}",
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "raw_output": $(echo "$USAGE_OUTPUT" | jq -Rs .)
}
EOF
    else
        # Fallback if parsing fails - just save raw output
        cat > "$CACHE_FILE" << EOF
{
  "usage_percent": 0,
  "reset_info": "unknown",
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "raw_output": $(echo "$USAGE_OUTPUT" | jq -Rs .)
}
EOF
    fi
fi
