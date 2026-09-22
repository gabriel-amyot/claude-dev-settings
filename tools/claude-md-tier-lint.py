#!/usr/bin/env python3
"""Tier lint for CLAUDE.md files.

CLAUDE.md is the always-on RULE layer. Facts belong in GOLD library pages, locators in
SILVER indexes (ALIASES.md), raw origins in BRONZE (_archive/). A raw incident narrative
sitting inline is a tier violation: bronze content in the layer that loads every session.

Checks:
  1. BRONZE-IN-RULES  — "Learned from ..." narratives in prose or headings (not in code fences)
  2. UNLINKED-ORIGIN  — a ticket key cited with no pointer to a library page
  3. BUDGET           — ratchet: a file may shrink freely, but growth past its
                        recorded high-water mark warns

The budget is a ratchet, never a gate. It warns on growth and silently lowers the
baseline when a file shrinks. It must never block a fix: a bad rule landing in an
over-budget file has to stay fixable.

Usage:
  claude-md-tier-lint.py                 # report, exit 0
  claude-md-tier-lint.py --check         # exit 1 on any violation
  claude-md-tier-lint.py --file <path>   # lint one file
  claude-md-tier-lint.py --accept-budget # re-baseline to current sizes
"""
import json
import re
import sys
from pathlib import Path

TARGETS = [
    Path.home() / ".claude-shared-config/CLAUDE.md",
    Path.home() / "Developer/grp-beklever-com/project-management/CLAUDE.md",
]
BUDGET_FILE = Path.home() / ".claude-shared-config/tools/.claude-md-budget.json"

TICKET = re.compile(r"\b(?:KTP|KTT|SPV|INS|PER)-\d+\b")
NARRATIVE = re.compile(r"\(?Learned from\b", re.I)
# A line is "linked" if it points at a library page, a wikilink, or a doc path.
LINKED = re.compile(r"\[\[[^\]]+\]\]|library/context/|bibliotheque/|documentation/|\.md\b")
SKIP = re.compile(r"^\s*(#|>|\||```)")
FENCE = re.compile(r"^(`{3,}|~{3,})")
# Origin language: the line is explaining WHERE the rule came from.
ORIGINISH = re.compile(r"\b(learned|from|incident|caused|after|discovered|"
                       r"session|regression|postmortem|rca|blocked|broke)\b", re.I)


def lint_file(path: Path):
    out = []
    fence_char = None
    fence_len = 0
    for n, line in enumerate(path.read_text().splitlines(), 1):
        s = line.lstrip()
        m = FENCE.match(s)
        if m:
            ch, run = m.group(1)[0], len(m.group(1))
            if fence_char is None:
                fence_char, fence_len = ch, run
                continue
            if ch == fence_char and run >= fence_len and not s[run:].strip():
                fence_char, fence_len = None, 0
                continue
        if fence_char is not None:
            continue
        if NARRATIVE.search(line):
            out.append(("BRONZE-IN-RULES", n,
                        "inline incident narrative; move the origin to _archive/ (bronze), "
                        "the lesson to a gold page, and cite the page"))
            continue
        if SKIP.match(line) or LINKED.search(line):
            continue
        # A ticket key inside a path or code span is an illustrative example, not an
        # origin. Only flag keys presented as the provenance of the rule.
        bare = TICKET.findall(re.sub(r"`[^`]*`", "", line))
        if bare and ORIGINISH.search(line):
            keys = ", ".join(sorted(set(bare)))
            out.append(("UNLINKED-ORIGIN", n,
                        f"cites {keys} as provenance with no pointer to a library page"))
    return out


def load_budget():
    try:
        return json.loads(BUDGET_FILE.read_text())
    except Exception:
        return {}


def main() -> int:
    check = "--check" in sys.argv
    accept = "--accept-budget" in sys.argv
    targets = TARGETS
    if "--file" in sys.argv:
        targets = [Path(sys.argv[sys.argv.index("--file") + 1])]

    budget = load_budget()
    violations = 0
    grew = []

    for path in targets:
        if not path.exists():
            continue
        key = str(path)
        size = path.stat().st_size
        base = budget.get(key)

        findings = lint_file(path)
        if findings:
            print(f"\n{path}")
            for kind, n, msg in findings:
                print(f"  {kind:18s} :{n}  {msg}")
            violations += len(findings)

        if accept or base is None or size < base:
            budget[key] = size          # ratchet down, or first run
        elif size > base:
            grew.append((path, base, size))

    if grew:
        print()
        for path, base, size in grew:
            print(f"BUDGET  {path.name} grew {base} -> {size} B (+{size - base}). "
                  f"Warning only, never a block.")
            print(f"        If intentional: claude-md-tier-lint.py --accept-budget")

    try:
        BUDGET_FILE.write_text(json.dumps(budget, indent=1) + "\n")
    except Exception:
        pass

    if violations:
        print(f"\n{violations} tier violation(s). "
              f"CLAUDE.md holds rules; origins go to bronze, lessons to gold.")
    elif not grew and "--hook" not in sys.argv:
        print("Tier lint clean. No inline origins, no unlinked ticket keys.")

    return 1 if (check and (violations or grew)) else 0


if __name__ == "__main__":
    sys.exit(main())
