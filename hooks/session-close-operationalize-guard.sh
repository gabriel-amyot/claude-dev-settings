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

# Freshest manifest by last_run. Emits two tokens: "<age_min> <inbox_ok>".
#   age_min  = minutes since that manifest's last_run (empty if none parseable)
#   inbox_ok = 1 if the freshest manifest references a bibliothèque inbox file that
#              EXISTS on disk (proof gab-operationalize routed knowledge this session),
#              OR if this PM has no bibliothèque inbox dir (org doesn't use it → don't block).
#              0 means a stamp exists but no real inbox capture is referenced — e.g. a
#              hand-stamped manifest or operationalize-audit (which writes no inbox file).
RESULT=$(PM_ROOT="$PM_ROOT" python3 - <<'PY' 2>/dev/null
import os, glob, datetime, re, sys

pm = os.environ['PM_ROOT']
patterns = [
    os.path.join(pm, 'sessions', 'active', '*', 'knowledge-manifest.yaml'),
    os.path.join(pm, 'sessions', 'archive', 'done', '*', 'knowledge-manifest.yaml'),
]
best = None
best_txt = ''
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
            best_txt = txt
if best is None:
    sys.exit(0)

# Does the freshest manifest reference a real bibliothèque inbox file?
inbox_dir = os.path.join(pm, 'documentation', 'bibliotheque', 'inbox')
if not os.path.isdir(inbox_dir):
    inbox_ok = 1   # org doesn't use the inbox — don't enforce
else:
    existing = {os.path.basename(p) for p in glob.glob(os.path.join(inbox_dir, '*.md'))
                if os.path.basename(p) != 'INDEX.md'}
    inbox_ok = 1 if any(name and name in best_txt for name in existing) else 0

now = datetime.datetime.now(datetime.timezone.utc)
mins = (now - best).total_seconds() / 60.0
print('%.1f %d' % (mins, inbox_ok))
PY
)

AGE_MIN=$(printf '%s' "$RESULT" | awk '{print $1}')
INBOX_OK=$(printf '%s' "$RESULT" | awk '{print $2}')

# Allow only when BOTH: capture is fresh AND it routed to a real inbox file.
if [ -n "$AGE_MIN" ]; then
  FRESH=$(awk -v a="$AGE_MIN" -v w="$WINDOW_MIN" 'BEGIN{print (a <= w) ? 1 : 0}')
  if [ "$FRESH" = "1" ] && [ "$INBOX_OK" = "1" ]; then
    exit 0
  fi
fi

echo "BLOCKED: Cannot close this session — real capture (gab-operationalize) has not run for this close."
echo ""
if [ -z "$AGE_MIN" ]; then
  echo "No knowledge-manifest.yaml with a valid last_run was found. Capture has never run for this session."
elif [ "$(awk -v a="$AGE_MIN" -v w="$WINDOW_MIN" 'BEGIN{print (a <= w) ? 1 : 0}')" != "1" ]; then
  echo "Most recent manifest last_run was ${AGE_MIN} min ago (window: ${WINDOW_MIN} min)."
  echo "That capture is stale — work has likely happened since. Capture again before closing."
else
  echo "Manifest last_run is fresh, but it does NOT reference a bibliothèque inbox file that exists."
  echo "That means knowledge was not routed to the inbox this session — a fresh stamp alone is not"
  echo "proof of capture. Common cause: 'operationalize-audit' (the backlog reviewer) was run by"
  echo "mistake, or last_run was stamped without a real capture. Run the CAPTURE skill, not the audit."
fi
echo ""
echo "session:check Phase S-2 (Capture) is mandatory and runs FIRST in the shutdown."
echo "Use the gab-operationalize skill (the /operationalize command), NOT /operationalize-audit."
echo "It mines THIS session and writes nuggets through to the bibliotheque inbox."
echo ""
echo "Recovery:"
echo "  1. Invoke the gab-operationalize skill (or re-run /session:check --close, which captures first)."
echo "  2. Confirm it wrote an inbox file under documentation/bibliotheque/inbox/ AND stamped"
echo "     last_run in sessions/active/{slug}/knowledge-manifest.yaml (recording that inbox file)."
echo "  3. Retry this ledger write."
echo ""
echo "Genuine override (capture truly cannot run — rare):"
echo "  echo 'reason' > $PM_ROOT/sessions/.operationalize-skip   # then retry"
exit 2
