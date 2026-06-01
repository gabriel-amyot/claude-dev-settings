#!/usr/bin/env bash
# Session Close Operationalize Guard: PreToolUse hook for Edit and Write.
#
# Blocks the universal close artifact — the ledger write that sets a session to
# `status: closed` or `status: abandoned` — unless /operationalize has run as part
# of THIS close. Proof-of-capture is the session's knowledge-manifest.yaml `last_run`
# stamp being recent.
#
# Why: session:check Phase S-2 (Capture/Operationalize) is mandatory, but a skill
# instruction is rationalizable and was skipped in practice. This moves enforcement
# out of the agent's judgment and into the harness. The agent cannot mark a session
# closed until capture has actually run and stamped the manifest.
#
# Signal: knowledge-manifest.yaml `last_run` (ISO timestamp), NOT git/inbox state.
#   - The librarian inbox is meant to accumulate across sessions, so its git-dirtiness
#     says nothing about whether THIS session captured. The manifest does.
#   - `last_run` is stamped on EVERY /operationalize run, even zero-nugget runs, so the
#     "already captured everything" case passes instead of false-blocking.
#   - Recency (not just existence) is required, so an operationalize run from early in
#     the session — before more work happened — does not satisfy the gate.
#
# Window: OPERATIONALIZE_GATE_WINDOW_MIN minutes (default 15). The close sequence runs
# capture first (S-2), then a few more phases before the gated ledger write, so the
# window must comfortably exceed that span.
#
# Override: create <pm>/sessions/.operationalize-skip (with a reason inside) to bypass
# once when capture genuinely cannot run. Explicit and logged.
#
# Exit 0 = allow the write. Exit 2 = BLOCK the write (stdout shown to agent).

INPUT=$(cat)

FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', data)
print(ti.get('file_path', ti.get('filePath', '')))" 2>/dev/null)

NEW_CONTENT=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', data)
print(ti.get('new_string', ti.get('content', '')) or '')" 2>/dev/null)

# Only guard the session ledger.
case "$FILE_PATH" in
  *"/sessions/ledger.yaml") ;;
  *) exit 0 ;;
esac

# Only act when this write is closing/abandoning a session.
if ! printf '%s' "$NEW_CONTENT" | grep -Eq 'status:[[:space:]]*(closed|abandoned)'; then
  exit 0
fi

PM_ROOT="${FILE_PATH%/sessions/ledger.yaml}"
if [ ! -d "$PM_ROOT" ]; then
  exit 0
fi

# Explicit override marker (with a reason inside the file).
if [ -f "$PM_ROOT/sessions/.operationalize-skip" ]; then
  echo "NOTICE: .operationalize-skip present — operationalize gate bypassed for this close." >&2
  exit 0
fi

WINDOW_MIN="${OPERATIONALIZE_GATE_WINDOW_MIN:-15}"

# Freshest last_run across all session manifests (active first; archive/done covers a
# manifest already moved). Returns minutes-since-last_run, or empty if none parseable.
AGE_MIN=$(PM_ROOT="$PM_ROOT" python3 - <<'PY' 2>/dev/null
import os, glob, datetime, re, sys

pm = os.environ['PM_ROOT']
patterns = [
    os.path.join(pm, 'sessions', 'active', '*', 'knowledge-manifest.yaml'),
    os.path.join(pm, 'sessions', 'archive', 'done', '*', 'knowledge-manifest.yaml'),
]
best = None
for pat in patterns:
    for f in glob.glob(pat):
        try:
            with open(f) as fh:
                txt = fh.read()
        except OSError:
            continue
        m = re.search(r'^last_run:\s*(.+)$', txt, re.MULTILINE)
        if not m:
            continue
        val = m.group(1).strip().strip('"').strip("'")
        if not val or val.lower() in ('null', '~', 'none'):
            continue
        v = val.replace('Z', '+00:00')
        try:
            dt = datetime.datetime.fromisoformat(v)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        if best is None or dt > best:
            best = dt
if best is None:
    sys.exit(0)
now = datetime.datetime.now(datetime.timezone.utc)
mins = (now - best).total_seconds() / 60.0
print('%.1f' % mins)
PY
)

# Fresh enough → capture ran as part of this close → allow.
if [ -n "$AGE_MIN" ]; then
  if awk -v a="$AGE_MIN" -v w="$WINDOW_MIN" 'BEGIN{exit !(a <= w)}'; then
    exit 0
  fi
fi

echo "BLOCKED: Cannot close this session — capture (/operationalize) has not run for this close."
echo ""
if [ -n "$AGE_MIN" ]; then
  echo "Most recent knowledge-manifest.yaml last_run was ${AGE_MIN} min ago (window: ${WINDOW_MIN} min)."
  echo "That capture is stale — work has likely happened since. Capture again before closing."
else
  echo "No knowledge-manifest.yaml with a valid last_run was found under sessions/active/."
  echo "Capture has never run for this session."
fi
echo ""
echo "session:check Phase S-2 (Capture) is mandatory and runs FIRST in the shutdown."
echo "It mines the session for tribal knowledge and writes it through to the bibliotheque"
echo "inbox before the session is torn down. Every session produces learnings."
echo ""
echo "Recovery:"
echo "  1. Invoke /operationalize (or re-run /session:check --close, which captures first)."
echo "  2. Confirm it stamped last_run in sessions/active/{slug}/knowledge-manifest.yaml."
echo "  3. Retry this ledger write."
echo ""
echo "Genuine override (capture truly cannot run — rare):"
echo "  echo 'reason' > $PM_ROOT/sessions/.operationalize-skip   # then retry"
exit 2
