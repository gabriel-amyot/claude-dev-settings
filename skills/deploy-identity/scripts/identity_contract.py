#!/usr/bin/env python3
"""identity_contract.py — deployed-identity contract for deploy-identity.

probe.sh answers ONE question: is the branch I read the branch that deploys.
This script answers the three questions the branch stamp cannot:

  image    which artifact actually SERVES in an environment, and which commit built it
  reach    is a route reachable end to end, layer by layer, and which layer is the gap
  receipt  does the rollout's expected source/image match the runtime, stage by stage

It never reads a live system itself. The agent collects read-only evidence (DAC
variables, Cloud Run / MIG describe output, git reads, job statuses) into one JSON
file. This script applies fixed rules to that file, so the verdict is an OUTPUT of
the evidence, never a self-rating. A layer or stage with no evidence command is
UNVERIFIED, whatever state the agent wrote for it.

Usage:
  identity_contract.py <evidence.json> [--now <iso8601>]
Output: a human report, then one machine line IDENTITY_CONTRACT_JSON={...}.
Exit code: 0 always (a probe, not a gate). The caller reads the verdicts.

Evidence schema: see ../references/identity-contract.md.
"""
import argparse
import datetime
import json
import sys

LIVE_KINDS = {"live", "runtime", "request"}
REQUIRED_STAGES = ["source_review", "build", "dac_plan", "dac_apply"]


def has_evidence(item):
    return isinstance(item, dict) and bool(str(item.get("evidence", "")).strip())


# ---------------------------------------------------------------- image ----
def evaluate_image(image, env):
    if not image:
        return None
    intended = image.get("intended") or {}
    serving = image.get("serving") or {}
    source = image.get("source_commit") or {}
    tip = image.get("branch_tip") or {}
    notes = []
    result = {"intended": intended.get("version"), "serving": serving.get("version"),
              "source_commit": source.get("ref"), "notes": notes}

    serving_read = has_evidence(serving) and serving.get("version")
    serving_pinned = bool(serving.get("digest") or serving.get("revision"))

    if not serving_read:
        if intended.get("version") and has_evidence(intended):
            result["status"] = "INTENDED_ONLY"
            result["stamp"] = (f"[UNVERIFIED — intended image {intended['version']} "
                               f"({env}), serving image not read]")
            notes.append("A DAC variable is intended configuration. An unapplied or failed "
                         "apply leaves it ahead of the runtime. Read the serving revision.")
        else:
            result["status"] = "UNVERIFIED"
            result["stamp"] = f"[UNVERIFIED — {env} image identity not read]"
        result["confidence"] = "HYPOTHESIS"
        return result

    if not serving_pinned:
        result["status"] = "UNVERIFIED"
        result["confidence"] = "HYPOTHESIS"
        result["stamp"] = (f"[UNVERIFIED — {env} serves tag {serving['version']}, "
                           f"no revision or digest read]")
        notes.append("A tag can move. Read the serving revision or image digest.")
        return result

    traffic = serving.get("traffic_percent")
    if traffic is not None and traffic < 100:
        result["status"] = "SPLIT"
        result["confidence"] = "HYPOTHESIS"
        result["stamp"] = (f"[UNVERIFIED — {env} traffic split, {serving['version']} "
                           f"serves {traffic}%]")
        notes.append("More than one revision serves. Name every revision in the claim.")
        return result

    if intended.get("version") and intended["version"] != serving["version"]:
        result["status"] = "MISMATCH"
        result["confidence"] = "HYPOTHESIS"
        result["stamp"] = (f"[UNVERIFIED — {env} serves {serving['version']}, "
                           f"DAC intends {intended['version']}]")
        notes.append("Intended and serving differ. The apply did not land, failed, or is "
                     "pending. The gap is usually the finding.")
        return result

    if not (source.get("ref") and has_evidence(source)):
        result["status"] = "UNMAPPED"
        result["confidence"] = "HYPOTHESIS"
        result["stamp"] = (f"[UNVERIFIED — {env} image {serving['version']} "
                           f"not mapped to a commit]")
        notes.append("Map the version to a tag or commit, then read config at that commit.")
        return result

    result["status"] = "VERIFIED"
    result["confidence"] = "HIGH-ALLOWED"
    result["stamp"] = f"[VERIFIED against {env} image {serving['version']} = {source['ref']}]"
    if tip.get("ref") and tip["ref"] != source["ref"]:
        notes.append(f"Branch tip {tip['ref']} differs from the deployed {source['ref']}. "
                     f"Read files at {source['ref']}, never at the tip.")
        result["tip_gap"] = True
    return result


# ---------------------------------------------------------------- reach ----
def evaluate_layer(layer):
    name = layer.get("name", "?")
    claimed = str(layer.get("state", "")).upper()
    kind = str(layer.get("kind", "")).lower()
    if not has_evidence(layer):
        return name, "UNVERIFIED", "no evidence command recorded"
    if claimed == "GAP":
        return name, "GAP", layer.get("detail", "")
    if claimed == "ARMED":
        if kind in LIVE_KINDS:
            return name, "ARMED", layer.get("detail", "")
        return name, "CONFIGURED", "read from configuration, not from the live system"
    return name, "UNVERIFIED", f"state '{claimed or 'missing'}' is not ARMED or GAP"


def evaluate_reach(reach):
    if not reach:
        return None
    rows = [evaluate_layer(l) for l in reach.get("layers", [])]
    request = reach.get("request") or {}
    request_pass = has_evidence(request) and str(request.get("result", "")).upper() == "PASS"
    states = {s for _, s, _ in rows}
    if not rows:
        verdict = "UNPROVEN"
    elif "GAP" in states and request_pass:
        verdict = "CONFLICT"
    elif "GAP" in states:
        verdict = "NOT_REACHABLE"
    elif "UNVERIFIED" in states:
        verdict = "UNPROVEN"
    elif request_pass:
        verdict = "REACHABLE"
    else:
        verdict = "CONFIGURED_NOT_EXERCISED"
    return {"layers": [{"name": n, "state": s, "detail": d} for n, s, d in rows],
            "request": "PASS" if request_pass else ("NOT_RUN" if not request else "NOT_PASS"),
            "verdict": verdict}


# -------------------------------------------------------------- receipt ----
def evaluate_stage(stage):
    name = stage.get("name", "?")
    result = str(stage.get("result", "")).lower()
    if not has_evidence(stage):
        return name, "UNVERIFIED", "no evidence recorded"
    if name == "dac_validate" and not str(stage.get("config_dir", "")).strip():
        return name, "UNVERIFIED", "validation ran with no configuration directory"
    if result in ("success", "passed", "pass"):
        return name, "PASS", stage.get("detail", "")
    if result in ("failed", "fail", "canceled", "cancelled"):
        return name, "FAIL", stage.get("detail", "")
    return name, "PENDING", f"result '{result or 'missing'}'"


def evaluate_receipt(receipt, image_result, now):
    if not receipt:
        return None
    stages = [evaluate_stage(s) for s in receipt.get("stages", [])]
    recorded = {n for n, _, _ in stages}
    missing = [s for s in REQUIRED_STAGES if s not in recorded]
    expected = (receipt.get("expected") or {}).get("image")
    serving = (image_result or {}).get("serving")
    image_status = (image_result or {}).get("status")

    if any(s == "FAIL" for _, s, _ in stages):
        status = "FAILED_STAGE"
    elif image_status != "VERIFIED":
        status = "RUNTIME_UNPROVEN"
    elif expected and serving != expected:
        status = "MISMATCH"
    elif missing or any(s != "PASS" for _, s, _ in stages):
        status = "INCOMPLETE"
    else:
        status = "MATCH"

    acceptance = []
    for item in receipt.get("acceptance", []):
        ok = has_evidence(item) and str(item.get("result", "")).upper() == "PASS"
        acceptance.append({"name": item.get("name", "?"), "state": "PASS" if ok else "UNRUN"})
    return {"generated_at": now, "status": status, "expected_image": expected,
            "serving_image": serving,
            "stages": [{"name": n, "state": s, "detail": d} for n, s, d in stages],
            "missing_stages": missing,
            "undeployed_fixes": receipt.get("undeployed_fixes", []),
            "acceptance": acceptance}


# ----------------------------------------------------------------- main ----
def evaluate(evidence, now):
    env = evidence.get("env", "?")
    image = evaluate_image(evidence.get("image"), env)
    return {"service": evidence.get("service", "?"), "env": env,
            "image": image, "reach": evaluate_reach(evidence.get("reach")),
            "receipt": evaluate_receipt(evidence.get("receipt"), image, now)}


def render(out):
    lines = [f"── identity contract: {out['service']} ({out['env']}) ──"]
    img = out["image"]
    if img:
        lines.append(f"  image   {img['status']:16} confidence {img['confidence']}")
        lines.append(f"          stamp → {img['stamp']}")
        for n in img["notes"]:
            lines.append(f"          note: {n}")
    reach = out["reach"]
    if reach:
        for layer in reach["layers"]:
            lines.append(f"  layer   {layer['name']:16} {layer['state']:12} {layer['detail']}")
        lines.append(f"  request {reach['request']}")
        lines.append(f"  REACH VERDICT = {reach['verdict']}")
    rec = out["receipt"]
    if rec:
        lines.append(f"  receipt {rec['status']} at {rec['generated_at']} "
                     f"(expected {rec['expected_image']}, serving {rec['serving_image']})")
        for st in rec["stages"]:
            lines.append(f"          stage {st['name']:14} {st['state']:10} {st['detail']}")
        for m in rec["missing_stages"]:
            lines.append(f"          stage {m:14} NOT RECORDED")
        for fix in rec["undeployed_fixes"]:
            lines.append(f"          reviewed, not deployed: {fix}")
        for acc in rec["acceptance"]:
            lines.append(f"          acceptance {acc['name']}: {acc['state']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence")
    ap.add_argument("--now", default=None)
    args = ap.parse_args()
    with open(args.evidence, encoding="utf-8") as fh:
        evidence = json.load(fh)
    now = args.now or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    out = evaluate(evidence, now)
    print(render(out))
    print("IDENTITY_CONTRACT_JSON=" + json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
