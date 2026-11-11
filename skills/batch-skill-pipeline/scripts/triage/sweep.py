#!/usr/bin/env python3
"""P7 of the skill-proposal triage: run every Layer A suite, and compare against a baseline.

Runs each Layer A runner of <worktree>/evals/manifest.yaml with the live harness path mapped to
the worktree. With --baseline (normally the main checkout, for example ~/.claude-shared-config),
it runs the same suites from the baseline manifest too and classifies each suite:
  REGRESSION    PASS on baseline, not PASS on the branch   -> blocks the merge
  PRE-EXISTING  not PASS on both                           -> report, do not block
  FIXED         not PASS on baseline, PASS on the branch
  NEW           only in the branch manifest
Why the baseline: some runners resolve live paths internally, so a red suite on the branch can
be a pre-existing failure. Never call a failure a regression without this comparison.

Writes <run>/apply/sweep.md. Exit 1 when any REGRESSION exists (or, without --baseline, any
suite is not PASS).

Usage: sweep.py --run-dir DIR --worktree DIR [--baseline DIR] [--live-root PATH] [--jobs 6]
"""
import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor


def layer_a_jobs(root, live_root):
    text = open(os.path.join(root, "evals", "manifest.yaml")).read().split("\nexclusions:")[0]
    jobs = {}
    for b in re.split(r"(?m)^(?=\s*-\s*target:)", text):
        t = re.search(r"-\s*target:\s*(\S+)", b)
        r = re.search(r"runner:\s*(.+)", b)
        if t and r and re.search(r"layer:\s*A\b", b):
            jobs[t.group(1)] = r.group(1).strip().strip('"').replace(live_root, root)
    return jobs


def run_one(cmd):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600,
                           executable="/bin/bash", stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    tail = ((p.stdout + p.stderr).strip().splitlines() or [""])[-1][:120]
    return ("PASS" if p.returncode == 0 else f"FAIL({p.returncode})"), tail


def run_all(jobs, n):
    with ThreadPoolExecutor(n) as ex:
        return dict(zip(jobs, ex.map(run_one, jobs.values())))


def classify(branch, base):
    if base is None:
        return "PASS" if branch == "PASS" else "FAIL"
    if base == "missing":
        return "NEW"
    if base == "PASS":
        return "OK" if branch == "PASS" else "REGRESSION"
    return "FIXED" if branch == "PASS" else "PRE-EXISTING"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--worktree", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--live-root", default="~/.claude-shared-config")
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    run = os.path.abspath(os.path.expanduser(args.run_dir))
    wt = os.path.abspath(os.path.expanduser(args.worktree))
    live = args.live_root

    branch = run_all(layer_a_jobs(wt, live), args.jobs)
    base = None
    if args.baseline:
        broot = os.path.abspath(os.path.expanduser(args.baseline))
        base = run_all(layer_a_jobs(broot, live), args.jobs)

    rows, counts = [], {}
    for tgt, (res, tail) in sorted(branch.items()):
        bres = None if base is None else base.get(tgt, ("missing", ""))[0]
        cls = classify(res, bres)
        counts[cls] = counts.get(cls, 0) + 1
        rows.append((tgt, res, bres or "", cls, tail))
    out = os.path.join(run, "apply", "sweep.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        fh.write("| Suite | Branch | Baseline | Class | Last line |\n|---|---|---|---|---|\n")
        fh.writelines(f"| {' | '.join(r)} |\n" for r in rows)
    print(f"{len(rows)} Layer A suites: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for r in rows:
        if r[3] not in ("OK", "PASS"):
            print(" | ".join(r))
    print(f"table: {out}")
    bad = "REGRESSION" if base is not None else "FAIL"
    sys.exit(1 if counts.get(bad) else 0)


if __name__ == "__main__":
    main()
