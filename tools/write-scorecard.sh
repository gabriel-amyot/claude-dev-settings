#!/bin/bash

# write-scorecard.sh — Deterministic scorecard writer
# Validates a JSON payload against the scorecard schema and safely appends to the scorecard YAML.
# Agents produce JSON; this script validates and writes. Agents never touch the YAML file directly.
#
# Usage: echo '{"schema_version":"1.0",...}' | write-scorecard.sh
#    or: write-scorecard.sh --file payload.json

set -euo pipefail

SCORECARD_FILE="${HOME}/.claude/harness-scorecard.yaml"
LOCK_FILE="${SCORECARD_FILE}.lockdir"

INPUT_FILE=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --file) INPUT_FILE="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: echo '{json}' | write-scorecard.sh"
      echo "       write-scorecard.sh --file payload.json"
      echo "Validates and appends a scorecard entry to: $SCORECARD_FILE"
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -n "$INPUT_FILE" ]]; then
  [[ -f "$INPUT_FILE" ]] || { echo "ERROR: File not found: $INPUT_FILE" >&2; exit 1; }
  RAW_INPUT=$(cat "$INPUT_FILE")
else
  RAW_INPUT=$(cat)
fi

[[ -n "$RAW_INPUT" ]] || { echo "ERROR: Empty input." >&2; exit 1; }

# Strip markdown wrapping (agents often wrap in code fences)
CLEANED=$(echo "$RAW_INPUT" | sed 's/^```json//; s/^```//; s/```$//; /^[[:space:]]*$/d' | tr '\n' ' ')
JSON_PAYLOAD=$(echo "$CLEANED" | perl -ne 'if (/(\{.*\})/) { print $1; exit }')
[[ -n "$JSON_PAYLOAD" ]] || { echo "ERROR: Could not extract JSON object." >&2; exit 1; }
echo "$JSON_PAYLOAD" | jq empty 2>/dev/null || { echo "ERROR: Invalid JSON syntax." >&2; exit 1; }

# Validate required fields
ERRORS=""
SV=$(echo "$JSON_PAYLOAD" | jq -r '.schema_version // empty')
[[ "$SV" == "1.0" ]] || ERRORS="${ERRORS}  - schema_version must be '1.0', got '${SV}'\n"

for field in date crawl_type ticket exit_reason; do
  val=$(echo "$JSON_PAYLOAD" | jq -r ".$field // empty")
  [[ -n "$val" ]] || ERRORS="${ERRORS}  - Missing required field: $field\n"
done

for field in crawl_number iterations_used iterations_budget wall_time_minutes; do
  val=$(echo "$JSON_PAYLOAD" | jq -r ".$field // empty")
  [[ -n "$val" ]] || { ERRORS="${ERRORS}  - Missing required field: $field\n"; continue; }
  [[ "$val" =~ ^[0-9]+$ ]] || ERRORS="${ERRORS}  - Field $field must be integer, got '$val'\n"
done

PASS=$(echo "$JSON_PAYLOAD" | jq -r '.gate_results.pass // empty')
FAIL_COUNT=$(echo "$JSON_PAYLOAD" | jq -r '.gate_results.fail // empty')
[[ -n "$PASS" && -n "$FAIL_COUNT" ]] || ERRORS="${ERRORS}  - gate_results must have 'pass' and 'fail'\n"

ER=$(echo "$JSON_PAYLOAD" | jq -r '.exit_reason // empty')
if [[ -n "$ER" ]]; then
  case "$ER" in success|budget_exhausted|blocked|aborted) ;; *)
    ERRORS="${ERRORS}  - exit_reason invalid: '$ER'\n" ;; esac
fi

CT=$(echo "$JSON_PAYLOAD" | jq -r '.crawl_type // empty')
if [[ -n "$CT" ]]; then
  case "$CT" in night-crawl|dev-crawl|ralph-loop|supervisr-autopilot|bmad-party) ;; *)
    ERRORS="${ERRORS}  - crawl_type invalid: '$CT'\n" ;; esac
fi

if [[ -n "$ERRORS" ]]; then
  echo "ERROR: Validation failed:" >&2
  echo -e "$ERRORS" >&2
  exit 1
fi

# Build YAML entry
DATE=$(echo "$JSON_PAYLOAD" | jq -r '.date')
CRAWL_TYPE=$(echo "$JSON_PAYLOAD" | jq -r '.crawl_type')
TICKET=$(echo "$JSON_PAYLOAD" | jq -r '.ticket')
CRAWL_NUM=$(echo "$JSON_PAYLOAD" | jq -r '.crawl_number')
ITER_USED=$(echo "$JSON_PAYLOAD" | jq -r '.iterations_used')
ITER_BUDGET=$(echo "$JSON_PAYLOAD" | jq -r '.iterations_budget')
GP=$(echo "$JSON_PAYLOAD" | jq -r '.gate_results.pass')
GF=$(echo "$JSON_PAYLOAD" | jq -r '.gate_results.fail')
SHA=$(echo "$JSON_PAYLOAD" | jq -r '.self_healing_attempts // 0')
SHR=$(echo "$JSON_PAYLOAD" | jq -r '.self_healing_resolved // 0')
EXIT_R=$(echo "$JSON_PAYLOAD" | jq -r '.exit_reason')
WALL=$(echo "$JSON_PAYLOAD" | jq -r '.wall_time_minutes')
SUBS=$(echo "$JSON_PAYLOAD" | jq -r '.sub_agents_spawned // 0')
COMPACTIONS=$(echo "$JSON_PAYLOAD" | jq -r '.context_compactions // 0')

YAML_ENTRY="  - schema_version: \"1.0\"
    date: \"$DATE\"
    crawl_type: $CRAWL_TYPE
    ticket: $TICKET
    crawl_number: $CRAWL_NUM
    iterations_used: $ITER_USED
    iterations_budget: $ITER_BUDGET
    gate_results: {pass: $GP, fail: $GF}
    self_healing_attempts: $SHA
    self_healing_resolved: $SHR
    exit_reason: $EXIT_R
    wall_time_minutes: $WALL
    sub_agents_spawned: $SUBS
    context_compactions: $COMPACTIONS
    harness_changes: []"

# Initialize scorecard if missing
if [[ ! -f "$SCORECARD_FILE" ]]; then
  mkdir -p "$(dirname "$SCORECARD_FILE")"
  cat > "$SCORECARD_FILE" << 'INIT_EOF'
# Harness Scorecard — Automated Crawl Metrics
schema_version: "1.0"
entries:
INIT_EOF
fi

# Thread-safe append (portable: mkdir-based lock, no flock on macOS)
_lock() {
  local retries=0
  while ! mkdir "$LOCK_FILE" 2>/dev/null; do
    retries=$((retries + 1))
    if [[ $retries -ge 20 ]]; then
      echo "ERROR: Could not acquire lock after 10s" >&2
      exit 1
    fi
    sleep 0.5
  done
  trap '_unlock' EXIT
}
_unlock() { rmdir "$LOCK_FILE" 2>/dev/null || true; }

_lock
echo "$YAML_ENTRY" >> "$SCORECARD_FILE"
echo "" >> "$SCORECARD_FILE"
_unlock

echo "Scorecard entry appended to $SCORECARD_FILE"
echo "Entry: $DATE | $CRAWL_TYPE | $TICKET | #$CRAWL_NUM | $EXIT_R | ${ITER_USED}/${ITER_BUDGET} iters | ${WALL}min"
