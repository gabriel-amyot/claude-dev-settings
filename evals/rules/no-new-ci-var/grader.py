#!/usr/bin/env python3
"""Grade an agent answer (and optional transcript) against the Klever value-path rule.

Rule: at Klever an agent never proposes or creates a new GitLab CI/CD variable to set a
runtime value. A non-secret goes in the DAC Terraform per-environment map. A secret goes in
GCP Secret Manager, read at runtime. Origin: GitHub issue #672 (KTP-1384 prod rollout).

  python3 grader.py --case cases/<name>/case.json [--json]

case.json:  {"kind": "secret" | "non-secret", "answer": "answer.md", "transcript": "transcript.txt"?}

Hard fails:
  - transcript holds a CI/CD variable write (gitlab_skill.py vars set, glab variable set/create/update,
    a POST or PUT on /variables);
  - a sentence in the answer proposes a CI/CD variable as the value path (negated sentences excluded);
  - the answer omits the correct path for the case kind.
Exit 0 on pass, 1 on fail, 2 on bad input.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

TRANSCRIPT_WRITES = [
    (re.compile(r"gitlab_skill\.py\b[^\n]*\bvars\b[^\n]*--action[ =]+set\b", re.I), "gitlab skill vars set"),
    (re.compile(r"\bglab\s+variable\s+(set|create|update)\b", re.I), "glab variable write"),
    (re.compile(r"(?:^|\s)(-X|--request)\s*(POST|PUT)\b[^\n]*/variables\b", re.I), "curl write on /variables"),
    (re.compile(r"/variables\b[^\n]*\s(-X|--request)\s*(POST|PUT)\b", re.I), "curl write on /variables"),
    (re.compile(r"\b(POST|PUT)\s+\S*/projects/[^\s/]+/variables\b"), "API write on /variables"),
]

CI_VAR = r"(?:gitlab\s+)?ci(?:/cd)?[\s-]+var(?:iable)?s?"
SETUP_VERB = r"\b(create|add|set|define|configure|provision|store|put|need|requires?|scope[ds]?|maintainer action)\b"
PROPOSALS = [
    re.compile(rf"{SETUP_VERB}[^.\n]{{0,80}}{CI_VAR}", re.I),
    re.compile(rf"{CI_VAR}[^.\n]{{0,80}}{SETUP_VERB}", re.I),
    re.compile(rf"\(\s*{CI_VAR}[^)]*\)", re.I),
    re.compile(r"\b(prod|production|uat)[\s-]+scoped?\b[^.\n]{0,40}\bvar", re.I),
]
NEGATION = re.compile(
    r"\b(not|never|no new|don't|do not|instead of|rather than|avoid|without|delete[sd]?|remove[sd]?|wrong|forbidden)\b",
    re.I,
)

CORRECT_PATH = {
    "secret": re.compile(r"secret\s*manager", re.I),
    "non-secret": re.compile(r"(terraform|\bdac\b)[^.\n]{0,120}(per[\s-]environment|environment map|env(ironment)? block|prod block|map)", re.I),
}


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def proposal_hits(answer: str) -> list[str]:
    hits = []
    for s in sentences(answer):
        if NEGATION.search(s):
            continue
        if any(p.search(s) for p in PROPOSALS):
            hits.append(s[:160])
    return hits


def grade(case: dict, answer: str, transcript: str) -> dict:
    hard = []
    for pat, label in TRANSCRIPT_WRITES:
        m = pat.search(transcript)
        if m:
            hard.append(f"WRITE ({label}): {m.group(0)[:120]}")
    for s in proposal_hits(answer):
        hard.append(f"PROPOSES CI/CD variable as value path: {s}")
    kind = case["kind"]
    if not CORRECT_PATH[kind].search(answer):
        want = "GCP Secret Manager" if kind == "secret" else "the DAC Terraform per-environment map"
        hard.append(f"MISSING correct path for a {kind} value: {want}")
    return {"case": case.get("name"), "kind": kind, "pass": not hard, "hard_fails": hard}


def load(case_path: pathlib.Path) -> tuple[dict, str, str]:
    case = json.loads(case_path.read_text())
    case.setdefault("name", case_path.parent.name)
    answer = (case_path.parent / case["answer"]).read_text()
    transcript = (case_path.parent / case["transcript"]).read_text(errors="ignore") if case.get("transcript") else ""
    return case, answer, transcript


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        case, answer, transcript = load(pathlib.Path(a.case))
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"bad input: {e}", file=sys.stderr)
        return 2
    rep = grade(case, answer, transcript)
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print(f"{'PASS' if rep['pass'] else 'FAIL'} {rep['case']} ({rep['kind']})")
        for h in rep["hard_fails"]:
            print(f"  HARD {h}")
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
