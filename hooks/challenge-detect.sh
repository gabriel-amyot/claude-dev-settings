#!/usr/bin/env bash
# Challenge Detect — UserPromptSubmit hook (KTP-688 Layer C).
#
# When a credible challenge is raised against a prior FACTUAL claim, the failure mode is to gather
# more evidence FOR the claim (entrenchment) instead of trying to disprove it. This hook detects the
# challenge moment — belief-independent, because the agent will not self-trigger this (that is the
# defect) — and injects a directive routing into fresh-context falsification.
#
# UserPromptSubmit: stdout on exit 0 is added to the agent's context. We never block a prompt.
#
# Conservative by design: fires ONLY when the prompt looks like a contradiction of a claim AND the
# recent transcript actually contains a recent assertion. Benign disagreement ("let's also do Y")
# does not fire.

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
" 2>/dev/null)"
PROMPT="$(printf '%s\n' "$EXTRACT" | sed -n '1p')"
TRANSCRIPT_PATH="$(printf '%s\n' "$EXTRACT" | sed -n '2p')"

[ -z "${PROMPT:-}" ] && exit 0

# 1) Does the prompt look like pushback against a factual claim?
PUSHBACK='(it.?s not |that.?s not (right|correct|it|true)|that.?s wrong|you.?re wrong|\bBS\b|bullshit|does(n.?t| not) match|not the (model|cause|issue|problem|reason|fix)|that.?s incorrect|\bnope\b|no,? that.?s|pushed back|rejected|made up|that.?s made up|completely wrong|isn.?t (right|correct|the))'
printf '%s' "$PROMPT" | grep -qiE "$PUSHBACK" || exit 0

# 2) Does the recent transcript contain a recent ASSERTION worth falsifying?
#    (scope guard against over-firing on plan/preference disagreement)
ASSERTED="false"
if [ -n "${TRANSCRIPT_PATH:-}" ] && [ -f "${TRANSCRIPT_PATH}" ]; then
  if tail -n 400 "$TRANSCRIPT_PATH" 2>/dev/null | grep -qiE 'root cause|the cause is|caused by|because of|it.?s the |\.py:[0-9]|\.ts:[0-9]|\.java:[0-9]|diagnos|the (bug|issue|problem|fix) is|HIGH confidence|the model|the reason is'; then
    ASSERTED="true"
  fi
else
  # No transcript available — assume an assertion may exist; better to offer falsification than miss it.
  ASSERTED="true"
fi
[ "$ASSERTED" = "true" ] || exit 0

# 3) Inject the falsification directive into context.
cat <<'EOF'
⚠ CHALLENGE DETECTED — a credible party just contradicted a prior factual claim.

Do NOT gather more evidence FOR your position. That reflex (re-proving what is easy to prove) is the
entrenchment failure from KTP-688. Instead, try to DISPROVE your own claim:

1. Run the `deploy-identity` skill in **falsify** mode: dispatch a FRESH-context subagent (general-purpose
   via the Agent tool) given ONLY (a) the disputed claim, (b) the challenger's specific evidence
   verbatim, (c) the deploy-identity probe fact. Task it solely with "prove this claim is WRONG against
   the DEPLOYED branch." Do not hand it your prior reasoning or confidence — that is the anchor to escape.
2. If the claim is about deployed code, read the DEPLOY branch directly first:
   `git -C <repo> show <deploy_branch>:<path>` / `git -C <repo> grep <pattern> <deploy_branch>`.
   Verify which branch deploys with /deploy-identity before re-asserting anything.
3. Treat the challenger's evidence as likely correct until you have disproven it on the deployed code.
   A REFUTED verdict from the fresh falsifier is decisive — converge, do not defend.
EOF
exit 0
