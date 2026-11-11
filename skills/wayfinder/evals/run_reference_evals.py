#!/usr/bin/env python3
"""Layer A drift checks for the wayfinder references.

The dispatch template exists because hand-relayed procedures drifted. A template drifts
too, when the tool or the spec changes under it. These checks tie the template to the
real tool and the real SKILL.md, so a rename on either side turns this suite red.

Run:  python3 run_reference_evals.py [-v]
Exit: 0 all green, 1 any failure
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL = SKILL_DIR / "SKILL.md"
TOOL = SKILL_DIR / "tools" / "wayfinder_runs.py"
DISPATCH = SKILL_DIR / "references" / "dispatch-template.md"
ROUNDS = SKILL_DIR / "references" / "overnight-rounds.md"
NON_RESOLVE_OUTCOMES = {"charted", "reported"}
VERBOSE = "-v" in sys.argv
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))
    if VERBOSE or not condition:
        print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not condition else ""))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def tool_outcomes(tool_text: str) -> set[str]:
    match = re.search(r"^OUTCOMES\s*=\s*\(([^)]*)\)", tool_text, re.MULTILINE)
    return set(re.findall(r'"([a-z_]+)"', match.group(1))) if match else set()


def skill_friction_tags(skill_text: str) -> set[str]:
    return set(re.findall(r"^\|\s*`([a-z-]+)`\s*\|", skill_text, re.MULTILINE))


def skill_headings(skill_text: str) -> set[str]:
    return {h.strip() for h in re.findall(r"^#{2,3}\s+(.+)$", skill_text, re.MULTILINE)}


def test_references_exist_and_are_linked() -> None:
    skill = read(SKILL)
    for ref in (DISPATCH, ROUNDS):
        check(f"exists:{ref.name}", ref.exists(), str(ref))
        check(f"linked from SKILL.md:{ref.name}", f"references/{ref.name}" in skill)


def test_dispatch_outcomes_match_tool() -> None:
    template = read(DISPATCH)
    line = re.search(r"--outcome\s+([a-z_|]+)", template)
    named = set(line.group(1).split("|")) if line else set()
    expected = tool_outcomes(read(TOOL)) - NON_RESOLVE_OUTCOMES
    check("dispatch:outcomes match the tool's resolve outcomes", bool(expected) and named == expected,
          f"template={sorted(named)} tool={sorted(expected)}")


def test_dispatch_friction_tags_match_spec() -> None:
    template = read(DISPATCH)
    line = re.search(r"# tags:\s*(.+)$", template, re.MULTILINE)
    named = set(line.group(1).split()) if line else set()
    expected = skill_friction_tags(read(SKILL))
    check("dispatch:friction tags match the SKILL.md vocabulary", bool(expected) and named == expected,
          f"template={sorted(named)} spec={sorted(expected)}")


def test_dispatch_sections_exist_in_spec() -> None:
    template = read(DISPATCH)
    line = re.search(r"sections (.+?)\.\s", template, re.DOTALL)
    named = re.findall(r'"([^"]+)"', line.group(1)) if line else []
    headings = skill_headings(read(SKILL))
    check("dispatch:names at least four spec sections", len(named) >= 4, str(named))
    for section in named:
        found = any(h == section or h.startswith(section + ":") for h in headings)
        check(f"dispatch:section exists in SKILL.md:{section}", found)


def test_dispatch_keeps_the_mechanics() -> None:
    template = read(DISPATCH)
    for name, needle in (
        ("reads the spec file, not a relay", "Read ~/.claude/skills/wayfinder/SKILL.md"),
        ("claim first", "--add-assignee @me"),
        ("label pre-check", "wayfinder:<type> label"),
        ("resolve through the tool", "wayfinder_runs.py resolve"),
        ("guarded append fetches fresh", "Do not reuse a copy you read earlier"),
        ("guarded append verifies once", "exactly once"),
        ("verify trailer sentinel", "<!-- wayfinder-run -->"),
        ("verify trailer mode", "mode: resolve"),
        ("re-issued work clause", "On re-issued work"),
    ):
        check(f"dispatch:{name}", needle in template)
    sentinel = re.search(r'TRAILER_SENTINEL\s*=\s*"([^"]+)"', read(TOOL))
    check("dispatch:sentinel matches the tool", bool(sentinel) and sentinel.group(1) in template,
          sentinel.group(1) if sentinel else "no sentinel in tool")


def test_rounds_contract() -> None:
    rounds = read(ROUNDS)
    for name, needle in (
        ("explicit request only", "explicitly asks"),
        ("needs a Notes override", "## Notes"),
        ("charter authority", "**Authority**"),
        ("rollback never passes", "never passes on a rollback"),
        ("frozen packet", "frozen packet"),
        ("reuses executors", "dark-factory"),
    ):
        check(f"rounds:{name}", needle in rounds)


def main() -> int:
    cases = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print(f"wayfinder reference evals — {len(cases)} cases")
    for fn in cases:
        fn()
    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} assertions passed")
    if failed:
        for name, detail in failed:
            print(f"  - {name}" + (f"\n      {detail}" if detail else ""))
        return 1
    print("all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
