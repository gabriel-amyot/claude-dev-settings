#!/usr/bin/env python3
"""Find older local work on the same problem as a new ticket.

A new ticket key has no history. The earlier investigation sits under another key
(KTP-1403 vs KTT-48 / KTT-54). So search by symptom and product terms, and by the key.

Ranks ticket and session folders by how many DISTINCT terms they match, so one generic
word ("health") cannot outrank a folder that matches the whole symptom. Prints paths,
match counts and file dates only. It never prints file bodies.

Usage:
  find_prior_work.py --root <PM_ROOT> --key KTP-1403 --term "campaign health" --term "empty response"
Exit: 0 hits found, 1 no hits, 2 bad input.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

SEARCH_DIRS = ("tickets", "sessions", "documentation/bibliotheque")
SUFFIXES = {".md", ".yaml", ".yml"}
MAX_FILE_BYTES = 2_000_000
TICKET_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


def unit_of(path: Path, root: Path) -> str:
    """Group hits by ticket folder, session folder, or library page."""
    parts = path.relative_to(root).parts
    for index, part in enumerate(parts):
        if TICKET_KEY.match(part):
            return "/".join(parts[: index + 1])
    if parts[0] == "sessions" and len(parts) > 3:
        return "/".join(parts[:3])
    return "/".join(parts)


def scan(root: Path, terms: list[str]) -> dict[str, dict]:
    patterns = {term: re.compile(re.escape(term), re.IGNORECASE) for term in terms}
    units: dict[str, dict] = {}
    for base in SEARCH_DIRS:
        top = root / base
        if not top.is_dir():
            continue
        for path in top.rglob("*"):
            if path.suffix not in SUFFIXES or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            rel = str(path.relative_to(root))
            matched = {term for term, pattern in patterns.items() if pattern.search(text) or pattern.search(rel)}
            if not matched:
                continue
            unit = units.setdefault(unit_of(path, root), {"terms": set(), "files": [], "latest": 0.0})
            unit["terms"] |= matched
            unit["files"].append((len(matched), rel))
            unit["latest"] = max(unit["latest"], path.stat().st_mtime)
    return units


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, help="project-management root")
    parser.add_argument("--key", help="the new ticket key; searched too, never alone")
    parser.add_argument("--term", action="append", default=[], help="symptom or product term (repeat)")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    terms = [t.strip() for t in args.term if t.strip()]
    if not root.is_dir() or not terms:
        print("need an existing --root and at least one --term (symptom or product name)")
        return 2
    search_terms = terms + ([args.key] if args.key else [])
    units = scan(root, search_terms)
    if not units:
        print("no prior work found for: " + ", ".join(search_terms))
        return 1

    ranked = sorted(units.items(), key=lambda kv: (-len(kv[1]["terms"] - {args.key}), -kv[1]["latest"]))
    print(f"prior work for {args.key or '(no key)'}: {len(units)} unit(s), top {min(args.limit, len(units))}")
    for unit, info in ranked[: args.limit]:
        symptom_hits = len(info["terms"] - {args.key})
        date = dt.date.fromtimestamp(info["latest"]).isoformat()
        key_note = " +key" if args.key in info["terms"] else ""
        print(f"[{symptom_hits}/{len(terms)} terms{key_note}] {unit}  (latest {date})")
        for _, file in sorted(info["files"], reverse=True)[:3]:
            print(f"    {file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
