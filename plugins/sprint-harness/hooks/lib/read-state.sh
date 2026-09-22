#!/bin/bash
# Shared library for reading sprint-harness-state.yaml
# Sources into other hook scripts. Provides get_state() and state helper functions.
# Designed for simple flat YAML (no nested objects). Uses grep/sed, no yq dependency.

STATE_FILE=".claude/sprint-harness-state.yaml"

# Find state file by walking up from CWD or using CLAUDE_PROJECT_DIR
find_state_file() {
  if [ -n "$CLAUDE_PROJECT_DIR" ] && [ -f "$CLAUDE_PROJECT_DIR/$STATE_FILE" ]; then
    echo "$CLAUDE_PROJECT_DIR/$STATE_FILE"
    return 0
  fi
  local dir="$PWD"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/$STATE_FILE" ]; then
      echo "$dir/$STATE_FILE"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

# Read a scalar value from the state file. Usage: get_state "phase"
get_state() {
  local key="$1"
  local file
  file="$(find_state_file)" || return 1
  grep -E "^${key}:" "$file" | head -1 | sed "s/^${key}:[[:space:]]*//" | sed 's/^["'"'"']//' | sed 's/["'"'"']$//' | tr -d '\r'
}

# Check if harness is active (state file exists and active: true)
is_harness_active() {
  local active
  active="$(get_state "active")" || return 1
  [ "$active" = "true" ]
}

# Read a YAML list as newline-separated values. Usage: get_state_list "completed_acs"
get_state_list() {
  local key="$1"
  local file
  file="$(find_state_file)" || return 1
  # Handle inline list: [item1, item2]
  local inline
  inline="$(grep -E "^${key}:" "$file" | head -1 | sed "s/^${key}:[[:space:]]*//")"
  if echo "$inline" | grep -qE '^\['; then
    echo "$inline" | tr -d '[]' | tr ',' '\n' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//' | sed '/^$/d'
    return 0
  fi
  # Handle block list:
  #   - item1
  #   - item2
  local in_list=false
  while IFS= read -r line; do
    if echo "$line" | grep -qE "^${key}:"; then
      in_list=true
      continue
    fi
    if $in_list; then
      if echo "$line" | grep -qE '^[[:space:]]+-'; then
        echo "$line" | sed 's/^[[:space:]]*-[[:space:]]*//' | sed 's/^["'"'"']//' | sed 's/["'"'"']$//'
      else
        break
      fi
    fi
  done < "$file"
}

# Get the project dir (the directory containing .claude/)
get_project_dir() {
  local file
  file="$(find_state_file)" || return 1
  # State file is at {project}/.claude/sprint-harness-state.yaml
  # So project dir is two levels up from the file
  local claude_dir
  claude_dir="$(dirname "$file")"
  dirname "$claude_dir"
}
