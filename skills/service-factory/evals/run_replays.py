#!/usr/bin/env python3
"""Tier-2 paper-replay grader/runner.

Grades the artifacts a replay agent produced under runs/<fixture>/ against the
deterministic clauses in graders/replay_graders.py. It does NOT itself spawn the
replay agents (that is a headless `claude -p` / subagent run in REPLAY MODE against
each evals/replays/<fixture>/world.yaml). A fixture with no run dir reports
NOT-RUN — never a fake pass.

  python3 run_replays.py [-v]                 # grade all runs present
  python3 run_replays.py --list               # show fixtures + run status
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "graders"))
import replay_graders as G  # noqa: E402

REPLAYS = HERE / "replays"
RUNS = HERE / "runs"
VERBOSE = "-v" in sys.argv

# Tier 2 criticals (doc 10 scoring): zero fails allowed among these to ship.
CRITICALS = {"sfe10_repro", "sfe13_attribution", "sfe15_confab",
             "sfe16_multicause", "sfe21_alias"}


def main():
    if "--list" in sys.argv:
        for name in sorted(G.GRADERS):
            run = RUNS / name
            status = "RUN" if (run / "transcript.jsonl").exists() or run.exists() else "NOT-RUN"
            print(f"  {name:22s} fixture={'ok' if (REPLAYS/name/'world.yaml').exists() else 'MISSING'}  {status}")
        return 0

    total, passed, notrun, crit_fail = 0, 0, 0, 0
    print("Service Factory — Tier 2 paper replays (deterministic graders)\n" + "=" * 60)
    for name, grader in sorted(G.GRADERS.items()):
        total += 1
        run_dir = RUNS / name
        world = REPLAYS / name / "world.yaml"
        if not run_dir.exists() or not (run_dir / "transcript.jsonl").exists():
            notrun += 1
            print(f"  [NOT-RUN] {name}  (dispatch a REPLAY-MODE agent -> runs/{name}/)")
            continue
        res = grader(G.Run(run_dir, world))
        ok = res["pass"]
        passed += ok
        crit = " *crit" if name in CRITICALS else ""
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}{crit}")
        for c in res["checks"]:
            if not c["ok"] or VERBOSE:
                print(f"       {'ok' if c['ok'] else 'XX'}  {c['name']}: {c['detail']}")
        if not ok and name in CRITICALS:
            crit_fail += 1

    print("=" * 60)
    graded = total - notrun
    print(f"Tier 2: {passed}/{graded} graded green · {notrun} not-run · "
          f"critical fails: {crit_fail}")
    if notrun:
        print("Run a replay: dispatch a fresh agent in REPLAY MODE (SKILL.md) against")
        print("evals/replays/<fixture>/world.yaml, writing artifacts to evals/runs/<fixture>/.")
    # exit non-zero only if a GRADED run failed (not-run is not a failure signal)
    return 1 if (graded and passed < graded) else 0


if __name__ == "__main__":
    sys.exit(main())
