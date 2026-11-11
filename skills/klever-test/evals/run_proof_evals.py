#!/usr/bin/env python3
"""run_proof_evals.py — Layer A suite for klever-test's deterministic evidence checks.

  scripts/classify_proof.py  PASS / FAIL / UNPROVEN for deployed-path evidence
  scripts/agui_events.py     AG-UI SSE stream conformance

Cases pin the source incidents: a 403 with no attributing log line is UNPROVEN (not
PASS); an expired credential is UNPROVEN (not FAIL); a 200 with all-null multi-word
fields is FAIL (the Goldfish casing trap); a TOOL_CALL_START with `toolName` is FAIL
(the Media Plan Zod trap); a cut stream is UNPROVEN.

Usage: python3 run_proof_evals.py [-v]. Exit 0 if all pass, 1 otherwise.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
ART = {"image": "0.12.3", "revision": "svc-00057", "evidence": "describe cmd"}
OK_PRE = [{"name": "token not expired", "state": "ok", "evidence": "exp check"}]
ALLOW_OK = {"name": "read", "expect": "allow", "client_exit": 0, "http_status": 200,
            "body": {"data": {"partner": {"name": "Acme"}}}, "expect_fields": ["data.partner.name"]}

PROOF_CASES = [
    ("p01-200-with-field-and-attributed-refusal-pass",
     {"artifact": ART, "preconditions": OK_PRE, "requires_negative_control": True,
      "observations": [ALLOW_OK, {"name": "unscoped", "expect": "refuse", "http_status": 403,
                                  "expected_refuser": "gateway",
                                  "refusal_log": "gateway: client not admitted"}],
      "not_proved": ["prod"]}, "PASS"),
    ("p02-403-without-log-line-is-unproven",
     {"artifact": ART, "preconditions": OK_PRE,
      "observations": [{"name": "unscoped", "expect": "refuse", "http_status": 403}]}, "UNPROVEN"),
    ("p03-expired-credential-is-unproven-not-fail",
     {"artifact": ART,
      "preconditions": [{"name": "token not expired", "state": "failed", "evidence": "exp"}],
      "observations": [ALLOW_OK]}, "UNPROVEN"),
    ("p04-200-with-graphql-errors-is-fail",
     {"artifact": ART, "preconditions": OK_PRE,
      "observations": [dict(ALLOW_OK, body={"data": {"partner": {"name": "Acme"}},
                                            "errors": [{"message": "denied"}]})]}, "FAIL"),
    ("p05-200-all-null-multiword-field-is-fail",
     {"artifact": ART, "preconditions": OK_PRE,
      "observations": [{"name": "proxy", "expect": "allow", "http_status": 200,
                        "items_path": "data",
                        "body": {"data": [{"id": 1, "locationType": None},
                                          {"id": 2, "locationType": None}]}}]}, "FAIL"),
    ("p06-no-artifact-binding-is-unproven",
     {"preconditions": OK_PRE, "observations": [ALLOW_OK]}, "UNPROVEN"),
    ("p07-control-claim-without-negative-control-unproven",
     {"artifact": ART, "preconditions": OK_PRE, "requires_negative_control": True,
      "observations": [ALLOW_OK]}, "UNPROVEN"),
    ("p08-client-exit-nonzero-is-unproven",
     {"artifact": ART, "preconditions": OK_PRE,
      "observations": [dict(ALLOW_OK, client_exit=28)]}, "UNPROVEN"),
    ("p09-refusal-expected-but-200-is-fail",
     {"artifact": ART, "preconditions": OK_PRE,
      "observations": [{"name": "unscoped", "expect": "refuse", "http_status": 200}]}, "FAIL"),
]


def sse(*events):
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events)


START = {"type": "RUN_STARTED"}
TEXT = {"type": "TEXT_MESSAGE_CONTENT", "delta": "Here is the plan."}
DONE = {"type": "RUN_FINISHED"}
AGUI_CASES = [
    ("a01-clean-run-pass", sse(START, {"type": "TOOL_CALL_START", "toolCallName": "draft_plan"},
                               TEXT, DONE), ["--expect-tool", "draft_plan"], "PASS"),
    ("a02-toolName-instead-of-toolCallName-fail",
     sse(START, {"type": "TOOL_CALL_START", "toolName": "draft_plan"}, TEXT, DONE), [], "FAIL"),
    ("a03-run-error-fail", sse(START, {"type": "RUN_ERROR", "message": "boom"}), [], "FAIL"),
    ("a04-cut-stream-unproven", sse(START, TEXT), [], "UNPROVEN"),
    ("a05-clarification-smoke-no-tools-pass", sse(START, TEXT, DONE), ["--expect-no-tools"], "PASS"),
    ("a06-expected-tool-not-reached-fail", sse(START, TEXT, DONE),
     ["--expect-tool", "resolve_geo"], "FAIL"),
    ("a07-empty-capture-unproven", "", [], "UNPROVEN"),
    ("a08-cut-before-any-text-unproven-not-fail", sse(START), [], "UNPROVEN"),
    ("a09-finished-with-no-text-fail", sse(START, DONE), [], "FAIL"),
]


def run(script, payload, extra, suffix):
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as fh:
        fh.write(payload)
        path = fh.name
    try:
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), path] + extra,
                              capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(path)
    return proc


def verdict_from(proc, prefix):
    for line in proc.stdout.splitlines():
        if line.startswith(prefix):
            return json.loads(line[len(prefix):]).get("verdict")
    return None


def main():
    verbose = "-v" in sys.argv
    failures, total = 0, 0
    exit_for = {"PASS": 0, "FAIL": 1, "UNPROVEN": 2}
    print("=== klever-test proof evals ===")
    suites = [("classify_proof.py", "PROOF_JSON=", [(n, json.dumps(d), [], w) for n, d, w in PROOF_CASES], ".json"),
              ("agui_events.py", "AGUI_JSON=", AGUI_CASES, ".txt")]
    for script, prefix, cases, suffix in suites:
        for name, payload, extra, want in cases:
            total += 1
            proc = run(script, payload, extra, suffix)
            got = verdict_from(proc, prefix)
            ok = got == want and proc.returncode == exit_for[want]
            print(f"  {name:52} {'PASS' if ok else 'FAIL'}")
            if not ok:
                failures += 1
                print(f"      ! verdict={got!r} rc={proc.returncode} wanted {want!r}/{exit_for[want]}")
                print(f"      | {proc.stderr.strip()[:300]}")
            elif verbose:
                print("      | " + proc.stdout.splitlines()[-1][:300])
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
