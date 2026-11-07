#!/usr/bin/env python3
"""Deterministic half of the bounded Codex review/fix loop.

    triage.py parse  <review.md>                      -> JSON: findings, verdict, warnings
    triage.py decide <triage.json> --round N [--max 5] -> JSON: next_action + the lists behind it

parse reads the output contract written by build_codex_prompt.py. It also counts raw severity words in
the whole text and warns when the parser saw fewer findings than the raw text suggests: never let a regex
eat a finding. A BLOCK verdict with no findings is reported as noise, not as a finding.

decide reads the AGENT's triage of one round. One entry per finding:
  {"id": "F1", "severity": "HIGH", "verified": true|false|"rejected", "rejection_evidence": "...",
   "provenance": "introduced"|"pre-existing"|"newly-reachable"|"unknown",
   "scope_conflict": false, "fixed": false, "filed": ""}
next_action is one of:
  verify_findings        some finding is neither verified nor rejected with evidence
  determine_provenance   a verified blocking finding has unknown provenance (compare against the base)
  escalate_scope         a verified blocking finding is blocked by a scope constraint: more rounds cannot fix it
  fix_and_recheck        fix the listed findings, then run the next round
  stop_clean             no verified CRITICAL/MAJOR remains open
  stop_cap_unresolved    the round cap is reached with blocking findings open: report them, never accept them
"""
import argparse
import json
import re
import sys

NORMALIZE = {
    "CRITICAL": "CRITICAL", "BLOCKER": "CRITICAL",
    "MAJOR": "MAJOR", "HIGH": "MAJOR",
    "MINOR": "MINOR", "MEDIUM": "MINOR",
    "NIT": "NIT", "LOW": "NIT", "INFO": "NIT", "TRIVIAL": "NIT",
}
BLOCKING = {"CRITICAL", "MAJOR"}
HEADER_RX = re.compile(r"^#{2,4}\s*(F\d+)\s*\[\s*([A-Za-z]+)\s*\]\s*(.*)$", re.M)
VERDICT_RX = re.compile(r"^\s*VERDICT:\s*(PASS|BLOCK)\s*$", re.M | re.I)
RAW_SEV_RX = re.compile(r"\[\s*(CRITICAL|BLOCKER|MAJOR|HIGH|MINOR|MEDIUM|NIT|LOW)\s*\]", re.I)


def normalize(sev):
    return NORMALIZE.get(str(sev or "").strip().upper(), "UNKNOWN")


def parse(text):
    findings = []
    for m in HEADER_RX.finditer(text):
        findings.append({"id": m.group(1), "raw_severity": m.group(2).upper(),
                         "severity": normalize(m.group(2)), "title": m.group(3).strip()})
    verdicts = VERDICT_RX.findall(text)
    verdict = verdicts[-1].upper() if verdicts else None
    warnings = []
    raw_count = len(RAW_SEV_RX.findall(text))
    if raw_count > len(findings):
        warnings.append(f"raw text holds {raw_count} bracketed severity tags but only {len(findings)} parsed findings: read the raw review")
    if verdict is None:
        warnings.append("no VERDICT line: the review is incomplete or ignored the contract")
    if verdict == "BLOCK" and not findings:
        warnings.append("BLOCK with no findings under it: noise, not a finding")
    if verdict == "PASS" and any(f["severity"] in BLOCKING for f in findings):
        warnings.append("PASS verdict but a CRITICAL/MAJOR is listed: trust the findings, not the verdict word")
    if any(f["severity"] == "UNKNOWN" for f in findings):
        warnings.append("a finding uses a severity outside the rubric")
    return {"findings": findings, "verdict": verdict, "warnings": warnings,
            "blocking_listed": sum(1 for f in findings if f["severity"] in BLOCKING)}


def is_rejected(f):
    return f.get("verified") == "rejected" and str(f.get("rejection_evidence") or "").strip() != ""


def decide(entries, round_no, max_rounds):
    for f in entries:
        f["severity"] = normalize(f.get("severity"))
    unverified = [f for f in entries if f.get("verified") is not True and not is_rejected(f)]
    verified = [f for f in entries if f.get("verified") is True]
    blocking = [f for f in verified if f["severity"] in BLOCKING]
    pre_existing = [f for f in blocking if f.get("provenance") == "pre-existing"]
    in_scope = [f for f in blocking if f.get("provenance") in ("introduced", "newly-reachable")]
    unknown = [f for f in blocking if f.get("provenance") not in ("introduced", "newly-reachable", "pre-existing")]
    open_blocking = [f for f in in_scope if not f.get("fixed")]
    scope = [f for f in open_blocking if f.get("scope_conflict")]
    unfiled = [f for f in pre_existing if not str(f.get("filed") or "").strip()]
    logged = [f for f in verified if f["severity"] not in BLOCKING]
    out = {
        "round": round_no, "max_rounds": max_rounds,
        "to_fix": [f["id"] for f in open_blocking if not f.get("scope_conflict")],
        "to_file": [f["id"] for f in unfiled],
        "logged_only": [f["id"] for f in logged],
        "rejected": [f["id"] for f in entries if is_rejected(f)],
    }
    if unverified:
        out.update(next_action="verify_findings", ids=[f.get("id") for f in unverified],
                   reason="verify each finding (or reject it with evidence) before acting")
    elif unknown:
        out.update(next_action="determine_provenance", ids=[f["id"] for f in unknown],
                   reason="reproduce each defect at the merge base; a file in the branch log does not prove the defect is new")
    elif scope:
        out.update(next_action="escalate_scope", ids=[f["id"] for f in scope],
                   reason="blocked by a scope constraint, not by difficulty: escalate to the human now")
    elif not open_blocking:
        out.update(next_action="stop_clean", reason="no verified CRITICAL/MAJOR open in scope; file pre-existing ones listed in to_file")
    elif round_no >= max_rounds:
        out.update(next_action="stop_cap_unresolved", ids=[f["id"] for f in open_blocking],
                   reason=f"round cap {max_rounds} reached with blocking findings open: report them as unresolved, never as accepted")
    else:
        out.update(next_action="fix_and_recheck", ids=out["to_fix"],
                   reason="fix these, mutation-check each fix, then run the next round scoped to the fix range")
    return out


def main(argv):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("parse")
    a.add_argument("review")
    d = sub.add_parser("decide")
    d.add_argument("triage")
    d.add_argument("--round", type=int, required=True)
    d.add_argument("--max", type=int, default=5)
    args = p.parse_args(argv)
    if args.cmd == "parse":
        with open(args.review) as handle:
            print(json.dumps(parse(handle.read()), indent=2))
        return 0
    with open(args.triage) as handle:
        data = json.load(handle)
    entries = data["findings"] if isinstance(data, dict) else data
    print(json.dumps(decide(entries, args.round, args.max), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
