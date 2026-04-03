#!/bin/bash

# curator.sh — Deterministic Context Curation + Toolbelt Assembly
# The Quartermaster: fetches task-relevant files and builds a minimal context payload
# for worker sub-agents. Workers must never curate their own initial context.
#
# Usage: curator.sh --task "fix NPE in DispositionPushController"
#                   --ticket SPV-3
#                   --role backend-fix
#                   [--repo-mapping path/to/REPO_MAPPING.yaml]
#                   [--ac-file path/to/ac.yaml]

set -euo pipefail

# --- Argument parsing ---
TASK=""
TICKET=""
ROLE=""
REPO_MAPPING=""
AC_FILE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --task) TASK="$2"; shift 2 ;;
    --ticket) TICKET="$2"; shift 2 ;;
    --role) ROLE="$2"; shift 2 ;;
    --repo-mapping) REPO_MAPPING="$2"; shift 2 ;;
    --ac-file) AC_FILE="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: curator.sh --task DESCRIPTION --ticket TICKET-ID --role ROLE"
      echo ""
      echo "Roles: backend-fix, frontend-fix, qa-verify, adversarial-review, architecture-spike"
      echo ""
      echo "Outputs a JSON context payload to stdout with:"
      echo "  - relevant_files: files the worker should read"
      echo "  - acceptance_criteria: relevant AC from the ticket"
      echo "  - allowed_tools: tool whitelist for the worker"
      echo "  - context_summary: one-paragraph task context"
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$TASK" ]] || { echo "ERROR: --task required" >&2; exit 1; }
[[ -n "$TICKET" ]] || { echo "ERROR: --ticket required" >&2; exit 1; }
[[ -n "$ROLE" ]] || { echo "ERROR: --role required" >&2; exit 1; }

# --- Toolbelt assembly by role ---
case "$ROLE" in
  backend-fix|frontend-fix)
    TOOLS='["Read", "Write", "Edit", "Bash", "Grep", "Glob"]'
    ;;
  qa-verify)
    TOOLS='["Read", "Bash", "Grep", "Glob"]'
    ;;
  adversarial-review)
    TOOLS='["Read", "Grep", "Glob"]'
    ;;
  architecture-spike)
    TOOLS='["Read", "Grep", "Glob", "Bash"]'
    ;;
  *)
    echo "WARN: Unknown role '$ROLE', using full toolset" >&2
    TOOLS='["Read", "Write", "Edit", "Bash", "Grep", "Glob"]'
    ;;
esac

# --- Find ticket folder ---
TICKET_DIR=""
# Try direct path first
for base in "tickets/$TICKET" "tickets/*/$TICKET"; do
  found=$(find . -path "./$base" -type d 2>/dev/null | head -1)
  if [[ -n "$found" ]]; then
    TICKET_DIR="$found"
    break
  fi
done

# --- Extract relevant files via keyword search ---
# Extract keywords from task description (simple: split on spaces, filter short words)
KEYWORDS=$(echo "$TASK" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '\n' | awk 'length >= 4' | head -10)

RELEVANT_FILES="[]"
if [[ -n "$KEYWORDS" ]]; then
  FILE_LIST=""
  for kw in $KEYWORDS; do
    # Search for keyword in source files (Java, TypeScript, YAML, etc.)
    matches=$(grep -rl --include='*.java' --include='*.ts' --include='*.tsx' --include='*.yaml' --include='*.yml' --include='*.sh' "$kw" . 2>/dev/null | head -5 || true)
    if [[ -n "$matches" ]]; then
      FILE_LIST="$FILE_LIST
$matches"
    fi
  done

  if [[ -n "$FILE_LIST" ]]; then
    # Deduplicate and limit to 15 files
    RELEVANT_FILES=$(echo "$FILE_LIST" | sort -u | head -15 | jq -R -s 'split("\n") | map(select(length > 0))')
  fi
fi

# --- Extract acceptance criteria ---
AC_CONTENT="[]"
if [[ -n "$AC_FILE" ]] && [[ -f "$AC_FILE" ]]; then
  AC_CONTENT=$(cat "$AC_FILE" | jq -R -s 'split("\n") | map(select(length > 0))' 2>/dev/null || echo "[]")
elif [[ -n "$TICKET_DIR" ]]; then
  AC_PATH="$TICKET_DIR/jira/ac.yaml"
  if [[ -f "$AC_PATH" ]]; then
    AC_CONTENT=$(cat "$AC_PATH" | jq -R -s 'split("\n") | map(select(length > 0))' 2>/dev/null || echo "[]")
  fi
fi

# --- Build context summary ---
CONTEXT_SUMMARY="Task: $TASK. Ticket: $TICKET. Role: $ROLE."
if [[ -n "$TICKET_DIR" ]] && [[ -f "$TICKET_DIR/README.md" ]]; then
  # Extract first paragraph of README for context
  README_SUMMARY=$(head -20 "$TICKET_DIR/README.md" | grep -v '^#' | grep -v '^$' | head -3 | tr '\n' ' ')
  CONTEXT_SUMMARY="$CONTEXT_SUMMARY Context: $README_SUMMARY"
fi

# --- Output JSON payload ---
jq -n \
  --arg task "$TASK" \
  --arg ticket "$TICKET" \
  --arg role "$ROLE" \
  --argjson relevant_files "$RELEVANT_FILES" \
  --argjson acceptance_criteria "$AC_CONTENT" \
  --argjson allowed_tools "$TOOLS" \
  --arg context_summary "$CONTEXT_SUMMARY" \
  '{
    task: $task,
    ticket: $ticket,
    role: $role,
    relevant_files: $relevant_files,
    acceptance_criteria: $acceptance_criteria,
    allowed_tools: $allowed_tools,
    context_summary: $context_summary
  }'
