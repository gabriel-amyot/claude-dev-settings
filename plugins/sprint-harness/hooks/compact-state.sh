#!/bin/bash
# PreCompact hook: Persists harness state before context compaction.
# Ensures ac.yaml is consistent with current progress.
# Supplements (does not replace) the existing pre-compact-guard.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/read-state.sh"

# If harness is not active, skip
is_harness_active 2>/dev/null || exit 0

PHASE="$(get_state "phase" || echo "")"
TICKET="$(get_state "ticket" || echo "")"
CURRENT_AC="$(get_state "current_ac" || echo "")"
PROJECT_DIR="$(get_project_dir 2>/dev/null || echo "")"

# Output context reminder that will be injected
cat <<EOF
=== SPRINT HARNESS PRE-COMPACTION REMINDER ===
BEFORE compaction completes, ensure you have:
1. Updated ac.yaml if any AC status changed
2. Written progress to reports/status/ if implementation work was done
3. State file (.claude/sprint-harness-state.yaml) is current

Current state: ticket=$TICKET phase=$PHASE ac=$CURRENT_AC
The context-reinject hook will restore this state after compaction.
=== END REMINDER ===
EOF

exit 0
