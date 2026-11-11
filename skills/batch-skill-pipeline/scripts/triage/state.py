#!/usr/bin/env python3
"""Read or update <run>/STATE.json, the resume point of a triage run.

  state.py --run-dir DIR                         print the state
  state.py --run-dir DIR --phase P3              set the current phase (status running)
  state.py --run-dir DIR --done P2               mark a phase done
  state.py --run-dir DIR --batch batch-aa --pass claude --mark done
  state.py --run-dir DIR --status waiting        running | waiting | done | failed

The HTML page refreshes itself every 30 s while status is running.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage_common as tc  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--phase", choices=tc.PHASES)
    ap.add_argument("--done", choices=tc.PHASES)
    ap.add_argument("--status", choices=["running", "waiting", "done", "failed"])
    ap.add_argument("--batch")
    ap.add_argument("--pass", dest="pass_", choices=["claude", "codex"])
    ap.add_argument("--mark", default="done")
    args = ap.parse_args()
    run = os.path.abspath(os.path.expanduser(args.run_dir))
    state = tc.load_state(run)
    changes = {}
    if args.phase:
        changes.update(phase=args.phase, status=args.status or "running")
    if args.done:
        phases = state.get("phases", {})
        phases[args.done] = "done"
        changes["phases"] = phases
    if args.status:
        changes["status"] = args.status
    if args.batch:
        if not args.pass_:
            sys.exit("--batch needs --pass claude|codex")
        batches = state.get("batches", {})
        batches.setdefault(args.batch, {})[args.pass_] = args.mark
        changes["batches"] = batches
    if changes:
        os.makedirs(run, exist_ok=True)
        state = tc.save_state(run, **changes)
    print(json.dumps(state, indent=1))


if __name__ == "__main__":
    main()
