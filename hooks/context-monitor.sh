#!/usr/bin/env bash
# Context Monitor: PostToolUse hook (no matcher, fires on all tools)
# Tracks tool-call count as a proxy for token usage.
# Warns at configurable thresholds to trigger state persistence and session handoff.

MONITOR_DIR="/tmp/claude-context-monitor"
CONFIG="$HOME/.claude/hooks/context-monitor-config.json"

# Defaults
WARN_THRESHOLD=150
CRITICAL_THRESHOLD=200

# Load config if available
if [ -f "$CONFIG" ]; then
  WARN_THRESHOLD=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('warn_threshold', 150))" 2>/dev/null || echo 150)
  CRITICAL_THRESHOLD=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('critical_threshold', 200))" 2>/dev/null || echo 200)
fi

# Initialize if needed
mkdir -p "$MONITOR_DIR"
if [ ! -f "$MONITOR_DIR/count" ]; then
  echo 0 > "$MONITOR_DIR/count"
fi

# Increment counter
COUNT=$(cat "$MONITOR_DIR/count" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$MONITOR_DIR/count"

# Check thresholds (sentinels prevent repeat warnings)
if [ "$COUNT" -ge "$CRITICAL_THRESHOLD" ] && [ ! -f "$MONITOR_DIR/.critical-sent" ]; then
  touch "$MONITOR_DIR/.critical-sent"
  echo '{"hookSpecificOutput":{"additionalContext":"CRITICAL CONTEXT USAGE (~'"$COUNT"' tool calls). Finish current task. Write handoff summary to SESSION_STATE.md (progress, decisions, remaining work, next tasks for next session). Do not start new tasks. Start a fresh session."}}'
  exit 0
fi

if [ "$COUNT" -ge "$WARN_THRESHOLD" ] && [ ! -f "$MONITOR_DIR/.warn-sent" ]; then
  touch "$MONITOR_DIR/.warn-sent"
  echo '{"hookSpecificOutput":{"additionalContext":"High context usage (~'"$COUNT"' tool calls). If long-running, apply progressive disclosure and persist state at logical boundaries. If mid-task, continue."}}'
  exit 0
fi

exit 0
