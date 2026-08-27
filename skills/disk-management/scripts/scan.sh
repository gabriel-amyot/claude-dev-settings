#!/bin/bash
# Disk usage scan: overall capacity + ranked list of common space-hogging locations.
# Read-only. Deletes nothing.

echo "=== Overall disk usage ==="
df -h /

echo
echo "=== Top-level Application Support (sorted) ==="
du -sh ~/Library/Application\ Support/*/ 2>/dev/null | sort -rh | head -20

echo
echo "=== Top-level Caches (sorted) ==="
du -sh ~/Library/Caches/*/ 2>/dev/null | sort -rh | head -20

echo
echo "=== Downloads (top-level items, sorted) ==="
du -sh ~/Downloads/*/ ~/Downloads/* 2>/dev/null | sort -rh | head -20

echo
echo "=== Dev tool caches ==="
du -sh ~/.npm 2>/dev/null
du -sh ~/Library/Caches/pip 2>/dev/null
du -sh ~/Library/Developer 2>/dev/null
BREW_CACHE=$(brew --cache 2>/dev/null)
[ -n "$BREW_CACHE" ] && du -sh "$BREW_CACHE" 2>/dev/null
command -v docker >/dev/null 2>&1 && docker system df 2>/dev/null

echo
echo "=== Trash ==="
du -sh ~/.Trash 2>/dev/null

echo
echo "=== Possible duplicate directory names in Downloads (name minus trailing ' N' / '(N)') ==="
find ~/Downloads -maxdepth 1 -mindepth 1 2>/dev/null \
  | sed -E 's/ [0-9]+$//; s/\([0-9]+\)$//' \
  | sort | uniq -d
