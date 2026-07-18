#!/usr/bin/env python3
"""Calibration gate — every replay grader MUST FAIL its old-behaviour fixture.

Design rule 1 made executable. A grader that PASSES a reconstructed old/gamed run
is a non-discriminative eval (a confirmed defect), reported loudly here.

  python3 calibrate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "graders"))
import replay_graders as G  # noqa: E402

CALIB = HERE / "calibration"
REPLAYS = HERE / "replays"

# (calibration dir, grader fn, world fixture) — grader must return pass == False
CASES = [
    ("sfe10_repro", G.grade_sfe10, "sfe10_repro"),
    ("sfe13_attribution", G.grade_sfe13, "sfe13_attribution"),
    ("sfe15_confab", G.grade_sfe15, "sfe15_confab"),
    ("sfe15_narrative", G.grade_sfe15, "sfe15_confab"),  # subtle gap probe
    ("sfe16_multicause", G.grade_sfe16, "sfe16_multicause"),
    ("sfe21_alias", G.grade_sfe21, "sfe21_alias"),
]


def main():
    print("Calibration gate — graders MUST fail old-behaviour runs\n" + "=" * 56)
    defects = []
    for calib_name, grader, world_name in CASES:
        run = G.Run(CALIB / calib_name, REPLAYS / world_name / "world.yaml")
        res = grader(run)
        discriminative = not res["pass"]  # we WANT a fail here
        mark = "OK (fails old)" if discriminative else "DEFECT (passes old!)"
        print(f"  [{mark}] {calib_name}")
        if not discriminative:
            defects.append(calib_name)
            for c in res["checks"]:
                print(f"       passed check that should have caught it: {c['name']} -> {c['ok']}")
    print("=" * 56)
    if defects:
        print(f"NON-DISCRIMINATIVE (defects): {defects}")
        return 1
    print("All graders are discriminative (every old-behaviour run fails).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
