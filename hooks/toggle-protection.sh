#!/usr/bin/env bash
# Toggle protection hooks on/off
# Controls: CLAUDE.md, .claude/settings.json, agent-os/sbe/ file edits

PROTECTION_FLAG="$HOME/.claude/hooks/.protection-enabled"

if [ -f "$PROTECTION_FLAG" ]; then
    rm "$PROTECTION_FLAG"
    echo "Protection DISABLED (CLAUDE.md, settings.json, agent-os/sbe/ edits allowed)"
else
    touch "$PROTECTION_FLAG"
    echo "Protection ENABLED (CLAUDE.md, settings.json, agent-os/sbe/ edits blocked)"
fi
