#!/usr/bin/env bash
# Ticket Path Guard: PreToolUse hook for Write and Edit.
#
# project-management has a strict layout: nothing new in the repo root, and ticket files
# live under tickets/{PREFIX}/{EPIC|no-epic}/{TICKET-ID}/. That is a deterministic check,
# so it belongs in a script rather than in prose that loads every session.
#
# WARN-ONLY for now. Promote to blocking after an observation period with no false
# positives. A placement warning must never stop real work.

FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('file_path', d.get('filePath','')))" 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0

PM="$HOME/Developer/grp-beklever-com/project-management"
case "$FILE_PATH" in
  "$PM"/*) ;;
  *) exit 0 ;;
esac

REL="${FILE_PATH#$PM/}"
[ -f "$FILE_PATH" ] && exit 0   # editing something that exists is not a placement decision

warn() { echo ""; echo "TICKET PATH GUARD: $1"; echo "$2"; echo ""; }

# 1. Repo root holds only CLAUDE.md, GEMINI.md, AGENTS.md, INDEX.md and known dirs.
case "$REL" in
  */*) ;;
  CLAUDE.md|GEMINI.md|AGENTS.md|INDEX.md|README.md) ;;
  *)
    warn "new file at the repo root: $REL" \
"The root holds only CLAUDE.md, GEMINI.md, AGENTS.md, INDEX.md and the core directories.
Put this under the ticket it belongs to, or documentation/ if it is long-lived reference."
    exit 0 ;;
esac

# 2. Ticket paths must be tickets/{PREFIX}/{EPIC|no-epic}/{TICKET-ID}/...
case "$REL" in
  tickets/*)
    if echo "$REL" | grep -qE '^tickets/(KTP|KTT|SPV|INS|PER)-[0-9]+/'; then
      P=$(echo "$REL" | sed -E 's|^tickets/([A-Z]+)-[0-9]+/.*|\1|')
      T=$(echo "$REL" | sed -E 's|^tickets/([A-Z]+-[0-9]+)/.*|\1|')
      warn "flat ticket path: $REL" \
"Tickets are bucketed by prefix, then epic. Use:
  tickets/$P/{EPIC-ID}/$T/...     if it belongs to an epic
  tickets/$P/no-epic/$T/...       if it is standalone"
      exit 0
    fi
    if echo "$REL" | grep -qE '^tickets/(KTP|SPV|INS|PER)/(KTP|SPV|INS|PER)-[0-9]+/'; then
      P=$(echo "$REL" | sed -E 's|^tickets/([A-Z]+)/.*|\1|')
      T=$(echo "$REL" | sed -E 's|^tickets/[A-Z]+/([A-Z]+-[0-9]+)/.*|\1|')
      warn "ticket directly under its prefix: $REL" \
"A ticket needs an epic bucket. Use tickets/$P/{EPIC-ID}/$T/ or tickets/$P/no-epic/$T/."
      exit 0
    fi
    ;;
esac
exit 0
