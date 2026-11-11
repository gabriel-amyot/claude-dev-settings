#!/bin/bash
# Gate for transcript-only (private) mode: refuse an output directory that git or a
# notes vault can pick up. Read-only. Creates nothing.
#
# Usage: check_private_dest.sh <output-dir>
# Exit 0 = safe ("SAFE <dir>"). Exit 1 = refused ("REFUSED <reason>"). Exit 2 = usage error.
#
# Refused when the directory, or its nearest existing ancestor, is:
#   - inside a git work tree
#   - inside an Obsidian vault (an ancestor holds .obsidian/)
#   - inside a meetings or weekly-notes tree (path segment "meetings" or "weekly")

dest="$1"
[ -n "$dest" ] || { echo "usage: check_private_dest.sh <output-dir>" >&2; exit 2; }

probe="$dest"
while [ ! -d "$probe" ]; do
  parent=$(dirname "$probe")
  [ "$parent" = "$probe" ] && break
  probe="$parent"
done
abs=$(cd "$probe" 2>/dev/null && pwd -P) || { echo "REFUSED cannot resolve $dest"; exit 1; }

if git -C "$abs" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "REFUSED $dest is inside git work tree $(git -C "$abs" rev-parse --show-toplevel)"
  exit 1
fi

walk="$abs"
while :; do
  if [ -d "$walk/.obsidian" ]; then
    echo "REFUSED $dest is inside notes vault $walk"
    exit 1
  fi
  [ "$walk" = "/" ] && break
  walk=$(dirname "$walk")
done

case "/$(printf '%s' "$dest" | tr '[:upper:]' '[:lower:]')/" in
  */meetings/*|*/weekly/*|*/weekly-notes/*)
    echo "REFUSED $dest is a meetings or weekly-notes path"
    exit 1 ;;
esac

echo "SAFE $dest"
exit 0
