#!/usr/bin/env bash
# Dark Factory — Compliance Audit (Layer 2: the true backstop)
# ---------------------------------------------------------------------------
# Wired as a PostToolUse hook on the Skill tool. Fires after EVERY Skill call,
# then exits immediately and silently unless the skill was `dark-factory`.
#
# Why this is the real enforcement: the pre-ship gate (Layer 1) runs inside the
# agent's control — the agent could ignore a non-zero exit. This audit runs
# OUTSIDE agent control, after the dark-factory run completes. The agent cannot
# suppress, skip, or rationalize past its output. It prints a compliance report
# card that the agent (and the human reading the transcript) sees next turn.
#
# It is AUDIT, not GATE. It NEVER blocks (always exits 0). KTP-713 / Dexter RCA:
# "adding more instructional text does not improve compliance" — so the value
# here is the out-of-band report card, not another instruction.
#
# The audit logic lives in compliance-audit.py (sibling). This wrapper only:
#   1. reads the hook payload from stdin
#   2. bails unless the invoked skill is dark-factory
#   3. runs the audit and wraps its output as additionalContext JSON
# ---------------------------------------------------------------------------

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT_PY="$HERE/compliance-audit.py"

INPUT="$(cat)"

# Extract invoked skill + cwd. Fail open (exit 0, silent) on any malformed input.
SKILL="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {}) or {}
    print((ti.get('skill') or ti.get('name') or '').strip())
except Exception:
    pass
" 2>/dev/null)"

case "$SKILL" in
  dark-factory|*:dark-factory) : ;;
  *) exit 0 ;;
esac

CWD="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get('cwd') or '').strip())
except Exception:
    pass
" 2>/dev/null)"

REPORT="$(SEARCH_CWD="$CWD" python3 "$AUDIT_PY" 2>/dev/null)"

# Emit as additionalContext so the agent sees the report card next turn.
# Never block: always exit 0.
REPORT="$REPORT" python3 -c "
import os, json
msg = os.environ.get('REPORT', '')
if msg.strip():
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': msg}}))
" 2>/dev/null

exit 0
