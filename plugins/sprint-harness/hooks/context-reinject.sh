#!/bin/bash
# SessionStart hook (matcher: startup|resume|compact): Reinjects harness state as additionalContext.
# Ensures phase, AC progress, assumptions, and context manifest survive compaction.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/read-state.sh"

# If harness is not active, do nothing
is_harness_active 2>/dev/null || exit 0

PHASE="$(get_state "phase" || echo "")"
TICKET="$(get_state "ticket" || echo "")"
CURRENT_AC="$(get_state "current_ac" || echo "")"
ITERATION="$(get_state "iteration" || echo "")"
GATE_FAILURES="$(get_state "gate_failures" || echo "0")"
LAST_GATE="$(get_state "last_gate_result" || echo "")"

# Build completed ACs list
COMPLETED_ACS="$(get_state_list "completed_acs" 2>/dev/null | tr '\n' ', ' | sed 's/,$//')"

# Read assumptions from spec gate
ASSUMPTIONS="$(get_state_list "assumptions" 2>/dev/null | tr '\n' '; ' | sed 's/;$//')"

# Read context manifest summary if it exists
MANIFEST_FILE="$(get_state "context_manifest" || echo "")"
MANIFEST_SUMMARY=""
if [ -n "$MANIFEST_FILE" ]; then
  PROJECT_DIR="$(get_project_dir 2>/dev/null || echo "")"
  if [ -n "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/$MANIFEST_FILE" ]; then
    MANIFEST_STATUS="$(grep "^status:" "$PROJECT_DIR/$MANIFEST_FILE" 2>/dev/null | head -1 | sed 's/^status:[[:space:]]*//')"
    MANIFEST_SUMMARY="Context manifest: $MANIFEST_STATUS"
  fi
fi

# Read spec gate status if it exists
SPEC_REPORT="$(get_state "spec_gate_report" || echo "")"
SPEC_SUMMARY=""
if [ -n "$SPEC_REPORT" ]; then
  PROJECT_DIR="$(get_project_dir 2>/dev/null || echo "")"
  if [ -n "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/$SPEC_REPORT" ]; then
    SPEC_STATUS="$(grep "^status:" "$PROJECT_DIR/$SPEC_REPORT" 2>/dev/null | head -1 | sed 's/^status:[[:space:]]*//')"
    SPEC_SUMMARY="Spec gate: $SPEC_STATUS"
  fi
fi

# Read latest status report
PROJECT_DIR="$(get_project_dir 2>/dev/null || echo "")"
LATEST_STATUS=""
if [ -n "$PROJECT_DIR" ] && [ -n "$TICKET" ]; then
  STATUS_DIR="$PROJECT_DIR/tickets/$TICKET/reports/status"
  if [ -d "$STATUS_DIR" ]; then
    LATEST_FILE="$(find "$STATUS_DIR" -maxdepth 1 -name '*.md' -print 2>/dev/null | head -1)"
    if [ -n "$LATEST_FILE" ]; then
      LATEST_STATUS="Latest status report: $(basename "$LATEST_FILE")"
    fi
  fi
fi

# Output context as plain text (stdout gets injected as additionalContext)
cat <<EOF
=== SPRINT HARNESS STATE ===
Ticket: $TICKET
Phase: $PHASE
Current AC: $CURRENT_AC
Completed ACs: ${COMPLETED_ACS:-none}
Iteration: $ITERATION
Gate failures: $GATE_FAILURES
Last gate result: ${LAST_GATE:-none}
${SPEC_SUMMARY:+$SPEC_SUMMARY}
${MANIFEST_SUMMARY:+$MANIFEST_SUMMARY}
${ASSUMPTIONS:+Assumptions: $ASSUMPTIONS}
${LATEST_STATUS:+$LATEST_STATUS}

IMPORTANT: You are in phase '$PHASE'. Use '/harness advance' to transition to the next phase when gate conditions are met. Use '/harness status' to see full state.
=== END HARNESS STATE ===
EOF
