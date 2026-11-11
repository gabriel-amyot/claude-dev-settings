#!/bin/bash
# Size each deletion candidate on its own, so a question never shows only a parent total.
# Read-only. Deletes nothing.
#
# Usage:
#   size_items.sh <path> [<path> ...]   size each named path
#   size_items.sh --children <dir>      size each direct child of <dir>
#
# Output: one "ITEM <size> <path>" line per item, largest first, then "TOTAL <size>".

human() {
  awk -v kib="$1" 'BEGIN {
    if (kib >= 1048576) printf "%.1fG", kib / 1048576
    else if (kib >= 1024) printf "%.1fM", kib / 1024
    else printf "%dK", kib
  }'
}

if [ "$1" = "--children" ]; then
  [ -d "$2" ] || { echo "size_items.sh: not a directory: $2" >&2; exit 2; }
  set -- "$2"/*
fi
[ $# -gt 0 ] || { echo "usage: size_items.sh <path>... | --children <dir>" >&2; exit 2; }

total=0
rows=""
for item in "$@"; do
  [ -e "$item" ] || continue
  kib=$(du -sk "$item" 2>/dev/null | awk '{print $1}')
  [ -n "$kib" ] || continue
  total=$((total + kib))
  rows+="$kib"$'\t'"$item"$'\n'
done

printf '%s' "$rows" | sort -t$'\t' -k1,1nr | while IFS=$'\t' read -r kib item; do
  [ -n "$kib" ] && echo "ITEM $(human "$kib") $item"
done
echo "TOTAL $(human "$total")"
