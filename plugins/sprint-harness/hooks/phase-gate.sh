#!/bin/bash
# PreToolUse hook: Enforces phase-based tool constraints.
# Reads sprint-harness-state.yaml, checks phase + tool against constraint matrix.
# Exit 0 = allow, Exit 2 = block (hard deny).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/read-state.sh"

# If harness is not active, allow everything
is_harness_active 2>/dev/null || exit 0

INPUT="$(cat)"
TOOL_NAME="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")"
TOOL_INPUT="$(echo "$INPUT" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('tool_input',{})))" 2>/dev/null || echo "{}")"

[ -z "$TOOL_NAME" ] && exit 0

PHASE="$(get_state "phase")"
[ -z "$PHASE" ] && exit 0

# Extract file path from tool input (for Edit/Write)
FILE_PATH="$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null || echo "")"

# Extract command from Bash tool input
BASH_CMD="$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('command',''))" 2>/dev/null || echo "")"

# Always block protected paths (any phase)
if [ -n "$FILE_PATH" ]; then
  while IFS= read -r protected; do
    [ -z "$protected" ] && continue
    if echo "$FILE_PATH" | grep -qF "$protected"; then
      echo "HARNESS BLOCKED: $FILE_PATH is a protected path ($protected). Cannot modify in any phase." >&2
      exit 2
    fi
  done < <(get_state_list "protected_paths")
fi

# Get ticket folder for reports/ exception
TICKET="$(get_state "ticket")"
REPORTS_PATH="tickets/${TICKET}/reports/"

# Phase constraint matrix
case "$PHASE" in
  spec-gate)
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
      # Allow writes to reports/status/ only
      if [ -n "$FILE_PATH" ] && echo "$FILE_PATH" | grep -q "reports/status/"; then
        exit 0
      fi
      echo "HARNESS BLOCKED: Phase 'spec-gate' does not allow $TOOL_NAME. Only Read/Grep/Glob/Agent(Explore) and writes to reports/status/ are permitted." >&2
      exit 2
    fi
    if [ "$TOOL_NAME" = "Bash" ]; then
      # Block destructive commands
      if echo "$BASH_CMD" | grep -qE '(git (push|commit|add|checkout|merge|rebase)|rm |mv |cp .*>|npm |yarn |mvn |gradle)'; then
        echo "HARNESS BLOCKED: Phase 'spec-gate' only allows read-only bash commands. Blocked: $BASH_CMD" >&2
        exit 2
      fi
    fi
    ;;

  context-gate)
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
      # Allow writes to reports/status/ only
      if [ -n "$FILE_PATH" ] && echo "$FILE_PATH" | grep -q "reports/status/"; then
        exit 0
      fi
      echo "HARNESS BLOCKED: Phase 'context-gate' does not allow $TOOL_NAME except to reports/status/." >&2
      exit 2
    fi
    if [ "$TOOL_NAME" = "Bash" ]; then
      # Allow git fetch, gcloud auth, read-only commands
      if echo "$BASH_CMD" | grep -qE '(git (push|commit|add|checkout|merge|rebase)|rm |mv |npm |yarn |mvn |gradle)'; then
        # But allow git fetch
        if ! echo "$BASH_CMD" | grep -qE '^git fetch'; then
          echo "HARNESS BLOCKED: Phase 'context-gate' only allows read-only bash, git fetch, gcloud auth. Blocked: $BASH_CMD" >&2
          exit 2
        fi
      fi
    fi
    ;;

  planning)
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
      # Allow writes to reports/ only
      if [ -n "$FILE_PATH" ] && echo "$FILE_PATH" | grep -q "$REPORTS_PATH"; then
        exit 0
      fi
      echo "HARNESS BLOCKED: Phase 'planning' only allows writes to $REPORTS_PATH. Cannot write to: $FILE_PATH" >&2
      exit 2
    fi
    if [ "$TOOL_NAME" = "Bash" ]; then
      # Block destructive commands
      if echo "$BASH_CMD" | grep -qE '(git (push|commit|add)|rm -rf|mvn |gradle )'; then
        echo "HARNESS BLOCKED: Phase 'planning' does not allow destructive bash commands. Blocked: $BASH_CMD" >&2
        exit 2
      fi
    fi
    ;;

  implementation)
    # All tools allowed except protected paths (checked above)
    exit 0
    ;;

  review)
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
      echo "HARNESS BLOCKED: Phase 'review' does not allow file writes. Complete the review first, then advance to fix issues." >&2
      exit 2
    fi
    if [ "$TOOL_NAME" = "Bash" ]; then
      # Allow test commands and read-only
      if echo "$BASH_CMD" | grep -qE '(git (push|commit|add|checkout|merge)|rm |mv |Edit|Write)'; then
        echo "HARNESS BLOCKED: Phase 'review' only allows read-only bash and test commands." >&2
        exit 2
      fi
    fi
    ;;

  verification)
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
      # Allow only ac.yaml and reports/ updates
      if [ -n "$FILE_PATH" ]; then
        if echo "$FILE_PATH" | grep -qE '(ac\.yaml|reports/)'; then
          exit 0
        fi
      fi
      echo "HARNESS BLOCKED: Phase 'verification' only allows writes to ac.yaml and reports/. Cannot write to: $FILE_PATH" >&2
      exit 2
    fi
    ;;

  ship)
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
      echo "HARNESS BLOCKED: Phase 'ship' does not allow file edits. Only git operations (commit, push) are allowed." >&2
      exit 2
    fi
    # Bash: allow git commands only
    if [ "$TOOL_NAME" = "Bash" ]; then
      if ! echo "$BASH_CMD" | grep -qE '^git '; then
        echo "HARNESS BLOCKED: Phase 'ship' only allows git commands. Blocked: $BASH_CMD" >&2
        exit 2
      fi
    fi
    ;;

  done)
    if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Bash" ]; then
      echo "HARNESS BLOCKED: Phase 'done'. All modifications blocked. Use '/harness ac' to start next AC or '/harness reset' to disable harness." >&2
      exit 2
    fi
    ;;
esac

exit 0
