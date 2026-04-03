#!/usr/bin/env bash
# Session Init: SessionStart hook
# Resets the context-monitor counter at the start of each new session.

MONITOR_DIR="/tmp/claude-context-monitor"

rm -rf "$MONITOR_DIR"
mkdir -p "$MONITOR_DIR"
echo 0 > "$MONITOR_DIR/count"

exit 0
