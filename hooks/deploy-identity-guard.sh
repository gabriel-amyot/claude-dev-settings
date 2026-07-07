#!/usr/bin/env bash
# Deploy-Identity Guard — PreToolUse hook for Read|Grep (KTP-688 Layer A, the spine).
#
# Fires when you are about to READ source code in a repo whose deployed branch differs from the
# branch you have checked out, AND there is a signal you are reasoning about DEPLOYED behaviour.
# This is the belief-independent trigger: it does NOT ask the agent how confident it feels.
# It breaks the frame that caused the wrong-branch catastrophe (reading `main` while `dev` deploys).
#
# Block condition (exit 2 = block, stderr shown to agent):
#   probe says current branch is NOT a deploy branch, AND
#   ( you are sitting on the repo's DEFAULT branch  OR  the recent transcript shows deployed-system intent )
# Otherwise: exit 0 (allow). Normal feature work on a feature branch is NOT blocked.
#
# Defense-in-depth, not sole safeguard. Probe: ~/.claude/skills/deploy-identity/probe.sh

set -u
PROBE="$HOME/.claude/skills/deploy-identity/probe.sh"
[ -x "$PROBE" ] || exit 0

INPUT=$(cat)

# Extract the target path (Read.file_path or Grep.path) and the transcript path.
# Printed on separate lines so paths containing spaces survive intact.
EXTRACT="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get('tool_input', d)
fp = ti.get('file_path') or ti.get('filePath') or ti.get('path') or ''
tp = d.get('transcript_path','')
print(fp)
print(tp)
" 2>/dev/null)"
FILE_PATH="$(printf '%s\n' "$EXTRACT" | sed -n '1p')"
TRANSCRIPT_PATH="$(printf '%s\n' "$EXTRACT" | sed -n '2p')"

[ -z "${FILE_PATH:-}" ] && exit 0

# Only consider files under ~/Developer (code repos); skip project-management.
case "$FILE_PATH" in
  "$HOME/Developer/"*) ;;
  *) exit 0 ;;
esac
case "$FILE_PATH" in
  *"/project-management/"*) exit 0 ;;
esac

# Run the probe (deterministic, ~1 git call). Parse its machine line.
PROBE_OUT="$("$PROBE" "$FILE_PATH" 2>/dev/null)"
JSON_LINE="$(printf '%s\n' "$PROBE_OUT" | sed -n 's/^DEPLOY_IDENTITY_JSON=//p' | head -1)"
[ -z "$JSON_LINE" ] && exit 0

# Parse fields WITHOUT eval — probe data (esp. branch names, which may legally contain ; ` && |)
# must never be executed. Values are printed one-per-line and read positionally; branch names
# cannot contain newlines, so this is unambiguous.
FIELDS="$(printf '%s' "$JSON_LINE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for k in ('status','on_deploy_branch','current_branch','default_branch','deploy_branch','snapshot'):
    print(d.get(k,''))
" 2>/dev/null)"
STATUS="$(printf '%s\n' "$FIELDS"   | sed -n '1p')"
ON_DEPLOY="$(printf '%s\n' "$FIELDS" | sed -n '2p')"
CUR="$(printf '%s\n' "$FIELDS"      | sed -n '3p')"
DEF="$(printf '%s\n' "$FIELDS"      | sed -n '4p')"
DEPLOY="$(printf '%s\n' "$FIELDS"   | sed -n '5p')"
SNAP="$(printf '%s\n' "$FIELDS"     | sed -n '6p')"

# Only MISMATCH / CANT_VERIFY are interesting. VERIFIED / NO_REGISTRY / NO_REPO → allow.
case "${STATUS:-}" in
  MISMATCH|CANT_VERIFY) ;;
  *) exit 0 ;;
esac
# If we're actually on a deploy branch, allow (shouldn't reach here, but be safe).
[ "${ON_DEPLOY:-false}" = "True" ] || [ "${ON_DEPLOY:-false}" = "true" ] && exit 0

# Is the agent sitting on the repo's default branch? (the strongest anomaly — the exact KTP-688 trap)
ON_DEFAULT="false"
[ -n "${CUR:-}" ] && [ "${CUR:-}" = "${DEF:-}" ] && ON_DEFAULT="true"

# Deployed-system intent in the recent transcript?
INTENT="false"
if [ -n "${TRANSCRIPT_PATH:-}" ] && [ -f "${TRANSCRIPT_PATH}" ]; then
  if tail -n 250 "$TRANSCRIPT_PATH" 2>/dev/null | grep -qiE 'deploy|deployed|in prod|production|why .*(fail|broke|wrong)|is .*failing|running in|on dev\b|prod\b|live (env|site|chat)|diagnos'; then
    INTENT="true"
  fi
fi

# Decide.
if [ "$ON_DEFAULT" = "true" ] || [ "$INTENT" = "true" ]; then
  {
    echo "BLOCKED by deploy-identity-guard: you are about to read code that is NOT the deployed branch."
    echo
    printf '%s\n' "$PROBE_OUT" | grep -vE '^DEPLOY_IDENTITY_JSON='
    echo
    echo "WHY THIS FIRED: current branch='${CUR}', deploy branch='${DEPLOY}'"
    [ "$ON_DEFAULT" = "true" ] && echo "  • you are on the repo's DEFAULT branch, which is NOT the deploy branch (the KTP-688 trap)."
    [ "$INTENT" = "true" ]     && echo "  • the recent conversation is about deployed/production behaviour."
    echo
    echo "DO THIS INSTEAD:"
    echo "  1. Read the DEPLOY branch, not the checked-out branch:"
    echo "       git -C <repo> show ${DEPLOY}:<relative/path>"
    echo "       git -C <repo> grep <pattern> ${DEPLOY}"
    echo "  2. Run /deploy-identity for the full probe + the citation stamp to attach to any claim."
    echo "  3. Confidence on any deployed-code claim is CAPPED to HYPOTHESIS until you read ${DEPLOY}."
    echo
    echo "If you are intentionally reading the checked-out branch for non-deployed reasons, that is fine —"
    echo "but you may NOT cite it as 'the deployed code'."
  } >&2
  exit 2
fi

exit 0
