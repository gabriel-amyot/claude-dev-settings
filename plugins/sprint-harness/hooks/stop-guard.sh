#!/bin/bash
# Stop hook: Prevents Claude from exiting before phase completion.
# Blocks exit unless phase is 'done', 'ship' (commit done), or spec-gate aborted.
# Coexists with ralph-loop stop hook (ralph-loop handles iteration, this handles phase).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/read-state.sh"

# If harness is not active, allow exit
is_harness_active 2>/dev/null || exit 0

INPUT="$(cat)"

# Check if this is already a stop-hook re-entry (prevent infinite loops)
STOP_HOOK_ACTIVE="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stop_hook_active', False))" 2>/dev/null || echo "False")"
if [ "$STOP_HOOK_ACTIVE" = "True" ]; then
  exit 0
fi

PHASE="$(get_state "phase" || echo "")"
TICKET="$(get_state "ticket" || echo "")"
CURRENT_AC="$(get_state "current_ac" || echo "")"

case "$PHASE" in
  done)
    # Phase complete, allow exit
    exit 0
    ;;

  spec-gate)
    # Check if spec gate aborted (intent unclear, nothing to do)
    SPEC_REPORT="$(get_state "spec_gate_report" || echo "")"
    PROJECT_DIR="$(get_project_dir 2>/dev/null || echo "")"
    if [ -n "$SPEC_REPORT" ] && [ -n "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/$SPEC_REPORT" ]; then
      SPEC_STATUS="$(grep "^status:" "$PROJECT_DIR/$SPEC_REPORT" 2>/dev/null | head -1 | sed 's/^status:[[:space:]]*//')"
      if [ "$SPEC_STATUS" = "abort" ]; then
        # Ticket is blocked, allow exit
        exit 0
      fi
    fi
    # Otherwise block
    REASON="Spec gate not complete for $TICKET. Run Leo spec quality check, write spec-gate-report.yaml, then '/harness advance'."
    ;;

  context-gate)
    REASON="Context gate not complete for $TICKET. Run context curator, write context-manifest.yaml, then '/harness advance'."
    ;;

  planning)
    REASON="Planning not complete for $TICKET $CURRENT_AC. Write implementation plan to reports/architecture/, then '/harness advance'."
    ;;

  implementation)
    REASON="Implementation not complete for $TICKET $CURRENT_AC. Ensure tests pass, then '/harness advance'."
    ;;

  review)
    REASON="Review not complete for $TICKET $CURRENT_AC. Run adversarial review, ensure no CRITICAL findings, then '/harness advance'."
    ;;

  verification)
    REASON="Verification not complete for $TICKET $CURRENT_AC. Update ac.yaml status to done, then '/harness advance'."
    ;;

  ship)
    REASON="Shipping not complete for $TICKET $CURRENT_AC. Commit and push changes, then '/harness advance'."
    ;;

  *)
    REASON="Unknown phase '$PHASE'. Use '/harness status' to check state or '/harness reset' to disable harness."
    ;;
esac

# Output JSON to block exit
python3 -c "
import json, sys
reason = sys.stdin.read().strip()
print(json.dumps({'decision': 'block', 'reason': reason}))
" <<< "$REASON"
