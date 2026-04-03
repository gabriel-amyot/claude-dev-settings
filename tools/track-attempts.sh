#!/bin/bash

# track-attempts.sh — Sub-agent attempt tracker (3-strike hard cap)
# Tracks sub-agent task attempts in a state JSON file.
# The ralph-loop orchestrator calls this; agents never self-track.
#
# Usage:
#   track-attempts.sh --state-file STATE.json --agent dev-backend --task "fix NPE" --action attempt
#   track-attempts.sh --state-file STATE.json --agent dev-backend --task "fix NPE" --action complete
#   track-attempts.sh --state-file STATE.json --agent dev-backend --task "fix NPE" --action check
#   track-attempts.sh --state-file STATE.json --summary

set -euo pipefail

STATE_FILE=""
AGENT=""
TASK=""
ACTION=""
MAX_ATTEMPTS=3

while [[ $# -gt 0 ]]; do
  case $1 in
    --state-file) STATE_FILE="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --task) TASK="$2"; shift 2 ;;
    --action) ACTION="$2"; shift 2 ;;
    --max) MAX_ATTEMPTS="$2"; shift 2 ;;
    --summary) ACTION="summary"; shift ;;
    --help|-h)
      echo "Usage: track-attempts.sh --state-file FILE --agent NAME --task DESC --action attempt|complete|check"
      echo "       track-attempts.sh --state-file FILE --summary"
      echo ""
      echo "Actions:"
      echo "  attempt  — Increment attempt counter. Returns 'HARD_CAP' if >= $MAX_ATTEMPTS."
      echo "  complete — Mark task as completed."
      echo "  check    — Check if hard cap reached (exit 1 if yes)."
      echo "  summary  — Print per-agent metrics JSON."
      exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$STATE_FILE" ]] || { echo "ERROR: --state-file required" >&2; exit 1; }

# Initialize state file if missing
if [[ ! -f "$STATE_FILE" ]]; then
  echo '{"sub_agent_attempts":{}}' > "$STATE_FILE"
fi

# Generate a stable key from agent+task
KEY="${AGENT}::${TASK}"

case "$ACTION" in
  attempt)
    [[ -n "$AGENT" && -n "$TASK" ]] || { echo "ERROR: --agent and --task required" >&2; exit 1; }
    
    CURRENT=$(jq -r --arg k "$KEY" '.sub_agent_attempts[$k].attempts // 0' "$STATE_FILE")
    NEW=$((CURRENT + 1))
    
    # Update state file
    jq --arg k "$KEY" --arg a "$AGENT" --arg t "$TASK" --argjson n "$NEW" \
      '.sub_agent_attempts[$k] = {agent: $a, task: $t, attempts: $n, status: "in_progress"}' \
      "$STATE_FILE" > "${STATE_FILE}.tmp"
    mv "${STATE_FILE}.tmp" "$STATE_FILE"
    
    if [[ $NEW -ge $MAX_ATTEMPTS ]]; then
      jq --arg k "$KEY" '.sub_agent_attempts[$k].status = "hard_cap_reached"' \
        "$STATE_FILE" > "${STATE_FILE}.tmp"
      mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "HARD_CAP: $AGENT has reached $MAX_ATTEMPTS attempts on '$TASK'. Escalate."
      exit 1
    else
      echo "ATTEMPT $NEW/$MAX_ATTEMPTS for $AGENT on '$TASK'"
    fi
    ;;
    
  complete)
    [[ -n "$AGENT" && -n "$TASK" ]] || { echo "ERROR: --agent and --task required" >&2; exit 1; }
    
    jq --arg k "$KEY" '.sub_agent_attempts[$k].status = "completed"' \
      "$STATE_FILE" > "${STATE_FILE}.tmp"
    mv "${STATE_FILE}.tmp" "$STATE_FILE"
    echo "COMPLETED: $AGENT finished '$TASK'"
    ;;
    
  check)
    [[ -n "$AGENT" && -n "$TASK" ]] || { echo "ERROR: --agent and --task required" >&2; exit 1; }
    
    CURRENT=$(jq -r --arg k "$KEY" '.sub_agent_attempts[$k].attempts // 0' "$STATE_FILE")
    STATUS=$(jq -r --arg k "$KEY" '.sub_agent_attempts[$k].status // "none"' "$STATE_FILE")
    
    if [[ $CURRENT -ge $MAX_ATTEMPTS ]] || [[ "$STATUS" == "hard_cap_reached" ]]; then
      echo "HARD_CAP: $AGENT at $CURRENT/$MAX_ATTEMPTS on '$TASK'"
      exit 1
    else
      echo "OK: $AGENT at $CURRENT/$MAX_ATTEMPTS on '$TASK'"
    fi
    ;;
    
  summary)
    # Produce per-agent metrics for scorecard
    jq '[.sub_agent_attempts | to_entries[] | {
      agent_name: .value.agent,
      tasks_assigned: 1,
      tasks_completed: (if .value.status == "completed" then 1 else 0 end),
      hit_hard_cap: (if .value.status == "hard_cap_reached" then 1 else 0 end)
    }] | group_by(.agent_name) | map({
      agent_name: .[0].agent_name,
      tasks_assigned: (map(.tasks_assigned) | add),
      tasks_completed: (map(.tasks_completed) | add),
      hit_hard_cap: (map(.hit_hard_cap) | add)
    })' "$STATE_FILE"
    ;;
    
  *)
    echo "ERROR: --action must be attempt, complete, check, or use --summary" >&2
    exit 1
    ;;
esac
