#!/usr/bin/env bash
# Branch Guard: PreToolUse hook for Edit and Write
# Blocks edits to files in git repos when the branch is already merged to dev
# or is a protected branch (dev/main/master). Prevents the KTP-669 wrong-branch
# incident from recurring.
#
# Exit 0 = allow the edit
# Exit non-zero = BLOCK the edit (stdout shown to agent as reason)

# Read tool input from stdin (correct API per spec-guard.sh pattern)
INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', data)
print(ti.get('file_path', ti.get('filePath', '')))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Only guard files under ~/Developer/ (skip project-management, config, etc.)
case "$FILE_PATH" in
  "$HOME/Developer/"*)
    ;;
  /tmp/*)
    # Worktrees in /tmp are fine — that's the intended workflow
    exit 0
    ;;
  *)
    exit 0
    ;;
esac

# Skip project-management (documentation repo, not code)
case "$FILE_PATH" in
  *"/project-management/"*)
    exit 0
    ;;
esac

# Find git repo root for this file
FILE_DIR=$(dirname "$FILE_PATH")
if [ ! -d "$FILE_DIR" ]; then
  exit 0
fi

REPO_ROOT=$(git -C "$FILE_DIR" rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  exit 0
fi

# Get current branch
BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)
if [ -z "$BRANCH" ]; then
  # Detached HEAD or error — allow (edge case, don't block)
  exit 0
fi

# Check 1: Is it a protected branch?
case "$BRANCH" in
  dev|main|master|uat|staging|production)
    echo "BLOCKED: You are on protected branch '$BRANCH' in $REPO_ROOT."
    echo "Create a fresh feature branch first:"
    echo "  git -C $REPO_ROOT checkout -b KTP-XXX-description origin/dev"
    echo "Or use a worktree:"
    echo "  git worktree add /tmp/KTP-XXX -b KTP-XXX-description origin/dev"
    exit 1
    ;;
esac

# Check 2: Is the branch already merged to origin/dev?
# Use local refs only (no network call) for speed. Acceptable false-negative
# if origin/dev is stale — the hook is defense-in-depth, not sole safeguard.
if git -C "$REPO_ROOT" rev-parse --verify origin/dev >/dev/null 2>&1; then
  # git branch output prefixes: "* " (current), "+ " (worktree), "  " (normal)
  # Strip all prefix characters before matching
  MERGED=$(git -C "$REPO_ROOT" branch --merged origin/dev 2>/dev/null | sed 's/^[* +]*//' | grep -E "^${BRANCH}$")
  if [ -n "$MERGED" ]; then
    echo "BLOCKED: Branch '$BRANCH' is already merged to dev in $REPO_ROOT."
    echo "This branch's work is already in dev. Create a fresh feature branch:"
    echo "  git -C $REPO_ROOT fetch origin"
    echo "  git -C $REPO_ROOT checkout -b KTP-XXX-description origin/dev"
    echo "Or use a worktree:"
    echo "  git worktree add /tmp/KTP-XXX -b KTP-XXX-description origin/dev"
    exit 1
  fi
fi

# All checks passed — allow the edit
exit 0
