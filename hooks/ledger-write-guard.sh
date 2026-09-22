#!/bin/bash
# PreToolUse Edit|Write guard for session ledgers.
#
# Blocks hand-editing of any org's sessions/ledger.yaml via the Edit/Write tools.
# The sanctioned write path is the `ledger` helper (it writes via python os.replace,
# NOT the Edit/Write tools, so it is never seen by this hook).
#
# Design: ~/.claude/plans/ledger-helper-design.md (v2).
# Enforcement scope: Edit/Write TOOL guard, not filesystem exclusivity (a deliberate
# Bash/sed write bypasses it — the helper itself uses Bash, so that path must stay open).
#
# Kill-switch (either disables the guard):
#   export LEDGER_GUARD_OFF=1
#   touch /Users/gabrielamyot/.claude/.ledger-guard-off
# FAILS OPEN on any internal error — never wedge every session because the guard broke.

SENTINEL="/Users/gabrielamyot/.claude/.ledger-guard-off"
[ -n "$LEDGER_GUARD_OFF" ] && exit 0
[ -f "$SENTINEL" ] && exit 0

input="$(cat)"

# Decide in python (robust JSON + realpath + allowlist). Prints "BLOCK <reason>" or nothing.
decision="$(printf '%s' "$input" | python3 -c '
import sys, json, os
ALLOW = [
    "/Users/gabrielamyot/Developer/grp-beklever-com/project-management/sessions/ledger.yaml",
    "/Users/gabrielamyot/Developer/supervisr-ai/project-management/sessions/ledger.yaml",
    "/Users/gabrielamyot/Developer/gabriel-amyot/project-management/sessions/ledger.yaml",
]
def canon(p):
    try: return os.path.realpath(p)
    except Exception: return p
allow = set(canon(p) for p in ALLOW)
try:
    data = json.load(sys.stdin)
    fp = (data.get("tool_input") or {}).get("file_path")
    if not fp:
        sys.exit(0)  # nothing to guard -> allow
    if canon(fp) in allow:
        org = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(canon(fp)))))
        print("BLOCK " + org)
except Exception:
    sys.exit(0)  # fail open
' 2>/dev/null)"

# fail open if python errored / produced nothing
[ -z "$decision" ] && exit 0

case "$decision" in
  BLOCK*)
    cat >&2 <<'MSG'
Blocked: sessions/ledger.yaml must not be hand-edited (Edit/Write). Corruption
(col-0 indentation, mis-filed records, fused entries) comes from hand-editing.

Use the deterministic helper instead (locked, validated, journaled).
IT ALREADY EXISTS AND IS ON PATH AS `ledger` — do not rebuild it, do not work
around it in Bash. `find ~/.claude -maxdepth 4` does NOT reach it (depth 5).

  ledger --org <org> validate
  absolute: ~/.claude/plugins/local-marketplace/session/bin/ledger.py
  commands: ~/.claude/plugins/local-marketplace/session/bin/LEDGER_WRITES.md

  append : ledger --org <org> append --section {sessions|handoffs} --json '{...}'
  update : ledger --org <org> update --section <s> --key <slug|file> --set k=v [...]
  claim  : ledger --org <org> claim  --key <file> --expect-status <s> --set status=initiated
  batch  : ledger --org <org> batch  --ops '[{...}]'
  rekey  : ledger --org <org> rekey  --section <s> --old <k> --new <k> [--occurrence N]
  get/validate/bootstrap likewise.

This guard sees Edit/Write only. A Bash write (sed, cat >, yaml.safe_dump +
os.replace) is NOT checked and NOT approved — it just goes unseen, skips the
flock other sessions rely on, and reflows the file. Use the helper there too.

Emergency disable (if this guard is wrong): touch ~/.claude/.ledger-guard-off
MSG
    exit 2
    ;;
  *)
    exit 0
    ;;
esac
