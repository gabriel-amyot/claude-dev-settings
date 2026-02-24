#!/bin/bash
#===============================================================================
# Work Assistant - Claude Code Exit Hook
#
# This hook flushes all org-specific session files to their respective vaults
# when Claude Code exits.
#===============================================================================

LOG_FILE="/tmp/work-assistant-exit-hook.log"
echo "[$(date)] Work Assistant exit hook triggered" >> "$LOG_FILE"

ORG_REGISTRY="$HOME/.work-assistant/org-registry.yaml"

if [ ! -f "$ORG_REGISTRY" ]; then
    echo "[$(date)] No org registry found, skipping" >> "$LOG_FILE"
    exit 0
fi

# Parse YAML and flush each org's session
while IFS=: read -r org vault_path; do
    # Skip comments and empty lines
    [[ "$org" =~ ^#.*$ || -z "$org" ]] && continue

    # Clean up values (remove quotes and whitespace)
    org=$(echo "$org" | xargs)
    vault_path=$(echo "$vault_path" | xargs | sed 's/"//g' | sed "s/'//g")

    # Skip if not a valid org entry
    [[ -z "$org" || -z "$vault_path" ]] && continue

    # Session file for this org
    SESSION_FILE="$HOME/.work-assistant/session-summary-${org}-$(date +%Y-%m-%d).txt"

    if [ -f "$SESSION_FILE" ] && [ -s "$SESSION_FILE" ]; then
        echo "[$(date)] Flushing session for org: $org" >> "$LOG_FILE"

        # Call update-daily-notes.sh for each line
        while IFS= read -r line; do
            if [ -n "$line" ]; then
                VAULT_PATH="$vault_path" \
                ORG_CONTEXT="$org" \
                "$HOME/work-assistant/bin/update-daily-notes.sh" "$line" >> "$LOG_FILE" 2>&1
            fi
        done < "$SESSION_FILE"

        # Mark as processed
        mv "$SESSION_FILE" "${SESSION_FILE}.processed"
        echo "[$(date)] Session flushed for $org" >> "$LOG_FILE"
    fi
done < "$ORG_REGISTRY"

echo "[$(date)] Exit hook completed" >> "$LOG_FILE"
