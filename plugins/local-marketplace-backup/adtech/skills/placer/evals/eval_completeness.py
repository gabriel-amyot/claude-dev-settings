#!/usr/bin/env python3
"""Doc-completeness eval for adtech:placer SKILL.md.

The placer skill is procedural (curl + bq), with no unit-testable code path of
its own. The risk in consolidating three former skills (placer-onboarding,
klever-placer-api, placer-entity-matcher) into one is that a critical gotcha or
mode silently got dropped. This eval guards against that: it reads SKILL.md and
asserts the consolidation lost nothing material.

It checks two things:
  1. All three mode headers are present (onboard, api-check, entity-match).
  2. Every critical gotcha token survives (the silent-failure traps and gates
     that, if missing, would make the skill dangerous to follow).

Prints a checklist; exits non-zero if anything is missing.

stdlib only. Run: python3 eval_completeness.py
"""

import os
import sys

SKILL_MD = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "SKILL.md",
    )
)

PASS = "PASS"
FAIL = "FAIL"

# Mode headers — each mode must have its own `## Mode: ...` section.
MODE_HEADERS = [
    "## Mode: `onboard`",
    "## Mode: `api-check`",
    "## Mode: `entity-match`",
]

# Critical gotcha tokens. Each entry: (label, match) where `match` is either a
# single required substring, or a tuple meaning "any one of these is acceptable".
GOTCHA_TOKENS = [
    ("apiIds (plural array)", "apiIds"),
    ("apiId (singular)", "apiId"),
    ("entityIds (the wrong field)", "entityIds"),
    ("202 async in-progress", "202"),
    ("204 no panel data", "204"),
    ("chain cross-reference", "chain"),
    ("80% acceptance gate", "80%"),
    ("lat/lng non-functional search", ("lat/lng", "lat/lon")),
    ("brand alias rule", "alias"),
    ("stale-variant detection", "stale"),
    ("bridge MERGE SQL generator (KTP-695)", "csv_to_merge_sql.py"),
    ("idempotent MERGE keyed on klever_location_id", "keyed on `klever_location_id`"),
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
    print("eval_completeness: adtech:placer SKILL.md")
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

    print("RESULT: PASS (consolidation preserved all modes + gotchas)")


if __name__ == "__main__":
    main()
