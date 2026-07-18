#!/usr/bin/env python3
"""Closure-matrix validator (Phase 8 bundled EXIT).

Guards SFE-51 / IFM-12 ("tracked" theater) and SFE-16 / F15 (phantom ticket).

Mechanical rules:
  1. Terminal dispositions only: green-rerepro, or tracked WITH a real ticket key.
     A bare owner comment is `comment-posted` — a distinct, NON-terminal
     disposition that blocks a "resolved" close.
  2. `tracked` requires a ticket key that resolves in the known-key set.
  3. The consolidated closing draft may not say "tracked" for a cause whose row
     is only comment-posted (verb stronger than the artifact).
  4. Every ticket key referenced in rca.md must resolve (no phantom tickets).
  5. Every reported env has a matrix row (env coverage).

  python3 closure_matrix.py <service-area-dir>   # exit 0 = closeable
Known-key resolver: known-tickets.txt (one key/line) OR closure-matrix.yaml
`known_tickets:` list. The current ticket id (state.yaml `ticket`) is always known.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import lib

_KEY_RE = re.compile(r"\b[A-Z]{2,}-\d+\b")
TERMINAL = {"green-rerepro", "tracked"}


def _known_keys(d: Path, matrix: dict) -> set:
    keys = set()
    kt = d / "known-tickets.txt"
    if kt.exists():
        keys |= {ln.strip() for ln in kt.read_text().splitlines() if ln.strip()}
    keys |= set(matrix.get("known_tickets") or [])
    state = lib.load_yaml(d / "state.yaml") or {}
    if state.get("ticket"):
        keys.add(state["ticket"])
    return keys


def check(service_area: str) -> dict:
    d = Path(service_area)
    matrix = lib.load_yaml(d / "closure-matrix.yaml") or {}
    rows = matrix.get("rows") or []
    rca = lib.read_text(d / "rca.md")
    draft = lib.read_text(d / "closing-draft.md")
    known = _known_keys(d, matrix)

    reasons = []
    nonterminal, tracked_no_key, comment_only_causes = [], [], []

    for r in rows:
        disp = (r.get("disposition") or "").strip()
        cause = r.get("cause", "?")
        if disp == "tracked":
            key = r.get("ticket")
            if not key or key not in known:
                tracked_no_key.append(cause)
                reasons.append(
                    f"row {cause}: disposition=tracked but ticket key "
                    f"'{key}' does not resolve -> downgrade to comment-posted"
                )
        elif disp == "comment-posted":
            comment_only_causes.append(cause)
            nonterminal.append(cause)
            reasons.append(
                f"row {cause}: comment-posted is non-terminal — blocks a 'resolved' close"
            )
        elif disp not in TERMINAL:
            nonterminal.append(cause)
            reasons.append(f"row {cause}: disposition '{disp}' is not terminal")

    # Rule 3 — draft may not overclaim "tracked" for a comment-only cause.
    if comment_only_causes and re.search(r"\btracked\b", draft, re.IGNORECASE):
        reasons.append(
            f"closing draft says 'tracked' while causes {comment_only_causes} are only comment-posted"
        )

    # Rule 4 — phantom ticket scan in rca.md.
    phantom = sorted({k for k in _KEY_RE.findall(rca) if k not in known})
    if phantom:
        reasons.append(f"rca.md references unresolved ticket key(s): {phantom}")

    # Rule 5 — env coverage.
    fact = lib.read_text(d / "env-fact-sheet.md")
    reported_envs = set(re.findall(r"^\s*ENV\s*:\s*(\S+)", fact, re.IGNORECASE | re.MULTILINE))
    row_envs = {r.get("env") for r in rows if r.get("env")}
    missing_envs = sorted(reported_envs - row_envs)
    if missing_envs:
        reasons.append(f"reported env(s) with no closure row: {missing_envs}")

    return {
        "pass": not reasons,
        "reasons": reasons,
        "nonterminal_rows": nonterminal,
        "tracked_without_key": tracked_no_key,
        "phantom_tickets": phantom,
    }


def main(argv):
    if len(argv) < 2:
        print("usage: closure_matrix.py <service-area-dir>", file=sys.stderr)
        return 2
    res = check(argv[1])
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
