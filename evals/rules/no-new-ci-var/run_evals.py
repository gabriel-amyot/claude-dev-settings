#!/usr/bin/env python3
"""Layer A runner for rules/no-new-ci-var. Each case declares the verdict it must get.

Incident replays must FAIL (the grader catches the old behavior). Correct answers must PASS.
Exit 0 when every verdict matches, 1 otherwise.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grader as G  # noqa: E402


def main() -> int:
    wrong = []
    for case_path in sorted((HERE / "cases").glob("*/case.json")):
        case, answer, transcript = G.load(case_path)
        rep = G.grade(case, answer, transcript)
        expected_pass = case["expect"] == "pass"
        ok = rep["pass"] == expected_pass
        verdict = "PASS" if rep["pass"] else "FAIL"
        print(f"  [{'OK' if ok else 'WRONG'}] {case['name']}: got {verdict}, want {case['expect'].upper()}")
        for h in rep["hard_fails"]:
            print(f"        {h}")
        if not ok:
            wrong.append(case["name"])
    print(f"{'GREEN' if not wrong else 'RED'}: {len(wrong)} wrong verdict(s) {wrong if wrong else ''}")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
