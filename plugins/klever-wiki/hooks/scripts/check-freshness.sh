#!/bin/bash
# Klever Wiki Freshness Check — runs on SessionStart
# Scans cached wiki pages for staleness and reports to agent context

WIKI_DIR="$HOME/Developer/grp-beklever-com/project-management/documentation/notion-wiki/pages"
THRESHOLD_DAYS=7
SOP_THRESHOLD_DAYS=3
TODAY=$(date +%Y-%m-%d)

if [ ! -d "$WIKI_DIR" ]; then
  exit 0
fi

stale_count=0
sop_stale_count=0
stale_pages=""

for file in "$WIKI_DIR"/*.md; do
  [ -f "$file" ] || continue

  basename=$(basename "$file")

  # Extract last_cached from frontmatter
  last_cached=$(grep "^last_cached:" "$file" 2>/dev/null | head -1 | sed 's/last_cached: *//')

  if [ -z "$last_cached" ]; then
    stale_count=$((stale_count + 1))
    stale_pages="$stale_pages  - $basename (never cached)\n"
    continue
  fi

  # Calculate age in days
  if command -v gdate &>/dev/null; then
    cached_epoch=$(gdate -d "$last_cached" +%s 2>/dev/null)
    today_epoch=$(gdate -d "$TODAY" +%s)
  else
    cached_epoch=$(date -j -f "%Y-%m-%d" "$last_cached" +%s 2>/dev/null)
    today_epoch=$(date -j -f "%Y-%m-%d" "$TODAY" +%s 2>/dev/null)
  fi

  if [ -n "$cached_epoch" ] && [ -n "$today_epoch" ]; then
    age_days=$(( (today_epoch - cached_epoch) / 86400 ))

    if [ "$age_days" -gt "$THRESHOLD_DAYS" ]; then
      stale_count=$((stale_count + 1))
      stale_pages="$stale_pages  - $basename ($age_days days old)\n"
    fi
  fi
done

total_pages=$(find "$WIKI_DIR" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

if [ "$stale_count" -gt 0 ]; then
  echo "Klever Wiki cache: $stale_count of $total_pages summary pages are stale (>$THRESHOLD_DAYS days)."
  echo "Run /wiki-refresh to update, or pages will refresh lazily on access."
  printf "$stale_pages"
else
  echo "Klever Wiki cache: all $total_pages summary pages are fresh."
fi
