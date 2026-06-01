#!/usr/bin/env bash
# Worktree Guard: PreToolUse hook for Edit and Write
# Blocks edits in the main worktree of any code repo. All code edits must
# happen in git worktrees. project-management repos are exempt.
#
# Detection: git rev-parse --git-dir vs --git-common-dir
#   Main worktree: both resolve to the same .git directory
#   Worktree: --git-dir points to .git/worktrees/<name>, --git-common-dir to shared .git
#
# Exit 0 = allow the edit
# Exit 2 = BLOCK the edit (stdout shown to agent as reason)

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', data)
print(ti.get('file_path', ti.get('filePath', '')))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Only guard files under ~/Developer/
case "$FILE_PATH" in
  "$HOME/Developer/"*) ;;
  *) exit 0 ;;
esac

# Exempt project-management repos (documentation, not code)
case "$FILE_PATH" in
  *"/project-management/"*) exit 0 ;;
esac

# Find the first existing ancestor directory of the file
# (Write tool can target non-existent subdirs; walking up prevents that bypass)
FILE_DIR=$(dirname "$FILE_PATH")
while [ ! -d "$FILE_DIR" ] && [ "$FILE_DIR" != "/" ]; do
  FILE_DIR=$(dirname "$FILE_DIR")
done
if [ ! -d "$FILE_DIR" ] || [ "$FILE_DIR" = "/" ]; then
  exit 0
fi

# Must be inside a git repo
REPO_ROOT=$(git -C "$FILE_DIR" rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  exit 0
fi

# Detect main worktree vs linked worktree
GIT_DIR=$(git -C "$FILE_DIR" rev-parse --git-dir 2>/dev/null)
GIT_COMMON=$(git -C "$FILE_DIR" rev-parse --git-common-dir 2>/dev/null)

if [ -z "$GIT_DIR" ] || [ -z "$GIT_COMMON" ]; then
  exit 0
fi

# Resolve to absolute paths for reliable comparison
GIT_DIR_ABS=$(cd "$FILE_DIR" && cd "$GIT_DIR" && pwd 2>/dev/null)
GIT_COMMON_ABS=$(cd "$FILE_DIR" && cd "$GIT_COMMON" && pwd 2>/dev/null)

if [ "$GIT_DIR_ABS" = "$GIT_COMMON_ABS" ]; then
  REPO_NAME=$(basename "$REPO_ROOT")
  echo "BLOCKED: Editing in main worktree of '$REPO_NAME' ($REPO_ROOT)."
  echo ""
  echo "Main worktrees must stay clean. All code edits happen in git worktrees."
  echo ""
  echo "Recovery:"
  echo "  1. git -C $REPO_ROOT fetch origin"
  echo "  2. Invoke superpowers:using-git-worktrees to create an isolated workspace"
  echo ""
  echo "The skill handles directory selection and branch setup."
  exit 2
fi

# We're in a linked worktree — allow
exit 0
