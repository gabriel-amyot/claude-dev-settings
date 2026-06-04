#!/usr/bin/env bash
# Dark Factory — Pre-Ship Artifact Gate (Layer 1: strong advisory)
# ---------------------------------------------------------------------------
# Referenced by SKILL.md Phase 7 Step 0. The orchestrator runs this BEFORE any
# Phase 7 shipping action (version bump, push, MR, Jira). If the exit code is
# not 0, Phase 7 HALTS and the agent returns to the phase that owns the missing
# artifact.
#
# Why a script and not prose: KTP-713 established that "adding more instructional
# text does not improve compliance." Prose checks get self-certified. A script
# that prints "FAIL: qa report missing" and returns exit 1 is cognitively harder
# to rationalize past than a paragraph. This is "strong advisory" — the agent
# still runs it and technically has the last word. The true backstop is the
# PostToolUse compliance hook (Layer 2), which runs outside agent control.
#
# Usage:
#   pre-ship-gate.sh <TICKET_DIR>
#
#   TICKET_DIR is the ticket folder containing pipeline-state.yaml,
#   qa/, review/, analyst/, and design/ (e.g.
#   tickets/KTP/KTP-559/KTP-682).
#
# Exit codes:
#   0  all required artifacts present  -> Phase 7 may proceed
#   1  one or more checks failed       -> Phase 7 HALTS (failures listed)
#   2  usage / environment error       -> bad argument, dir not found
# ---------------------------------------------------------------------------

set -u
shopt -s nullglob

TICKET_DIR="${1:-}"

if [ -z "$TICKET_DIR" ]; then
  echo "pre-ship-gate: ERROR — no TICKET_DIR argument given." >&2
  echo "Usage: pre-ship-gate.sh <TICKET_DIR>" >&2
  exit 2
fi

if [ ! -d "$TICKET_DIR" ]; then
  echo "pre-ship-gate: ERROR — ticket directory not found: $TICKET_DIR" >&2
  exit 2
fi

# Normalize: strip trailing slash for clean path printing.
TICKET_DIR="${TICKET_DIR%/}"
TICKET_ID="$(basename "$TICKET_DIR")"

PASS_MARK="PASS"
FAIL_MARK="FAIL"
SKIP_MARK="SKIP"

failures=0
declare -a results

record() {
  # record <mark> <check-name> <detail>
  results+=("$1|$2|$3")
  if [ "$1" = "$FAIL_MARK" ]; then
    failures=$((failures + 1))
  fi
}

# ---------------------------------------------------------------------------
# Check 1: QA report exists and is non-empty (> 10 lines).
# Phase 6 produces qa/qa-report.v*.md. An empty or stub report means QA did
# not actually run.
# ---------------------------------------------------------------------------
qa_reports=("$TICKET_DIR"/qa/qa-report.v*.md)
if [ ${#qa_reports[@]} -eq 0 ]; then
  record "$FAIL_MARK" "QA report" "no qa/qa-report.v*.md found — Phase 6 (QA) has not produced a report"
else
  # Pick the highest-versioned report (last after sort).
  latest_qa="$(printf '%s\n' "${qa_reports[@]}" | sort -V | tail -1)"
  qa_lines="$(wc -l < "$latest_qa" | tr -d ' ')"
  if [ "$qa_lines" -le 10 ]; then
    record "$FAIL_MARK" "QA report" "$(basename "$latest_qa") has only $qa_lines lines (need > 10) — report looks empty/stub"
  else
    record "$PASS_MARK" "QA report" "$(basename "$latest_qa") ($qa_lines lines)"
  fi
fi

# ---------------------------------------------------------------------------
# Check 2: review/ directory has at least one file.
# Phase 5 (Review) writes its findings here. An empty review/ means the
# external review agent never ran or never wrote its artifact.
# ---------------------------------------------------------------------------
if [ ! -d "$TICKET_DIR/review" ]; then
  record "$FAIL_MARK" "Review artifacts" "no review/ directory — Phase 5 (Review) has not run"
else
  review_files=("$TICKET_DIR"/review/*)
  # Count only regular files (ignore empty subdirs).
  review_count=0
  for f in ${review_files[@]+"${review_files[@]}"}; do
    [ -f "$f" ] && review_count=$((review_count + 1))
  done
  if [ "$review_count" -eq 0 ]; then
    record "$FAIL_MARK" "Review artifacts" "review/ exists but is empty — Phase 5 produced no findings file"
  else
    record "$PASS_MARK" "Review artifacts" "$review_count file(s) in review/"
  fi
fi

# ---------------------------------------------------------------------------
# Check 3: pipeline-state.yaml contains an execution_verified field.
# Phase 4 step 5 writes execution_verified; Phase 6 reads it as a hard gate.
# Its absence means execution was never attempted/recorded.
# ---------------------------------------------------------------------------
state_file="$TICKET_DIR/pipeline-state.yaml"
if [ ! -f "$state_file" ]; then
  record "$FAIL_MARK" "execution_verified" "no pipeline-state.yaml in ticket folder"
elif ! grep -Eq '^[[:space:]]*execution_verified[[:space:]]*:' "$state_file"; then
  record "$FAIL_MARK" "execution_verified" "pipeline-state.yaml has no execution_verified: field (Phase 4 step 5 skipped)"
else
  ev_value="$(grep -E '^[[:space:]]*execution_verified[[:space:]]*:' "$state_file" | head -1 | sed -E 's/^[^:]*:[[:space:]]*//' | tr -d '\r')"
  record "$PASS_MARK" "execution_verified" "present (${ev_value:-<empty>})"
fi

# ---------------------------------------------------------------------------
# Check 4: Frontend screenshots.
# If affected_repos references a frontend (package.json / Node) repo, then
# design/screenshots/ must have files OR the qa report must document why not.
# Backend-only tickets skip this check.
# ---------------------------------------------------------------------------
repo_files=("$TICKET_DIR"/analyst/affected_repos.v*.json)
if [ ${#repo_files[@]} -eq 0 ]; then
  record "$SKIP_MARK" "Frontend screenshots" "no analyst/affected_repos.v*.json — cannot determine repo types"
else
  latest_repos="$(printf '%s\n' "${repo_files[@]}" | sort -V | tail -1)"
  # Frontend signal: the affected_repos JSON mentions package.json, or a repo
  # type/name that indicates a Node/npm frontend project.
  if grep -Eiq 'package\.json|"type"[[:space:]]*:[[:space:]]*"[^"]*(node|npm|next|react|front)|front-portal|grp-frontend' "$latest_repos"; then
    screenshots=("$TICKET_DIR"/design/screenshots/*)
    shot_count=0
    for s in ${screenshots[@]+"${screenshots[@]}"}; do
      [ -f "$s" ] && shot_count=$((shot_count + 1))
    done
    if [ "$shot_count" -gt 0 ]; then
      record "$PASS_MARK" "Frontend screenshots" "$shot_count screenshot(s) in design/screenshots/"
    else
      # No screenshots — acceptable only if the qa report explains why.
      documented=false
      if [ -n "${latest_qa:-}" ] && [ -f "${latest_qa:-/nonexistent}" ]; then
        if grep -Eiq 'screenshot|no visual|not applicable|n/a|headless|no ui change|no frontend change' "$latest_qa"; then
          documented=true
        fi
      fi
      if [ "$documented" = true ]; then
        record "$PASS_MARK" "Frontend screenshots" "no screenshots, but qa report documents why"
      else
        record "$FAIL_MARK" "Frontend screenshots" "frontend repo affected but design/screenshots/ empty and qa report does not explain why"
      fi
    fi
  else
    record "$SKIP_MARK" "Frontend screenshots" "no frontend (package.json) repo in affected_repos — backend-only ticket"
  fi
fi

# ---------------------------------------------------------------------------
# Report.
# ---------------------------------------------------------------------------
echo "═══════════════════════════════════════════════════════════════════"
echo " Dark Factory Pre-Ship Artifact Gate — $TICKET_ID"
echo " $TICKET_DIR"
echo "═══════════════════════════════════════════════════════════════════"
for r in "${results[@]}"; do
  IFS='|' read -r mark name detail <<< "$r"
  printf ' [%-4s] %-22s %s\n' "$mark" "$name" "$detail"
done
echo "───────────────────────────────────────────────────────────────────"

if [ "$failures" -eq 0 ]; then
  echo " RESULT: PASS — all required artifacts present. Phase 7 may proceed."
  echo "═══════════════════════════════════════════════════════════════════"
  exit 0
else
  echo " RESULT: HALT — $failures check(s) failed. Phase 7 MUST NOT proceed."
  echo ""
  echo " Return to the phase that owns each missing artifact, produce it, then"
  echo " re-run this gate. Do not rationalize, self-certify, or ship past a"
  echo " failed gate (KTP-713 lesson)."
  echo "═══════════════════════════════════════════════════════════════════"
  exit 1
fi
