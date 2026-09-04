#!/usr/bin/env bash
# Passive SessionStart audit for the shared Claude Code and Codex harness.
#
# Invariant: ~/.claude-shared-config is the only owner of skills and hook
# implementations. ~/.agents/skills and ~/.codex/hooks are adapters only:
# every managed entry there must be a symlink to the matching shared entry.
# The former shared-overlay exception is retired. A real consumer directory is
# drift, even when a third-party installer created it. ~/.claude remains local
# machine configuration and is checked only for hook mappings, never for files.

set -u

HOME_DIR="${HARNESS_HOME:-$HOME}"
SHARED="$HOME_DIR/.claude-shared-config"
SHARED_SKILLS="$SHARED/skills"
SHARED_HOOKS="$SHARED/hooks"
AGENT_SKILLS="$HOME_DIR/.agents/skills"
CODEX_HOME="$HOME_DIR/.codex"
CODEX_HOOKS="$CODEX_HOME/hooks"
CLAUDE_SETTINGS="$HOME_DIR/.claude/settings.json"
CODEX_HOOKS_CONFIG="$CODEX_HOME/hooks.json"
SKILL_ARCHIVE="$SHARED_SKILLS/_archive"

INPUT_ERRORS=()
SHARED_SOURCE_ERRORS=()
MISSING_ADAPTERS=()
CONSUMER_CONTENT=()
BROKEN_LINKS=()
RETIRED_LINKS=()
WRONG_LINKS=()
CLAUDE_MAPPING_MISSING=()
CODEX_MAPPING_MISSING=()

add_input_error() { INPUT_ERRORS+=("$1"); }
add_shared_source_error() { SHARED_SOURCE_ERRORS+=("$1"); }
add_missing_adapter() { MISSING_ADAPTERS+=("$1"); }
add_consumer_content() { CONSUMER_CONTENT+=("$1"); }
add_broken_link() { BROKEN_LINKS+=("$1"); }
add_retired_link() { RETIRED_LINKS+=("$1"); }
add_wrong_link() { WRONG_LINKS+=("$1"); }
add_claude_mapping_missing() { CLAUDE_MAPPING_MISSING+=("$1"); }
add_codex_mapping_missing() { CODEX_MAPPING_MISSING+=("$1"); }

is_ignored_skill_entry() {
  case "$1" in
    _archive|_backup-*|templates|__pycache__|INDEX.md|.DS_Store|.*|*.pyc|*.swp|*.tmp|*~)
      return 0
      ;;
  esac
  return 1
}

is_ignored_hook_entry() {
  case "$1" in
    _archive|_backup-*|templates|__pycache__|evals|usage-cache|peon-ping|INDEX.md|.DS_Store|*.pyc|*.swp|*.tmp|*~)
      return 0
      ;;
  esac
  return 1
}

is_retired_skill_link() {
  link="$1"
  name="$2"

  [ -d "$SKILL_ARCHIVE" ] || return 1

  if [ -e "$SKILL_ARCHIVE/$name" ]; then
    if [ ! -e "$link" ] || [ "$link" -ef "$SKILL_ARCHIVE/$name" ]; then
      return 0
    fi
  fi

  for archived in "$SKILL_ARCHIVE"/*; do
    [ -e "$archived" ] || [ -L "$archived" ] || continue
    [ "$link" -ef "$archived" ] && return 0
  done

  return 1
}

runtime_maps_hook() {
  config="$1"
  runtime_hooks="$2"
  name="$3"

  grep -F "$runtime_hooks/$name" "$config" >/dev/null 2>&1
}

report_group() {
  label="$1"
  count="$2"
  shift 2

  [ "$count" -gt 0 ] || return 0

  printf '  %s (%s):\n' "$label" "$count" >&2
  for item in "$@"; do
    printf '    - %s\n' "$item" >&2
  done
}

[ -d "$SHARED_SKILLS" ] || add_input_error "shared skills directory is unavailable: $SHARED_SKILLS"
[ -d "$SHARED_HOOKS" ] || add_input_error "shared hooks directory is unavailable: $SHARED_HOOKS"
[ -d "$AGENT_SKILLS" ] || add_input_error "Codex skills adapter directory is unavailable: $AGENT_SKILLS"
[ -d "$CODEX_HOOKS" ] || add_input_error "Codex hooks adapter directory is unavailable: $CODEX_HOOKS"

CLAUDE_SETTINGS_READABLE=0
CODEX_HOOKS_CONFIG_READABLE=0

if [ -r "$CLAUDE_SETTINGS" ]; then
  CLAUDE_SETTINGS_READABLE=1
else
  add_input_error "Claude hook configuration is unreadable: $CLAUDE_SETTINGS"
fi

if [ -r "$CODEX_HOOKS_CONFIG" ]; then
  CODEX_HOOKS_CONFIG_READABLE=1
else
  add_input_error "Codex hook configuration is unreadable: $CODEX_HOOKS_CONFIG"
fi

# Shared skills must be real directories. Consumer entries must resolve to them.
for source in "$SHARED_SKILLS"/*; do
  [ -e "$source" ] || [ -L "$source" ] || continue
  name="${source##*/}"
  is_ignored_skill_entry "$name" && continue

  if [ -L "$source" ]; then
    add_shared_source_error "skill source is a symlink, not shared content: $name"
    continue
  fi

  [ -d "$source" ] || continue
  target="$AGENT_SKILLS/$name"

  if [ ! -e "$target" ] && [ ! -L "$target" ]; then
    add_missing_adapter "skill has no Codex adapter: $name"
  fi
done

# Report every managed consumer skill that is not the exact shared symlink.
for target in "$AGENT_SKILLS"/*; do
  [ -e "$target" ] || [ -L "$target" ] || continue
  name="${target##*/}"
  is_ignored_skill_entry "$name" && continue
  source="$SHARED_SKILLS/$name"

  if [ ! -L "$target" ]; then
    add_consumer_content "real skill content in ~/.agents/skills: $name"
  elif is_retired_skill_link "$target" "$name"; then
    add_retired_link "skill link points to retired content: $name"
  elif [ ! -e "$target" ]; then
    add_broken_link "broken skill link: $name"
  elif [ ! -d "$source" ] || [ -L "$source" ] || ! [ "$target" -ef "$source" ]; then
    add_wrong_link "skill link does not resolve to shared source: $name"
  fi
done

# Every meaningful top-level hook entry is shared content and needs a Codex link.
# Only executable regular files are hook implementations, so only they require
# runtime mappings. Fixtures, caches, documentation, and editor artifacts skip.
for source in "$SHARED_HOOKS"/*; do
  [ -e "$source" ] || [ -L "$source" ] || continue
  name="${source##*/}"
  is_ignored_hook_entry "$name" && continue

  if [ -L "$source" ]; then
    add_shared_source_error "hook source is a symlink, not shared content: $name"
    continue
  fi

  target="$CODEX_HOOKS/$name"

  if [ ! -e "$target" ] && [ ! -L "$target" ]; then
    add_missing_adapter "hook has no Codex adapter: $name"
  fi

  if [ -f "$source" ] && [ -x "$source" ]; then
    if [ "$CLAUDE_SETTINGS_READABLE" -eq 1 ] && ! runtime_maps_hook "$CLAUDE_SETTINGS" "$HOME_DIR/.claude/hooks" "$name"; then
      add_claude_mapping_missing "Claude mapping missing: $name"
    fi

    if [ "$CODEX_HOOKS_CONFIG_READABLE" -eq 1 ] && ! runtime_maps_hook "$CODEX_HOOKS_CONFIG" "$CODEX_HOOKS" "$name"; then
      add_codex_mapping_missing "Codex mapping missing: $name"
    fi
  fi
done

# Report every managed Codex hook that is not the exact shared symlink.
for target in "$CODEX_HOOKS"/*; do
  [ -e "$target" ] || [ -L "$target" ] || continue
  name="${target##*/}"
  is_ignored_hook_entry "$name" && continue
  source="$SHARED_HOOKS/$name"

  if [ ! -L "$target" ]; then
    add_consumer_content "real hook content in ~/.codex/hooks: $name"
  elif [ ! -e "$target" ]; then
    add_broken_link "broken hook link: $name"
  elif [ ! -e "$source" ] || [ -L "$source" ] || ! [ "$target" -ef "$source" ]; then
    add_wrong_link "hook link does not resolve to shared source: $name"
  fi
done

TOTAL=$(( ${#INPUT_ERRORS[@]} + ${#SHARED_SOURCE_ERRORS[@]} + ${#MISSING_ADAPTERS[@]} + ${#CONSUMER_CONTENT[@]} + ${#BROKEN_LINKS[@]} + ${#RETIRED_LINKS[@]} + ${#WRONG_LINKS[@]} + ${#CLAUDE_MAPPING_MISSING[@]} + ${#CODEX_MAPPING_MISSING[@]} ))

if [ "$TOTAL" -gt 0 ]; then
  printf 'HARNESS PARITY WARNING: %s issue(s) found. This audit never blocks a session.\n' "$TOTAL" >&2
  report_group "audit inputs unavailable" "${#INPUT_ERRORS[@]}" ${INPUT_ERRORS[@]+"${INPUT_ERRORS[@]}"}
  report_group "shared sources that are not real content" "${#SHARED_SOURCE_ERRORS[@]}" ${SHARED_SOURCE_ERRORS[@]+"${SHARED_SOURCE_ERRORS[@]}"}
  report_group "shared content missing a Codex adapter" "${#MISSING_ADAPTERS[@]}" ${MISSING_ADAPTERS[@]+"${MISSING_ADAPTERS[@]}"}
  report_group "real content in adapter directories" "${#CONSUMER_CONTENT[@]}" ${CONSUMER_CONTENT[@]+"${CONSUMER_CONTENT[@]}"}
  report_group "broken adapter symlinks" "${#BROKEN_LINKS[@]}" ${BROKEN_LINKS[@]+"${BROKEN_LINKS[@]}"}
  report_group "retired skills still linked" "${#RETIRED_LINKS[@]}" ${RETIRED_LINKS[@]+"${RETIRED_LINKS[@]}"}
  report_group "adapter symlinks with the wrong target" "${#WRONG_LINKS[@]}" ${WRONG_LINKS[@]+"${WRONG_LINKS[@]}"}
  report_group "hook implementations unmapped in Claude" "${#CLAUDE_MAPPING_MISSING[@]}" ${CLAUDE_MAPPING_MISSING[@]+"${CLAUDE_MAPPING_MISSING[@]}"}
  report_group "hook implementations unmapped in Codex" "${#CODEX_MAPPING_MISSING[@]}" ${CODEX_MAPPING_MISSING[@]+"${CODEX_MAPPING_MISSING[@]}"}
fi

exit 0
