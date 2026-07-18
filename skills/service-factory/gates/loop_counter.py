#!/usr/bin/env python3
"""Loop-counter / governor materiality gate (§6, Phase 4).

Guards SFE-46 / IFM-7. The loop cap ("3 re-entries without a NEW confirmed
observation") is toothless if "new confirmed observation" is undefined for
materiality: an agent logs a throwaway re-confirm each cycle and the counter
resets forever. Materiality rule, mechanically checkable:

  the counter resets ONLY on a cycle whose ledger append changed >=1 card's
  status OR created a new scoped card. A zero-information observation
  (re-confirmed anchor, grep-with-line-cite that flips nothing) increments it.

At cap the transition step refuses re-entry until a pulse option is chosen.

  python3 loop_counter.py <state.yaml> <delta.yaml>
    state.yaml:  {loops: 0, cap: 3}
    delta.yaml:  {status_changed: 0, new_cards: 0}
  exit 0 = re-entry allowed, 1 = refused (pulse required)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lib

DEFAULT_CAP = 3


def materiality(delta: dict) -> bool:
    delta = delta or {}
    return int(delta.get("status_changed", 0)) > 0 or int(delta.get("new_cards", 0)) > 0


def apply_cycle(state: dict, material: bool) -> dict:
    state = dict(state or {})
    state.setdefault("cap", DEFAULT_CAP)
    state.setdefault("loops", 0)
    if material:
        state["loops"] = 0
    else:
        state["loops"] = state["loops"] + 1
    return state


def can_reenter(state: dict):
    cap = state.get("cap", DEFAULT_CAP)
    loops = state.get("loops", 0)
    if loops >= cap:
        return False, f"loop cap hit ({loops}/{cap}) — pulse required before re-entry"
    return True, f"under budget ({loops}/{cap})"


def run_sequence(state: dict, cycles):
    """Apply a list of {status_changed, new_cards} deltas; return snapshots."""
    snaps = []
    s = dict(state or {})
    for c in cycles:
        s = apply_cycle(s, materiality(c))
        ok, reason = can_reenter(s)
        snaps.append({"loops": s["loops"], "can_reenter": ok, "reason": reason})
    return snaps


def check(state_path, delta_path) -> dict:
    state = lib.load_yaml(state_path)
    delta = lib.load_yaml(delta_path)
    new_state = apply_cycle(state, materiality(delta))
    ok, reason = can_reenter(new_state)
    return {"pass": ok, "loops": new_state["loops"], "cap": new_state.get("cap", DEFAULT_CAP), "reason": reason}


def main(argv):
    if len(argv) < 3:
        print("usage: loop_counter.py <state.yaml> <delta.yaml>", file=sys.stderr)
        return 2
    res = check(argv[1], argv[2])
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
