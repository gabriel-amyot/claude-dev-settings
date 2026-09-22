#!/usr/bin/env bash
# ~/.claude/statusline-command.sh
# Claude Code status line — reads JSON from stdin

input=$(cat)

# Extract fields
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
model=$(echo "$input" | jq -r '.model.display_name // ""')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
remaining_pct=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')
session_name=$(echo "$input" | jq -r '.session_name // empty')
vim_mode=$(echo "$input" | jq -r '.vim.mode // empty')
worktree_branch=$(echo "$input" | jq -r '.worktree.branch // empty')
git_worktree=$(echo "$input" | jq -r '.workspace.git_worktree // empty')

# Shorten cwd: replace $HOME with ~
home="$HOME"
short_cwd="${cwd/#$home/\~}"

# Build the status line parts
parts=()

# Directory
[ -n "$short_cwd" ] && parts+=("$short_cwd")

# Git branch (from worktree if available)
branch=""
if [ -n "$worktree_branch" ]; then
  branch="$worktree_branch"
elif [ -n "$git_worktree" ]; then
  branch="$git_worktree"
else
  branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null)
fi
[ -n "$branch" ] && parts+=("[$branch]")

# Model
[ -n "$model" ] && parts+=("$model")

# Context usage
if [ -n "$used_pct" ]; then
  ctx=$(printf "ctx:%.0f%%" "$used_pct")
  parts+=("$ctx")
fi

# Session name (only if set)
[ -n "$session_name" ] && parts+=("{$session_name}")

# Vim mode (only if active)
[ -n "$vim_mode" ] && parts+=("[$vim_mode]")

# Rate limits: 5h window
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
[ -n "$five_pct" ] && parts+=("5h:$(printf '%.0f' "$five_pct")%")

# Join with separator
printf '%s' "$(IFS=" | "; echo "${parts[*]}")"
