#!/usr/bin/env bash
# Passive SessionStart audit for the shared Claude/Codex harness.

set -u

HOME_DIR="${HARNESS_HOME:-$HOME}"
SHARED="$HOME_DIR/.claude-shared-config"
CODEX_HOME="$HOME_DIR/.codex"
AGENT_SKILLS="$HOME_DIR/.agents/skills"
FAILURES=()

fail() {
  FAILURES+=("$1")
}

if [ ! -L "$CODEX_HOME/AGENTS.md" ] || [ ! "$CODEX_HOME/AGENTS.md" -ef "$HOME_DIR/.claude/CLAUDE.md" ]; then
  fail "global Codex instructions are not linked to ~/.claude/CLAUDE.md"
fi

if ! grep -q '^project_doc_fallback_filenames = \["CLAUDE.md"\]$' "$CODEX_HOME/config.toml" 2>/dev/null; then
  fail "Codex project_doc_fallback_filenames does not select CLAUDE.md"
fi

if [ -f "$PWD/CLAUDE.md" ] && [ -e "$PWD/AGENTS.md" ]; then
  fail "$PWD contains both CLAUDE.md and AGENTS.md"
fi

for source in "$SHARED"/skills/*; do
  [ -e "$source" ] || [ -L "$source" ] || continue
  name="$(basename "$source")"
  target="$AGENT_SKILLS/$name"
  if [ -L "$source" ]; then
    [ -d "$target" ] || fail "shared overlay skill is broken: $name"
  elif [ -d "$source" ]; then
    [ -L "$target" ] && [ "$target" -ef "$source" ] || fail "Codex skill is not linked to the shared source: $name"
  fi
done

for source in "$SHARED"/hooks/*; do
  [ -f "$source" ] || continue
  name="$(basename "$source")"
  case "$name" in
    INDEX.md|.DS_Store) continue ;;
  esac
  target="$CODEX_HOME/hooks/$name"
  [ -L "$target" ] && [ "$target" -ef "$source" ] || fail "Codex hook implementation is not linked: $name"
done

for hook in challenge-detect.sh bibliotheque-recall.sh rabbit-hole-guard.sh deploy-identity-guard.sh library-stamp-guard.sh; do
  grep -q "$hook" "$HOME_DIR/.claude/settings.json" 2>/dev/null || fail "Claude hook mapping missing: $hook"
  grep -q "$hook" "$CODEX_HOME/hooks.json" 2>/dev/null || fail "Codex hook mapping missing: $hook"
done

if [ ! -L "$CODEX_HOME/library" ] || [ ! "$CODEX_HOME/library" -ef "$HOME_DIR/.claude/library" ]; then
  fail "Codex library alias is not linked to ~/.claude/library"
fi

if [ "${#FAILURES[@]}" -gt 0 ]; then
  printf 'HARNESS PARITY WARNING: Claude and Codex have drifted:\n' >&2
  printf '  - %s\n' "${FAILURES[@]}" >&2
  printf 'Run ~/.claude-shared-config/tools/harness-parity-check.sh after repairing the adapters.\n' >&2
fi

exit 0
