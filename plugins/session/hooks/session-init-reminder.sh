#!/usr/bin/env bash
# Session plugin SessionStart hook
# Reads sessions/ledger.yaml, counts awaiting handoffs, emits a one-liner nudge.
# Skips silently if ledger doesn't exist or no handoffs are pending.

set -euo pipefail

# Find the project-management ledger for the CURRENT org only.
# Walk up from $PWD; the first sessions/ledger.yaml found belongs to the org
# whose tree we are in. Never fall back to another org's ledger — that would
# leak handoffs across org boundaries (e.g. surfacing Klever handoffs in a
# supervisr-ai session). If no ledger is in the current tree, stay silent.
find_ledger() {
  local dir="$PWD"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/sessions/ledger.yaml" ]]; then
      echo "$dir/sessions/ledger.yaml"
      return 0
    fi
    dir="$(dirname "$dir")"
  done

  return 1
}

LEDGER=$(find_ledger 2>/dev/null) || exit 0

# Count awaiting_initiation entries.
# grep -c prints "0" AND exits non-zero when there are no matches, so the
# old `|| echo 0` idiom produced a "0\n0" value that broke the -eq test below.
# Swallow the exit code with `|| true` and rely on grep -c's own count output.
AWAITING=$(grep -c 'status: awaiting_initiation' "$LEDGER" 2>/dev/null || true)
AWAITING=${AWAITING:-0}

APPROVED=$(grep -c 'autopilot: approved' "$LEDGER" 2>/dev/null || true)
APPROVED=${APPROVED:-0}
FAILED=$(grep -c 'autopilot: failed' "$LEDGER" 2>/dev/null || true)
FAILED=${FAILED:-0}

if [[ "$AWAITING" -eq 0 && "$FAILED" -eq 0 ]]; then
  exit 0
fi

MSG="SESSION: $AWAITING handoff(s) awaiting pickup. Run /session:init or /session:pickup."
[[ "$APPROVED" -gt 0 ]] && MSG="$MSG $APPROVED queued for autopilot."
[[ "$FAILED" -gt 0 ]] && MSG="$MSG $FAILED autopilot run(s) NEED HUMAN (/session:autopilot status)."
echo "$MSG"
