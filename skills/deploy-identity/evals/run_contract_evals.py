#!/usr/bin/env python3
"""run_contract_evals.py — Layer A suite for deploy-identity/scripts/identity_contract.py.

Each case is an evidence fixture plus the verdict fields it must produce. The cases pin
the three source incidents:
  * 2026-09-14 image truth: the DAC variable alone must never yield VERIFIED.
  * 2026-09-16 layer arming: an unreadable layer must never read as ARMED, terraform
    config is not live entitlement, and no manual-apply gate is assumed.
  * 2026-11-03 rollout receipt: identity is not acceptance, and an empty-config
    validation is not a PASS.

Usage: python3 run_contract_evals.py [--script <path>] [-v]
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "identity_contract.py")

EV = "cmd recorded"
VERIFIED_IMAGE = {
    "intended": {"version": "0.11.0", "evidence": EV},
    "serving": {"version": "0.11.0", "revision": "svc-00042", "traffic_percent": 100,
                "evidence": EV},
    "source_commit": {"ref": "main@2e38022", "evidence": EV},
}


def get(d, path):
    for key in path.split("."):
        if isinstance(d, dict):
            d = d.get(key)
        elif isinstance(d, list) and key.isdigit():
            d = d[int(key)] if int(key) < len(d) else None
        else:
            return None
    return d


CASES = [
    ("01-dac-var-only-is-intended-not-verified",
     {"env": "prod", "image": {"intended": {"version": "0.11.0", "evidence": EV}}},
     {"image.status": "INTENDED_ONLY", "image.confidence": "HYPOTHESIS"},
     {"image.stamp": "[UNVERIFIED"}),
    ("02-serving-read-mapped-is-verified",
     {"env": "prod", "image": dict(VERIFIED_IMAGE, branch_tip={"ref": "dev@9f1c0aa"})},
     {"image.status": "VERIFIED", "image.confidence": "HIGH-ALLOWED", "image.tip_gap": True},
     {"image.stamp": "[VERIFIED against prod image 0.11.0 = main@2e38022]"}),
    ("03-intended-differs-from-serving-is-mismatch",
     {"env": "prod", "image": dict(VERIFIED_IMAGE,
                                   intended={"version": "0.12.0", "evidence": EV})},
     {"image.status": "MISMATCH"}, {"image.stamp": "DAC intends 0.12.0"}),
    ("04-tag-without-revision-or-digest-unverified",
     {"env": "prod", "image": {"serving": {"version": "0.11.0", "evidence": EV}}},
     {"image.status": "UNVERIFIED"}, {}),
    ("05-traffic-split-capped",
     {"env": "prod", "image": dict(VERIFIED_IMAGE, serving={
         "version": "0.11.0", "revision": "r2", "traffic_percent": 50, "evidence": EV})},
     {"image.status": "SPLIT", "image.confidence": "HYPOTHESIS"}, {}),
    ("06-serving-not-mapped-to-commit",
     {"env": "prod", "image": {"serving": VERIFIED_IMAGE["serving"]}},
     {"image.status": "UNMAPPED"}, {}),
    ("07-layer-without-evidence-is-unverified-not-armed",
     {"env": "prod", "reach": {"layers": [
         {"name": "gateway", "state": "ARMED", "kind": "live", "evidence": EV},
         {"name": "grants", "state": "ARMED", "kind": "live", "evidence": ""}]}},
     {"reach.verdict": "UNPROVEN", "reach.layers.1.state": "UNVERIFIED"}, {}),
    ("08-terraform-grant-is-configured-not-armed",
     {"env": "prod", "reach": {"layers": [
         {"name": "gateway", "state": "ARMED", "kind": "live", "evidence": EV},
         {"name": "grants", "state": "ARMED", "kind": "config", "evidence": EV}]}},
     {"reach.verdict": "CONFIGURED_NOT_EXERCISED", "reach.layers.1.state": "CONFIGURED"}, {}),
    ("09-image-gap-is-not-reachable",
     {"env": "prod", "reach": {"layers": [
         {"name": "gateway", "state": "ARMED", "kind": "live", "evidence": EV},
         {"name": "image", "state": "GAP", "kind": "live", "evidence": EV,
          "detail": "handler absent at 0.11.0"}]}},
     {"reach.verdict": "NOT_REACHABLE"}, {}),
    ("10-bounded-request-pass-is-reachable",
     {"env": "dev", "reach": {"layers": [
         {"name": "gateway", "state": "ARMED", "kind": "live", "evidence": EV},
         {"name": "grants", "state": "ARMED", "kind": "config", "evidence": EV}],
         "request": {"result": "PASS", "evidence": EV}}},
     {"reach.verdict": "REACHABLE", "reach.request": "PASS"}, {}),
    ("11-gap-plus-passing-request-is-conflict",
     {"env": "dev", "reach": {"layers": [
         {"name": "image", "state": "GAP", "kind": "live", "evidence": EV}],
         "request": {"result": "PASS", "evidence": EV}}},
     {"reach.verdict": "CONFLICT"}, {}),
    ("12-apply-not-success-is-pending-not-manual-gate",
     {"env": "prod", "image": VERIFIED_IMAGE, "receipt": {
         "expected": {"image": "0.11.0"},
         "stages": [{"name": n, "result": "success", "evidence": EV}
                    for n in ("source_review", "build", "dac_plan")]
         + [{"name": "dac_apply", "result": "running", "evidence": EV}]}},
     {"receipt.status": "INCOMPLETE", "receipt.stages.3.state": "PENDING"}, {}),
    ("13-empty-config-validate-is-not-pass",
     {"env": "dev", "image": VERIFIED_IMAGE, "receipt": {
         "expected": {"image": "0.11.0"},
         "stages": [{"name": "dac_validate", "result": "success", "config_dir": "",
                     "evidence": EV}]}},
     {"receipt.stages.0.state": "UNVERIFIED"}, {}),
    ("14-receipt-match-keeps-acceptance-unrun",
     {"env": "dev", "image": VERIFIED_IMAGE, "receipt": {
         "expected": {"image": "0.11.0"},
         "stages": [{"name": n, "result": "success", "evidence": EV}
                    for n in ("source_review", "build", "dac_plan", "dac_apply")],
         "undeployed_fixes": ["!512 reviewed after build"],
         "acceptance": [{"name": "browser", "result": "PASS", "evidence": ""},
                        {"name": "slack", "result": "PASS", "evidence": EV}]}},
     {"receipt.status": "MATCH", "receipt.acceptance.0.state": "UNRUN",
      "receipt.acceptance.1.state": "PASS",
      "receipt.undeployed_fixes.0": "!512 reviewed after build"}, {}),
    ("15-receipt-expected-differs-from-serving",
     {"env": "dev", "image": VERIFIED_IMAGE, "receipt": {
         "expected": {"image": "0.12.0"},
         "stages": [{"name": "build", "result": "success", "evidence": EV}]}},
     {"receipt.status": "MISMATCH"}, {}),
    ("16-receipt-runtime-unread-is-unproven",
     {"env": "dev", "image": {"intended": {"version": "0.12.0", "evidence": EV}},
      "receipt": {"expected": {"image": "0.12.0"},
                  "stages": [{"name": "build", "result": "success", "evidence": EV}]}},
     {"receipt.status": "RUNTIME_UNPROVEN"}, {}),
]


def run(script, evidence):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(evidence, fh)
        path = fh.name
    try:
        proc = subprocess.run([sys.executable, script, path, "--now", "2026-11-06T00:00:00Z"],
                              capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(path)
    for line in proc.stdout.splitlines():
        if line.startswith("IDENTITY_CONTRACT_JSON="):
            return json.loads(line[len("IDENTITY_CONTRACT_JSON="):]), proc
    return {}, proc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=DEFAULT_SCRIPT)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    print(f"=== deploy-identity contract evals → {os.path.basename(args.script)} ===")
    failures = 0
    for name, evidence, expected, contains in CASES:
        got, proc = run(args.script, evidence)
        problems = []
        if not got:
            problems.append(f"no IDENTITY_CONTRACT_JSON line (rc={proc.returncode}) "
                            f"{proc.stderr.strip()[:200]}")
        for path, want in expected.items():
            if get(got, path) != want:
                problems.append(f"{path}={get(got, path)!r} wanted {want!r}")
        for path, needle in contains.items():
            if needle not in str(get(got, path)):
                problems.append(f"{path}={get(got, path)!r} missing {needle!r}")
        print(f"  {name:52} {'PASS' if not problems else 'FAIL'}")
        if problems:
            failures += 1
            for p in problems:
                print(f"      ! {p}")
        if args.verbose:
            print(f"      | {json.dumps(got)}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
