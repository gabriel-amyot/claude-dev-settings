#!/usr/bin/env python3
"""Stamp check — the WALL's un-skippable pre-gate (Phase 5).

Guards SFE-01 (unsupported/"(VERIFIED)" cause) and SFE-41 (claim-type <-> method
compatibility — the NP1 relevance predicate: a mechanism cause backed only by a
symptom read is confidence laundering, not proof).

Authoritative on board.yaml CONFIRMED cards (each becomes a Cause), cross-checked
against observations.yaml, with an rca.md document-headline scan.

  python3 stamp_check.py <service-area-dir>   # exit 0 pass, 1 reject
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lib

_VERIFIED_HEADLINE = ("(verified)", "solved", "root cause (confirmed", "— solved")


def check(service_area: str) -> dict:
    d = Path(service_area)
    board = lib.load_yaml(d / "board.yaml") or []
    obs_list = lib.load_yaml(d / "observations.yaml") or []
    rca = lib.read_text(d / "rca.md")
    obs_by_id = {o.get("id"): o for o in obs_list if isinstance(o, dict)}

    reasons = []
    causes = [c for c in board if isinstance(c, dict) and c.get("status") == "CONFIRMED"]

    headline_verified = any(h in rca.lower() for h in _VERIFIED_HEADLINE)

    for c in causes:
        cid = c.get("id", "?")
        ev = c.get("evidence") or []
        # R1 — every cause cites >=1 OBSERVED row that resolves.
        observed_rows = [
            obs_by_id[e]
            for e in ev
            if e in obs_by_id and obs_by_id[e].get("stamp") == "OBSERVED"
        ]
        if not observed_rows:
            reasons.append(
                f"{cid}: cause has no resolving [OBSERVED] evidence row "
                f"-> claim relabeled [ASSUMED], cannot cross the WALL"
            )
            continue

        # R3 (SFE-41) — mechanism-class cause needs mechanism-grade evidence.
        component = (c.get("scope") or {}).get("component", "")
        if lib.is_mechanism_component(component):
            claim_dom = lib.domain_of(component)
            ok_method = False
            for o in observed_rows:
                m = o.get("method")
                if m in lib.MECHANISM_METHODS:
                    ok_method = True
                    break
                if m == "live-probe":
                    src = o.get("source") or {}
                    src_label = src.get("instance") or src.get("component") or src.get("env") or ""
                    if lib.domain_of(src_label) == claim_dom:
                        ok_method = True
                        break
            if not ok_method:
                methods = sorted({o.get("method") for o in observed_rows})
                reasons.append(
                    f"{cid}: mechanism-class cause (domain={claim_dom}) backed only by "
                    f"symptom-surface evidence {methods}; needs a "
                    f"{sorted(lib.MECHANISM_METHODS)} row or a domain-matched live-probe"
                )

        # R2 (SFE-01b) — a "solved"/"(VERIFIED)" headline demands verified_against.
        if headline_verified:
            if not any(o.get("verified_against") for o in observed_rows):
                reasons.append(
                    f"{cid}: document claims VERIFIED/solved but no cited row carries "
                    f"verified_against"
                )

    # rca.md cause-line scan (defense in depth): a Cause claim line with no
    # [OBSERVED Oxx] citation anywhere in its block is a reject.
    reasons += _scan_rca_cause_lines(rca)

    return {"pass": not reasons, "reasons": reasons, "cause_count": len(causes)}


def _scan_rca_cause_lines(rca: str) -> list:
    out = []
    if not rca:
        return out
    lines = rca.splitlines()
    in_causes = False
    for i, ln in enumerate(lines):
        low = ln.strip().lower()
        if low.startswith("## 3"):
            in_causes = True
            continue
        if in_causes and ln.strip().startswith("## "):
            break
        if in_causes and ("**claim:**" in low or low.startswith("- claim:")):
            # gather the block: this line + following until next claim/blank-blank
            block = ln
            for j in range(i + 1, min(i + 6, len(lines))):
                nxt = lines[j].strip().lower()
                if "**claim:**" in nxt or nxt.startswith("## "):
                    break
                block += "\n" + lines[j]
            if not lib.has_observed_citation(block):
                out.append(
                    f"rca §3 cause line lacks an [OBSERVED Oxx] citation: "
                    f"{ln.strip()[:70]}"
                )
    return out


def main(argv):
    if len(argv) < 2:
        print("usage: stamp_check.py <service-area-dir>", file=sys.stderr)
        return 2
    res = check(argv[1])
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
