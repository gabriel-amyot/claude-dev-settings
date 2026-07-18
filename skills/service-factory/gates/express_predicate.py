#!/usr/bin/env python3
"""Express-lane entry predicate (Phase 2b).

Guards SFE-40 / IFM-1 — the KTP-939 multi-cause class re-admitted through v3's
own express guard. "One cause explains the anchor in EVERY reported env" is
trivially true over a set of size 1 if you read the env universe from the
anchored set. This predicate reads the env universe from env-fact-sheet.md and
DECLINES the moment any reported env lacks an anchor (parked envs do NOT count
as anchored — NP3: absence must be loud).

Input: express-input.yaml with
  env_universe: [prod, demo-prod, demo-dev]   # from env-fact-sheet.md, the truth
  anchored_envs: [demo-dev]                    # envs with a two-part anchor
  parked_envs: [prod, demo-prod]               # cannot-access, parked-with-comment
  component_named: true                        # anchor names the failing component
  recent_change_in_hand: true                  # commit/MR/config diff in hand
  single_cause_all_envs: true                  # one cause explains every anchor

  python3 express_predicate.py <express-input.yaml>   # exit 0 = fire, 1 = decline
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lib


def check(inp) -> dict:
    if isinstance(inp, (str, Path)):
        data = lib.load_yaml(inp)
    else:
        data = inp or {}

    universe = list(data.get("env_universe") or [])
    anchored = set(data.get("anchored_envs") or [])
    reasons = []

    if not universe:
        reasons.append("env_universe empty — cannot define 'every reported env'")

    # The env universe is authoritative. Every reported env must be anchored.
    missing = [e for e in universe if e not in anchored]
    if missing:
        reasons.append(
            f"anchors({len(anchored & set(universe))}) < reported_envs({len(universe)}): "
            f"unanchored envs {missing} -> route SURFACE"
        )

    if not data.get("component_named"):
        reasons.append("anchor does not name the failing component")
    if not data.get("recent_change_in_hand"):
        reasons.append("no recent identified change in hand")
    if not data.get("single_cause_all_envs"):
        reasons.append("one cause does not explain the anchor in every env")

    fire = not reasons
    return {
        "pass": fire,  # pass == express fires
        "route": "EXPRESS" if fire else "SURFACE",
        "reasons": reasons,
        "env_universe_size": len(universe),
        "anchored_count": len(anchored & set(universe)),
    }


def main(argv):
    if len(argv) < 2:
        print("usage: express_predicate.py <express-input.yaml>", file=sys.stderr)
        return 2
    res = check(argv[1])
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
