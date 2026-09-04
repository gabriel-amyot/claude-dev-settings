#!/usr/bin/env python3
"""Doc-completeness eval for adtech:goldfish SKILL.md.

The goldfish skill is procedural (curl recipes + field-mapping tables), with no
unit-testable code path of its own. The risk in future edits is that a critical
gotcha — a silent-failure trap or the response-shape drift guard — gets dropped,
leaving a recipe that looks fine but produces empty/wrong data against the live
API. This eval reads SKILL.md and asserts the safety-critical knowledge survives.

It checks two things:
  1. Both mode headers are present (fetch, plan).
  2. Every critical gotcha token survives.

Prints a checklist; exits non-zero if anything is missing. stdlib only.
Run: python3 eval_completeness.py
"""

import os
import sys

SKILL_MD = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SKILL.md")
)

PASS = "PASS"
FAIL = "FAIL"

# Mode headers — each mode must have its own `## Mode: ...` section.
MODE_HEADERS = [
    "## Mode: `fetch`",
    "## Mode: `plan`",
]

# Critical gotcha tokens. Each entry: (label, match) where `match` is either a
# single required substring, or a tuple meaning "any one of these is acceptable".
GOTCHA_TOKENS = [
    ("response wraps payload (drift guard)", '{"inventory"'),
    ("latitude/longitude full-word params", "latitude"),
    ("lat/lng silently fail", ("`lat`", "lat`/`lng`", "lat/lng")),
    ("numerics are strings (parse cpm)", "cpm"),
    ("BQ join via programmaticPlatformKey", "programmaticPlatformKey"),
    ("TTD SITE bridge (not Placer map)", ("ttd_normalized_daily_inventory_performance", "TTD")),
    ("inventory does NOT paginate", "does NOT paginate"),
    ("planning endpoints paginate (meta/nextUrl)", ("nextUrl", "meta")),
    ("uid header required (both headers)", "uid"),
    ("v1 retired -> 410", "410"),
    ("REST-direct decision, not OAuth MCP", "REST API directly"),
]


def present(haystack, needle):
    """needle may be a str or a tuple-of-alternatives."""
    if isinstance(needle, tuple):
        return any(alt in haystack for alt in needle)
    return needle in haystack


def check(label, ok):
    print(f"  [{PASS if ok else FAIL}] {label}")
    return ok


def main():
    print("eval_completeness: adtech:goldfish SKILL.md")
    print(f"  doc: {SKILL_MD}\n")

    if not os.path.isfile(SKILL_MD):
        print(f"  [{FAIL}] SKILL.md not found at {SKILL_MD}")
        sys.exit(1)

    with open(SKILL_MD, "r", encoding="utf-8") as fh:
        text = fh.read()

    results = []

    print("Mode headers:")
    for header in MODE_HEADERS:
        results.append(check(header, header in text))

    print("\nCritical gotcha tokens:")
    missing = []
    for label, needle in GOTCHA_TOKENS:
        ok = present(text, needle)
        results.append(check(label, ok))
        if not ok:
            shown = needle if isinstance(needle, str) else " / ".join(needle)
            missing.append(f"{label} ({shown})")

    print()
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"eval_completeness: {passed}/{total} checks passed")

    if missing:
        print("\nMISSING TOKENS:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)
    if passed != total:
        sys.exit(1)

    print("RESULT: PASS (modes + critical gotchas present)")


if __name__ == "__main__":
    main()
