#!/usr/bin/env bash
# Reproduce the Claude Code harness on a second machine.
#
# Run after cloning this repo to ~/.claude-shared-config:
#   bash ~/.claude-shared-config/bootstrap.sh
#
# Idempotent. Safe to re-run after a git pull.

set -euo pipefail

SHARED="$HOME/.claude-shared-config"
CLAUDE="$HOME/.claude"

if [ ! -d "$SHARED" ]; then
  echo "ERROR: $SHARED does not exist. Clone the repo there first." >&2
  exit 1
fi

mkdir -p "$CLAUDE"

echo "==> Linking shared directories into $CLAUDE"
for item in agents commands context docs git-hooks hooks library skills CLAUDE.md; do
  target="$SHARED/$item"
  link="$CLAUDE/$item"
  if [ ! -e "$target" ]; then
    echo "    skip $item (not in shared-config)"
    continue
  fi
  if [ -L "$link" ]; then
    rm "$link"
  elif [ -e "$link" ]; then
    backup="$link.pre-bootstrap.$(date +%Y%m%d%H%M%S)"
    echo "    existing $item moved to $(basename "$backup")"
    mv "$link" "$backup"
  fi
  ln -s "$target" "$link"
  echo "    linked $item"
done

echo "==> Restoring loose config from claude-home/"
for item in crawl-profiles deploy-identity harness; do
  [ -d "$SHARED/claude-home/$item" ] || continue
  mkdir -p "$CLAUDE/$item"
  rsync -a "$SHARED/claude-home/$item/" "$CLAUDE/$item/"
  echo "    restored $item/"
done
for f in statusline-command.sh pmd-java-gate.json harness-scorecard.yaml; do
  [ -f "$SHARED/claude-home/$f" ] || continue
  cp "$SHARED/claude-home/$f" "$CLAUDE/$f"
  echo "    restored $f"
done
[ -f "$CLAUDE/statusline-command.sh" ] && chmod +x "$CLAUDE/statusline-command.sh"

if [ -f "$CLAUDE/settings.json" ]; then
  echo "    settings.json already present, NOT overwritten"
  echo "    compare: diff $SHARED/claude-home/settings.json $CLAUDE/settings.json"
else
  cp "$SHARED/claude-home/settings.json" "$CLAUDE/settings.json"
  chmod 600 "$CLAUDE/settings.json"
  echo "    restored settings.json"
fi

echo "==> Restoring plugins"
mkdir -p "$CLAUDE/plugins"
for p in klever-mech-suit klever-wiki sprint-harness; do
  [ -d "$SHARED/plugins/$p" ] || continue
  rsync -a "$SHARED/plugins/$p/" "$CLAUDE/plugins/$p/"
  echo "    restored plugins/$p"
done
if [ -d "$SHARED/plugins/local-marketplace-backup" ]; then
  rsync -a "$SHARED/plugins/local-marketplace-backup/" "$CLAUDE/plugins/local-marketplace/"
  rm -f "$CLAUDE/plugins/local-marketplace/BACKUP-NOTE.md"
  echo "    restored plugins/local-marketplace"
fi
for j in blocklist.json install-counts-cache.json installed_plugins.json known_marketplaces.json; do
  [ -f "$SHARED/plugins/$j" ] || continue
  [ -f "$CLAUDE/plugins/$j" ] || cp "$SHARED/plugins/$j" "$CLAUDE/plugins/$j"
done

echo "==> Linking the ledger helper onto PATH"
mkdir -p "$CLAUDE/bin"
ledger_src="$CLAUDE/plugins/local-marketplace/session/bin/ledger.py"
if [ -f "$ledger_src" ]; then
  chmod +x "$ledger_src"
  ln -sf "$ledger_src" "$CLAUDE/bin/ledger"
  echo "    linked $CLAUDE/bin/ledger"
fi
case ":$PATH:" in
  *":$CLAUDE/bin:"*) ;;
  *) echo "    ADD TO SHELL PROFILE: export PATH=\"\$HOME/.claude/bin:\$PATH\"" ;;
esac

echo
echo "Done. Verify with:"
echo "  ls -la $CLAUDE | grep '\->'"
echo "  command -v ledger"
echo
echo "NOTE: hook commands in settings.json use absolute paths under"
echo "$HOME. They work only if the second machine uses the same username."
