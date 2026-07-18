#!/usr/bin/env python3
"""Layer-coverage validator (Phase 3 exit + WALL package).

Guards SFE-50 / IFM-11. "REFUTED cards ARE the elimination log" can only contain
what was hypothesised — a never-seeded layer reads as covered by its absence
(NP3). Coverage must be asserted POSITIVELY, per layer: every in-scope stack
layer maps to >=1 card id OR an explicit `N/A because <reason>`. A zero-card,
non-N/A layer refuses the Phase 3 transition and is carried as a flagged gap
line into the WALL package.

  python3 coverage_line.py <service-area-dir>   # exit 0 = all layers covered
  optional coverage.yaml in the dir:  {na: {infra: "no infra in scope: local-only bug"}}
  optional in-scope override:         {in_scope: [ui, backend, data]}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lib

_DOMAIN_TO_LAYER = {
    "ui": "ui",
    "backend": "backend",
    "data": "data",
    "db": "db",
    "infra": "infra",
    "config": "infra",  # config drift is an infra-layer concern
}


def _card_layer(card: dict) -> str:
    explicit = card.get("layer")
    if explicit and explicit in lib.LAYERS:
        return explicit
    component = (card.get("scope") or {}).get("component", "")
    return _DOMAIN_TO_LAYER.get(lib.domain_of(component))


def check(service_area: str) -> dict:
    d = Path(service_area)
    board = lib.load_yaml(d / "board.yaml") or []
    cov = lib.load_yaml(d / "coverage.yaml") or {}
    in_scope = cov.get("in_scope") or list(lib.LAYERS)
    na = cov.get("na") or {}

    covered = {}
    for c in board:
        if not isinstance(c, dict) or not c.get("id") or not c.get("claim"):
            continue
        layer = _card_layer(c)
        if layer:
            covered.setdefault(layer, []).append(c["id"])

    gaps = []
    coverage_report = {}
    for layer in in_scope:
        if layer in covered:
            coverage_report[layer] = f"{len(covered[layer])} card(s): {covered[layer]}"
        elif layer in na:
            coverage_report[layer] = f"N/A because {na[layer]}"
        else:
            gaps.append(layer)
            coverage_report[layer] = "GAP — zero cards, no N/A"

    line = "LAYER COVERAGE: " + " · ".join(f"{k}={v}" for k, v in coverage_report.items())
    return {
        "pass": not gaps,
        "gaps": gaps,
        "coverage_line": line,
        "reasons": [f"uncovered layer with no N/A: {g}" for g in gaps],
    }


def main(argv):
    if len(argv) < 2:
        print("usage: coverage_line.py <service-area-dir>", file=sys.stderr)
        return 2
    res = check(argv[1])
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
