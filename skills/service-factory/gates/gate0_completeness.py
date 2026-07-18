#!/usr/bin/env python3
"""Gate 0 completeness checker (Phase 1 -> Gate 0).

Guards SFE-06 / F01 (intake is a FILE, not a self-attestation) and SFE-47 /
IFM-8 (auto-pass withheld on an [INFERRED] load-bearing observable — a non-empty
field is not a confirmed one; NP1).

Auto-pass requires, mechanically:
  1. all intake artifacts on disk: jira-raw.json, env-fact-sheet.md, intake.yaml,
     and scaffold (STATUS_SNAPSHOT.yaml, ac.yaml, state.yaml);
  2. env-fact-sheet.md cites a bibliotheque INDEX lookup OR records "library silent";
  3. every load-bearing OBSERVABLE line carries [REPORTED ...] (verbatim) or
     [OBSERVED Oxx] provenance. An [INFERRED]/[ASSUMED] observable withholds
     auto-pass and forces proceed-on-candidates + a drafted reporter question.

  python3 gate0_completeness.py <service-area-dir>   # exit 0 = auto-pass granted
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import lib

REQUIRED_FILES = [
    "jira-raw.json",
    "env-fact-sheet.md",
    "intake.yaml",
    "STATUS_SNAPSHOT.yaml",
    "ac.yaml",
    "state.yaml",
]

_OBSERVABLE_RE = re.compile(r"^\s*OBSERVABLE\s*:", re.IGNORECASE)


def check(service_area: str) -> dict:
    d = Path(service_area)
    reasons = []

    files_missing = [f for f in REQUIRED_FILES if not (d / f).exists()]
    if files_missing:
        reasons.append(f"intake artifacts missing on disk: {files_missing}")

    fact = lib.read_text(d / "env-fact-sheet.md")
    library_ok = ("library silent" in fact.lower()) or bool(
        re.search(r"^\s*Library\s*:.*(\.md|bibliotheque|INDEX)", fact, re.IGNORECASE | re.MULTILINE)
    )
    if fact and not library_ok:
        reasons.append("env-fact-sheet.md has no bibliotheque INDEX citation or 'library silent' line")

    # Load-bearing observable provenance.
    inferred_observables = []
    for ln in fact.splitlines():
        if _OBSERVABLE_RE.match(ln):
            stamps = {s for s, _d, _ids in lib.parse_stamps(ln)}
            has_reported = "REPORTED" in stamps
            has_observed = lib.has_observed_citation(ln)
            if not (has_reported or has_observed):
                inferred_observables.append(ln.strip()[:80])

    reporter_q_present = bool(
        (d / "reporter-question.md").exists()
        or list(d.glob("drafts/*reporter*.md"))
        or list(d.glob("drafts/*post-comment*.md"))
    )

    if inferred_observables:
        reasons.append(
            f"load-bearing observable is [INFERRED]/[ASSUMED], not [REPORTED]/[OBSERVED]: "
            f"{inferred_observables} -> auto-pass withheld"
        )
        route = "proceed-on-candidates"
    elif files_missing or (fact and not library_ok):
        route = "bounce" if files_missing else "blocked"
    else:
        route = "proceed"

    auto_pass = not reasons
    return {
        "pass": auto_pass,  # pass == auto-pass granted
        "route": route,
        "reasons": reasons,
        "files_missing": files_missing,
        "library_ok": library_ok,
        "inferred_observables": inferred_observables,
        "reporter_question_present": reporter_q_present,
    }


def main(argv):
    if len(argv) < 2:
        print("usage: gate0_completeness.py <service-area-dir>", file=sys.stderr)
        return 2
    res = check(argv[1])
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
