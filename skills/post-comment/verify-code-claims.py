#!/usr/bin/env python3
"""
verify-code-claims.py — KTP-688 Layer B gate for the /post-comment pipeline.

Scans a drafted external post for code-location citations (e.g. `bigquery.py:46`,
`sub_agents/data_routing/agent.py:97`). Every such citation must carry a deploy-identity
verification STAMP, so the claim's provenance travels with it into the reader's hands:

    bigquery.py:46 [VERIFIED against dev@bae8f58]
    bigquery.py:46 [UNVERIFIED — read on main, deploy=dev]

The catastrophe this prevents: sending main-based line-refs to a code owner with FALSE implied
authority (KTP-688). A "verification token" is a stamp produced by the `deploy-identity` probe.

Exit codes:
  0  — OK to proceed (all citations stamped). Prints a warning if any are UNVERIFIED.
  2  — BLOCK: one or more code-location citations have NO stamp. The draft is not approvable
        until each is stamped (run /deploy-identity to produce the stamp).

Usage: verify-code-claims.py <draft-file>
"""
import re
import sys

# file.ext:line  (path may include dirs). Extensions kept to real source types to avoid false hits.
CITATION = re.compile(
    r'\b[\w./\-]+\.(?:py|ts|tsx|js|jsx|java|go|rb|sql|kt|kts|rs|c|cc|cpp|h|hpp|scala|php|swift|m|mm)'
    r':\d+(?:-\d+)?\b'
)
# A stamp anywhere on the same line counts as covering the citations on that line.
STAMP = re.compile(r'\[(?:VERIFIED against |UNVERIFIED\b)', re.IGNORECASE)
UNVERIFIED = re.compile(r'\[UNVERIFIED\b', re.IGNORECASE)


def main():
    if len(sys.argv) < 2:
        print("usage: verify-code-claims.py <draft-file>", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as e:
        print(f"verify-code-claims: cannot read draft: {e}", file=sys.stderr)
        return 2

    unstamped = []   # (lineno, citation, line)
    unverified = []  # (lineno, citation)
    for i, line in enumerate(lines, 1):
        cites = list(CITATION.finditer(line))
        if not cites:
            continue
        line_has_stamp = bool(STAMP.search(line))
        line_unverified = bool(UNVERIFIED.search(line))
        for m in cites:
            cite = m.group(0)
            if not line_has_stamp:
                unstamped.append((i, cite, line.strip()))
            elif line_unverified:
                unverified.append((i, cite))

    if unstamped:
        print("BLOCKED by verify-code-claims: code-location citations without a deploy-identity stamp.\n",
              file=sys.stderr)
        print("Every code-location claim in an external post must carry its verification status, so the\n"
              "reader knows which branch it was checked against. This is the KTP-688 containment gate.\n",
              file=sys.stderr)
        for lineno, cite, text in unstamped:
            print(f"  line {lineno}: {cite}", file=sys.stderr)
            print(f"            in: {text}", file=sys.stderr)
        print("\nFIX each one:", file=sys.stderr)
        print("  1. Run /deploy-identity (probe) for the repo the citation refers to.", file=sys.stderr)
        print("  2. Append the stamp it emits to the citation, e.g.:", file=sys.stderr)
        print("       bigquery.py:46 [VERIFIED against dev@bae8f58]", file=sys.stderr)
        print("       bigquery.py:46 [UNVERIFIED — read on main, deploy=dev]", file=sys.stderr)
        print("  3. Re-run the gate. UNVERIFIED is allowed (it's honest), but it must be explicit.",
              file=sys.stderr)
        return 2

    if unverified:
        print("⚠ verify-code-claims: proceeding, but these citations are stamped UNVERIFIED —")
        print("  make sure the human approver sees that before this goes out:")
        for lineno, cite in unverified:
            print(f"    line {lineno}: {cite}")
        print("  (A claim about another engineer's code that you could not verify against the deploy")
        print("   branch should usually be reframed as an open question, not a stated fact.)")
        return 0

    print("verify-code-claims: OK — all code-location citations carry a VERIFIED deploy-identity stamp"
          " (or no code-location citations present).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
