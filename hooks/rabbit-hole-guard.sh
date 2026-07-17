#!/usr/bin/env bash
# Rabbit-Hole Guard — UserPromptSubmit hook (stern-owl handoff 2026-07-17).
#
# The rule: Peek = fine. Reach a hand in = fine (bounded). DIVE = not allowed inline — a dive
# requires a handoff. This hook catches the moment a DIVE is forming (a tangent that would pull
# sustained multi-step work off the active session intent) and injects a caveman nudge that
# converts it into a PARKED handoff instead of doing the work now. Rabbit holes are banked, not killed.
#
# Session-level sibling of Service Factory v3 §6 effort-governor (that guards the ticket; this guards
# the session). Same belief-independent design as challenge-detect.sh: the agent will NOT self-flag its
# own drift, so a mechanical trigger fires from outside the reasoning loop.
#
# UserPromptSubmit: stdout on exit 0 is added to the agent's context. We NEVER block a prompt.
#
# What trips it (the mechanical "this is a dive" test — two gates, conservative like challenge-detect):
#   1) the prompt uses ADDITIVE / EXPANSION language (the dive-phrase-class), AND
#   2) the transcript shows we are MID-TRAIL (already working a task) — so the tangent is a divergence,
#      not a fresh, legitimate redirect to new work.
# Peek ("noticing X, moving on") and a clean redirect ("ok now do KTP-123") do NOT fire — only an
# additive dive while on a trail does. This keeps the guard a nudge, not a nag.
#
# v1 = human-side only (Gab proposing a tangent). Agent-self-drift detection (Stop-mode: sustained
# off-anchor artifact creation) is a deliberate follow-up — see handoff
# 2026-07-17-rabbit-hole-guard-agent-self-drift.md.

set -u
INPUT=$(cat)

EXTRACT="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get('prompt',''))
print(d.get('transcript_path',''))
print(d.get('cwd',''))
" 2>/dev/null)"
PROMPT="$(printf '%s\n' "$EXTRACT" | sed -n '1p')"
TRANSCRIPT_PATH="$(printf '%s\n' "$EXTRACT" | sed -n '2p')"
CWD="$(printf '%s\n' "$EXTRACT" | sed -n '3p')"

[ -z "${PROMPT:-}" ] && exit 0

# 0) Explicit override: Gab knowingly greenlights the dive. Do not re-offer the choice — but STILL
#    remind that the override parks a stub first so nothing is lost.
OVERRIDE='(yes,? ?dive|go ahead and dive|i know (it.?s|this is) a dive|dive anyway|let.?s dive|override the guard)'
if printf '%s' "$PROMPT" | grep -qiE "$OVERRIDE"; then
  cat <<'EOF'
⚠ DIVE OVERRIDE acknowledged. Before doing the work: auto-park a one-line handoff stub for this dive
via `session:handoff` (so the long-term value is banked even though we're proceeding now), THEN dive.
The override skips the choice, not the parking.
EOF
  exit 0
fi

# 1) Does the prompt use additive / expansion (dive-forming) language?
DIVE_PHRASE='(while (i.?m|we.?re) (here|at it|in here)|as long as (i.?m|we.?re) (here|in here)|might as well|we should (really|also|probably)|this is (actually|really) a (bigger|whole|much bigger)|let me (also|just) (build|design|spec|create|add|refactor|set ?up|implement|architect)|could (also|we) (build|design|add|create|refactor)|worth (building|designing|adding|doing) (a|an|the)|deserves its own (skill|system|ticket|handoff|framework)|whole (system|framework|architecture|redesign) for|bigger (fish|problem|thing|refactor|rework)|rabbit ?hole|side ?quest|down a tangent|go deep on|really (dig|dive) into|refactor (this|the whole|everything)|rewrite (this|the whole|everything))'
printf '%s' "$PROMPT" | grep -qiE "$DIVE_PHRASE" || exit 0

# 2) Are we mid-trail? (scope guard: a dive is a divergence FROM ongoing work, not the first prompt.)
MIDTRAIL="false"
if [ -n "${TRANSCRIPT_PATH:-}" ] && [ -f "${TRANSCRIPT_PATH}" ]; then
  if tail -n 400 "$TRANSCRIPT_PATH" 2>/dev/null | grep -qiE 'tool_use|"type":"tool|Edit|Write|Bash|working on|implement|the ticket|KTP-[0-9]|SPV-[0-9]|INS-[0-9]|let me|on-trail|committed|pushed'; then
    MIDTRAIL="true"
  fi
else
  # No transcript — better to offer the choice than miss a dive.
  MIDTRAIL="true"
fi
[ "$MIDTRAIL" = "true" ] || exit 0

# 3) Best-effort anchor: the active session intent (for naming the trail in the nudge). A nudge that
#    never blocks tolerates a fuzzy anchor — the dive detection above stands on its own.
INTENT=""
PM_DIR=""
case "$CWD" in
  *project-management*) PM_DIR="${CWD%%project-management*}project-management" ;;
esac
if [ -z "$PM_DIR" ]; then
  PM_DIR="/Users/gabrielamyot/Developer/grp-beklever-com/project-management"
fi
ACTIVE_DIR="$PM_DIR/sessions/active"
if [ -d "$ACTIVE_DIR" ]; then
  LATEST_STATE="$(ls -t "$ACTIVE_DIR"/*/state.yaml 2>/dev/null | head -1)"
  if [ -n "${LATEST_STATE:-}" ] && [ -f "$LATEST_STATE" ]; then
    INTENT="$(grep -m1 -E '^intent:' "$LATEST_STATE" 2>/dev/null | sed -E 's/^intent:[[:space:]]*//; s/^"//; s/"$//')"
  fi
fi
[ -z "$INTENT" ] && INTENT="the active session intent"

# 4) Inject the caveman nudge. Detect → name → convert to a parked handoff (default), never execute inline.
cat <<EOF
⚠ DIVE DETECTED — this reads like a dive off: "${INTENT}".

Peek = fine. Reach in (bounded) = fine. A DIVE (sustained multi-step work that produces artifacts and
pulls off the trail) is NOT allowed inline — it must become a handoff. Do NOT start building/designing
the tangent now. Surface this ONE caveman choice to Gab and wait:

  DIVE off "${INTENT}" — park it?
    [handoff]         → auto-draft a parked handoff via session:handoff, then back to the trail (DEFAULT)
    [reach N-min]     → one bounded probe (say the budget), then back — no artifacts, no new build
    [not now]         → drop it, keep going

Default = park to a handoff. The rabbit hole is banked (its long-term value is kept), not killed.
If Gab picks [handoff], draft it and RETURN to the trail — do not also do the work.
EOF
exit 0
