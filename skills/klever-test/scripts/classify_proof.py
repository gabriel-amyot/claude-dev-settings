#!/usr/bin/env python3
"""classify_proof.py — PASS / FAIL / UNPROVEN for deployed-path evidence.

A status code is transport, not proof. This script reads one observation file that the
agent wrote after running its requests, and classifies the claim by fixed rules:

  * Evidence that does not name the deployed artifact is UNPROVEN.
  * A precondition that could not be checked (expired token, unreachable host) is
    UNPROVEN with its name. It is never reported as FAIL of the control under test.
  * "allow" observations need a 2xx, a zero client exit, every expected field present
    and non-null, and no application-level errors. A field that is null in every item
    is a FAIL with a casing hint (the snake_case / camelCase class of bug).
  * "refuse" observations need a refusal AND a service log line that attributes it to
    the expected layer. A bare 4xx is UNPROVEN: something refused, not proven which.
  * A claim about a control needs at least one negative control.

It never sends a request and never prints body values or credentials.

Usage: classify_proof.py <observations.json>
Output: a report, then PROOF_JSON={...}. Exit 0 PASS, 1 FAIL, 2 UNPROVEN.
Schema: ../references/deployed-path-proof.md.
"""
import json
import sys

RANK = {"PASS": 0, "UNPROVEN": 1, "FAIL": 2}


def dig(obj, path):
    for key in [k for k in str(path).split(".") if k]:
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list) and key.isdigit() and int(key) < len(obj):
            obj = obj[int(key)]
        else:
            return None
    return obj


def is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def all_null_fields(items):
    if not isinstance(items, list) or not items or not all(isinstance(i, dict) for i in items):
        return []
    keys = set().union(*(i.keys() for i in items))
    return sorted(k for k in keys if all(i.get(k) is None for i in items))


def classify_allow(obs, body):
    status = obs.get("http_status")
    if not isinstance(status, int) or not 200 <= status < 300:
        return "FAIL", f"expected success, got HTTP {status}"
    errors = dig(body, obs.get("errors_path", "errors"))
    if not is_empty(errors):
        return "FAIL", "HTTP 2xx but the body carries application errors"
    missing = [f for f in obs.get("expect_fields", []) if is_empty(dig(body, f))]
    if missing:
        return "FAIL", "HTTP 2xx but expected field(s) empty: " + ", ".join(missing)
    if obs.get("items_path"):
        nulls = all_null_fields(dig(body, obs["items_path"]))
        if nulls:
            return "FAIL", ("field(s) null in every item: " + ", ".join(nulls)
                            + ". Check upstream field casing against the real payload")
    return "PASS", "claim asserted on the body, not the status code"


def classify_refuse(obs):
    status = obs.get("http_status")
    if isinstance(status, int) and 200 <= status < 300:
        return "FAIL", f"expected a refusal, got HTTP {status}"
    if not str(obs.get("refusal_log", "")).strip():
        return "UNPROVEN", (f"HTTP {status}: something refused, but no service log line "
                            f"attributes it to {obs.get('expected_refuser', 'the expected layer')}")
    return "PASS", f"refusal attributed to {obs.get('expected_refuser', '?')} by its log line"


def classify_observation(obs):
    if obs.get("client_exit", 0) != 0:
        return "UNPROVEN", f"client exited {obs['client_exit']}: the request did not complete"
    if obs.get("expect") == "refuse":
        return classify_refuse(obs)
    body = obs.get("body")
    if body is None and obs.get("body_file"):
        try:
            with open(obs["body_file"], encoding="utf-8") as fh:
                body = json.load(fh)
        except (OSError, ValueError) as exc:
            return "UNPROVEN", f"body unreadable: {exc.__class__.__name__}"
    return classify_allow(obs, body)


def classify(doc):
    reasons = []
    artifact = doc.get("artifact") or {}
    if not str(artifact.get("evidence", "")).strip() or not (
            artifact.get("image") or artifact.get("revision")):
        reasons.append(("UNPROVEN", "artifact", "evidence does not name the deployed artifact"))
    for pre in doc.get("preconditions", []):
        if pre.get("state") != "ok":
            reasons.append(("UNPROVEN", f"precondition {pre.get('name', '?')}",
                            "could not be checked, so the run proves nothing"))
    rows = []
    for obs in doc.get("observations", []):
        verdict, why = classify_observation(obs)
        rows.append({"name": obs.get("name", "?"), "expect": obs.get("expect", "allow"),
                     "verdict": verdict, "why": why})
        reasons.append((verdict, obs.get("name", "?"), why))
    if not rows:
        reasons.append(("UNPROVEN", "observations", "no observation recorded"))
    if doc.get("requires_negative_control") and not any(r["expect"] == "refuse" for r in rows):
        reasons.append(("UNPROVEN", "negative control", "a control claim needs a refused request"))
    overall = max((r[0] for r in reasons), key=RANK.get, default="PASS")
    not_proved = doc.get("not_proved") or []
    return {"claim": doc.get("claim", ""), "verdict": overall, "observations": rows,
            "blocking": [{"verdict": v, "item": i, "why": w} for v, i, w in reasons if v != "PASS"],
            "artifact": {k: artifact.get(k) for k in ("image", "revision")},
            "not_proved": not_proved or ["NOT STATED: list what this run does not prove"]}


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    with open(sys.argv[1], encoding="utf-8") as fh:
        out = classify(json.load(fh))
    print(f"── proof: {out['claim']} ──")
    for row in out["observations"]:
        print(f"  {row['verdict']:9} {row['name']}: {row['why']}")
    for b in out["blocking"]:
        if b["item"] in ("artifact", "observations", "negative control") or b["item"].startswith("precondition"):
            print(f"  {b['verdict']:9} {b['item']}: {b['why']}")
    print(f"  VERDICT = {out['verdict']}")
    print("  does not prove: " + "; ".join(out["not_proved"]))
    print("PROOF_JSON=" + json.dumps(out, sort_keys=True))
    return {"PASS": 0, "FAIL": 1}.get(out["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
