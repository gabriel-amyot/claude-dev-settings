#!/usr/bin/env bash
# PM Single-Trunk Guard: PreToolUse hook for Bash
#
# project-management is a BACKUP-ONLY working directory: one trunk (main),
# no feature branches, no worktrees. This guard blocks git commands that
# would CREATE a branch or worktree when the target repo is project-management.
#
# It deliberately does NOT block:
#   - deletion/cleanup (branch -d/-D, worktree remove/prune)
#   - read-only listing (branch -a, worktree list)
#   - branch/worktree creation in ANY OTHER repo (code repos must use worktrees)
#   - commands that merely *mention* these strings (echo, grep, test harnesses,
#     heredocs) — it anchors on an actual `git ...` invocation at a command
#     segment boundary, not a substring match.
#
# Exit 0 = allow. Exit 2 = BLOCK (stdout shown to the agent as the reason).

INPUT=$(cat)

RESULT=$(CLAUDE_PM_GUARD_INPUT="$INPUT" python3 -c '
import os, json, re

raw = os.environ.get("CLAUDE_PM_GUARD_INPUT", "")
try:
    d = json.loads(raw)
except Exception:
    print("ALLOW"); raise SystemExit

ti = d.get("tool_input", d)
cmd = ti.get("command") or ""
cwd = d.get("cwd") or ""

# Split the command line into segments at shell boundaries so that a "git"
# mentioned inside a quoted argument (printf/echo/grep/JSON) is NOT treated
# as an invocation. We only inspect segments that *start* with "git".
segments = re.split(r"&&|\|\||;|\||\n|\$\(|`", cmd)

CREATE = re.compile(
    r"^git\b.*\b(worktree\s+add|checkout\s+-[bB]\b|switch\s+-[cC]\b|branch\s+-b\b)"
)

def target_of(seg):
    m = re.search(r"git\s+-C\s+(\S+)", seg)
    return m.group(1) if m else cwd

blocked = False
for seg in segments:
    seg = seg.lstrip(" \t(")
    if not seg.startswith("git"):
        continue
    if not CREATE.search(seg):
        continue
    if "/project-management" in target_of(seg):
        blocked = True
        break

print("BLOCK" if blocked else "ALLOW")
' 2>/dev/null)

if [ "$RESULT" = "BLOCK" ]; then
  # Exit 2 blocks the tool; the reason must go to STDERR to be shown to the agent.
  {
    echo "BLOCKED: project-management is a backup-only working directory."
    echo ""
    echo "It uses a SINGLE trunk (main) with no feature branches and no worktrees."
    echo "Git here is just a backup of accumulated tickets, knowledge, and sessions."
    echo ""
    echo "Do not create branches or worktrees in project-management. If a skill"
    echo "wants isolation (dark-factory, sprint-factory, Workflow isolation:worktree),"
    echo "run it against an actual code repo under ~/Developer/, never here."
    echo ""
    echo "Just edit files directly on main and let them be committed."
  } >&2
  exit 2
fi

exit 0
