#!/bin/bash
# Disk usage scan: overall capacity + ranked list of common space-hogging locations.
# Read-only. Deletes nothing.
#
# Usage:
#   scan.sh            full scan (capacity + ranked locations)
#   scan.sh --df-only  capacity only (use this for the after-shot)
#
# On APFS macOS, "/" is the sealed read-only system volume. Its capacity stays low
# while the Data volume (where user files live) is full. Always measure both and
# report the worst one. DATA_VOLUME is overridable for tests and non-APFS hosts.

DATA_VOLUME="${DATA_VOLUME:-/System/Volumes/Data}"

report_capacity() {
  local volumes=(/)
  [ -d "$DATA_VOLUME" ] && volumes+=("$DATA_VOLUME")

  echo "=== Overall disk usage ==="
  df -h "${volumes[@]}"
  df -P -k "${volumes[@]}" | awk '
    NR > 1 {
      cap = $5; sub("%", "", cap)
      if (vol == "" || cap + 0 > worst) { worst = cap + 0; vol = $NF; avail = $4 }
    }
    END {
      if (vol == "") { print "CAPACITY_VERDICT: unknown (df returned no volumes)"; exit }
      printf "CAPACITY_VERDICT: %d%% used on %s (%.1f GiB available)\n", worst, vol, avail / 1048576
    }'
}

report_capacity
[ "$1" = "--df-only" ] && exit 0

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
if command -v brew >/dev/null 2>&1; then
  BREW_CACHE=$(brew --cache 2>/dev/null)
  [ -n "$BREW_CACHE" ] && du -sh "$BREW_CACHE" 2>/dev/null
  echo "Homebrew reclaimable (dry run of 'brew cleanup --prune=all'; includes /opt/homebrew, not only the cache):"
  HOMEBREW_NO_AUTO_UPDATE=1 brew cleanup -n --prune=all 2>/dev/null | tail -1
fi
command -v docker >/dev/null 2>&1 && docker system df 2>/dev/null

echo
echo "=== Trash ==="
du -sh ~/.Trash 2>/dev/null

echo
echo "=== Possible duplicate directory names in Downloads (name minus trailing ' N' / '(N)') ==="
find ~/Downloads -maxdepth 1 -mindepth 1 2>/dev/null \
  | sed -E 's/ [0-9]+$//; s/\([0-9]+\)$//' \
  | sort | uniq -d
