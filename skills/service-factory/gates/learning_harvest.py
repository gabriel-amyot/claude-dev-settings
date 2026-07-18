#!/usr/bin/env python3
"""Learning-harvest gate — Phase 9 close (D4), dark-factory-Retro-inspired.

The self-learning loop was prose on the honor system; the first replay runs
NARRATED "playbook +1, knowledge-facts emitted" while mutating nothing (the exact
"DONE = said it" fault this factory exists to kill). This gate makes the harvest
un-skippable: Phase 9 cannot close until the artifacts exist and are material.

Checks over <service-area-dir>/knowledge-facts.yaml (+ siblings):

  1. FACTS — each fact = {fact, provenance: verbatim|inferred, raw_source, rca_link}
     (D4 schema — the bibliothèque-compatible payload). raw_source must resolve:
     a run-dir file, or observations.yaml#Oxx with a real Oxx.
     Materiality (NP1): a run with >=1 CONFIRMED cause MUST emit >=1 fact —
     `facts_none_reason` is legal only for no-cause/parked runs.
  2. PLAYBOOK — plus_one id must resolve to a real playbooks/<id>.md (no phantom
     playbook ids), with the append content materialised as playbook-append.md in
     the run dir (live mode also appends to the real file; the artifact proves the
     content exists either way). A proposal needs playbook-proposal-<id>.md.
     `none_reason` is legal only without a confirmed cause.
  3. RETRO — dark-factory pattern, minimal: task_confidence + factory_fitness
     (0-100 ints), red_flags[], improvements[{title,detail}]. fitness < 100 must
     be accounted for (>=1 deduction/red_flag/improvement — no silent low score).
  4. PARKING LOT — drained: every entry line (`- [...]`) carries a `| drained:`
     disposition, or the file is empty / a no-op line.

  python3 learning_harvest.py <service-area-dir> [--playbooks-dir DIR]
  exit 0 = harvest complete, close allowed; 1 = close refused
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import lib

PROVENANCE = frozenset({"verbatim", "inferred"})
_OBS_REF_RE = re.compile(r"^observations\.yaml#(O\d+)$")
_ENTRY_RE = re.compile(r"^- \[")


def _confirmed_causes(d: Path):
    board = lib.load_yaml(d / "board.yaml") or []
    return [c for c in board if isinstance(c, dict) and c.get("status") == "CONFIRMED"]


def _raw_source_resolves(src, d: Path, obs_ids) -> bool:
    if not src:
        return False
    m = _OBS_REF_RE.match(str(src).strip())
    if m:
        return m.group(1) in obs_ids
    return (d / str(src)).exists()


def check(service_area, playbooks_dir=None) -> dict:
    d = Path(service_area)
    pb_dir = Path(playbooks_dir) if playbooks_dir else Path(__file__).resolve().parent.parent / "playbooks"
    reasons = []

    kf_path = d / "knowledge-facts.yaml"
    if not kf_path.exists():
        return {"pass": False, "reasons": [
            "knowledge-facts.yaml missing — harvest narrated is not harvest done; close refused"
        ]}
    kf = lib.load_yaml(kf_path) or {}
    confirmed = _confirmed_causes(d)
    obs_ids = {o.get("id") for o in (lib.load_yaml(d / "observations.yaml") or []) if isinstance(o, dict)}

    # 1 — facts
    facts = kf.get("facts") or []
    if not facts:
        if confirmed:
            reasons.append(
                f"{len(confirmed)} CONFIRMED cause(s) but zero knowledge-facts — a confirmed "
                f"cause always teaches something (facts_none_reason not accepted here)"
            )
        elif not kf.get("facts_none_reason"):
            reasons.append("facts empty with no facts_none_reason")
    for i, f in enumerate(facts):
        f = f or {}
        fid = f"facts[{i}]"
        if not str(f.get("fact", "")).strip():
            reasons.append(f"{fid}: empty fact")
        if f.get("provenance") not in PROVENANCE:
            reasons.append(f"{fid}: provenance '{f.get('provenance')}' not in {sorted(PROVENANCE)}")
        if not _raw_source_resolves(f.get("raw_source"), d, obs_ids):
            reasons.append(f"{fid}: raw_source '{f.get('raw_source')}' does not resolve "
                           f"(run-dir file or observations.yaml#Oxx)")
        if not f.get("rca_link"):
            reasons.append(f"{fid}: missing rca_link back-reference")

    # 2 — playbook
    pb = kf.get("playbook") or {}
    plus_one, proposal = pb.get("plus_one"), pb.get("proposal")
    if plus_one:
        if not (pb_dir / f"{plus_one}.md").exists():
            reasons.append(f"playbook.plus_one '{plus_one}' resolves to no playbooks/{plus_one}.md "
                           f"(phantom playbook id)")
        if not (d / "playbook-append.md").exists():
            reasons.append("playbook.plus_one claimed but playbook-append.md not materialised "
                           "(+1 narrated, not done)")
    if proposal and not (d / f"playbook-proposal-{proposal}.md").exists():
        reasons.append(f"playbook.proposal '{proposal}' has no playbook-proposal-{proposal}.md")
    if not plus_one and not proposal:
        if confirmed:
            reasons.append("CONFIRMED cause(s) but playbook neither +1 nor proposal — every "
                           "confirmed cause either used a playbook path or invented one (D4)")
        elif not pb.get("none_reason"):
            reasons.append("playbook has neither plus_one/proposal nor none_reason")

    # 3 — retro
    retro = kf.get("retro") or {}
    for k in ("task_confidence", "factory_fitness"):
        v = retro.get(k)
        if not isinstance(v, int) or not (0 <= v <= 100):
            reasons.append(f"retro.{k} missing or not an int 0-100 (got {v!r})")
    if not isinstance(retro.get("red_flags"), list):
        reasons.append("retro.red_flags missing (list, may be empty)")
    improvements = retro.get("improvements")
    if not isinstance(improvements, list):
        reasons.append("retro.improvements missing (list, may be empty)")
    else:
        for j, imp in enumerate(improvements):
            if not isinstance(imp, dict) or not imp.get("title") or not imp.get("detail"):
                reasons.append(f"retro.improvements[{j}] needs title + detail")
    ff = retro.get("factory_fitness")
    if isinstance(ff, int) and ff < 100:
        accounted = bool(retro.get("deductions") or retro.get("red_flags") or improvements)
        if not accounted:
            reasons.append(f"factory_fitness={ff} < 100 with zero deductions/red_flags/improvements "
                           f"— lost points must be accounted for")

    # 4 — parking lot drained
    lot = lib.read_text(d / "parking-lot.md")
    entries = [ln for ln in lot.splitlines() if _ENTRY_RE.match(ln.strip())]
    undrained = [ln.strip()[:60] for ln in entries if "| drained:" not in ln]
    if undrained:
        reasons.append(f"parking-lot entries without a '| drained:' disposition: {undrained}")

    return {"pass": not reasons, "reasons": reasons,
            "facts": len(facts), "confirmed_causes": len(confirmed),
            "playbook": {"plus_one": plus_one, "proposal": proposal}}


def main(argv):
    if len(argv) < 2:
        print("usage: learning_harvest.py <service-area-dir> [--playbooks-dir DIR]", file=sys.stderr)
        return 2
    pb = None
    if "--playbooks-dir" in argv:
        pb = argv[argv.index("--playbooks-dir") + 1]
    res = check(argv[1], pb)
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
