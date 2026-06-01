#!/usr/bin/env bash
# Screenshot Placement Guard: PostToolUse hook for Playwright MCP screenshots
# Warns the agent when a screenshot lands at the repo root (bare filename).
# Does NOT block — just injects advisory context.
#
# Trigger: mcp__plugin_playwright_playwright__browser_take_screenshot
# RCA: general/housekeeping/2026-05-25-dexter-screenshot-rca-report.md

INPUT=$(cat)

# Extract the screenshot path from tool_input (the 'name' parameter)
SCREENSHOT_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', {})
print(ti.get('name', ti.get('fileName', '')))" 2>/dev/null)

if [ -z "$SCREENSHOT_NAME" ]; then
  exit 0
fi

# Check if the name has a directory component
case "$SCREENSHOT_NAME" in
  tickets/*|*/screenshots/*)
    # Has a proper ticket-relative path — good placement
    exit 0
    ;;
  */*)
    # Has some directory component — probably OK
    exit 0
    ;;
  *)
    # Bare filename — will land at CWD (project-management root)
    MSG="SCREENSHOT PLACEMENT WARNING: '$SCREENSHOT_NAME' has no directory path and will land at the repo root (project-management/).

Per CLAUDE.md, Playwright MCP screenshots must use the full relative path:
  tickets/{PREFIX}/{EPIC}/{TICKET}/design/screenshots/{filename}.png

Fix: mkdir -p the target directory, then mv $SCREENSHOT_NAME to the correct location.
Preferred: Use agent-browser CLI with --screenshot-dir for simple captures."

    echo "{\"hookSpecificOutput\":{\"additionalContext\":\"$MSG\"}}" | python3 -c "
import sys, json
raw = sys.stdin.read()
# Re-encode to ensure valid JSON (handles newlines in the message)
data = json.loads(raw)
print(json.dumps(data))" 2>/dev/null || \
    python3 -c "
import sys, json
msg = '''$MSG'''
print(json.dumps({'hookSpecificOutput': {'additionalContext': msg}}))"
    ;;
esac
