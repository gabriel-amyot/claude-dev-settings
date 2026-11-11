#!/usr/bin/env python3
"""run_verify_evals.py — Layer A suite for klever-local-stack/scripts/verify_emulator_stack.py.

Hermetic: every case writes a fake report log and saved responses to a temp dir and
runs the script with --skip-port. No stack, no network.

Key case (03): endpoints return 200 with data, but the boot log has no
"EMULATOR mode active". The orchestrator fell back to live BigQuery, so the check must
be RED. HTTP 200 plus non-empty data is not proof of the data source.

Usage: python3 run_verify_evals.py [-v]. Exit 0 if all pass, 1 otherwise.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "verify_emulator_stack.py")
BOOT_OK = "INFO BigqueryClient EMULATOR mode active host=http://localhost:9050\n"
CROSSWALK_WARN = "WARN CbgToZipCrosswalkAdapter crosswalk table missing, using fallback\n"
REAL_500 = "ERROR MapService Failed to execute BigQuery query: failed to analyze\n"
LOC = {"data": [{"locationId": 9001, "advertiserId": 842, "city": "Toronto"}]}

CASES = [
    ("01-emulator-active-data-green", BOOT_OK, {"locations": (LOC, "Toronto")}, True),
    ("02-crosswalk-warning-is-graceful", BOOT_OK + CROSSWALK_WARN, {"locations": (LOC, None)}, True),
    ("03-200-data-but-no-emulator-marker-red", "INFO started\n", {"locations": (LOC, None)}, False),
    ("04-real-bigquery-failure-red", BOOT_OK + REAL_500, {"locations": (LOC, None)}, False),
    ("05-empty-data-red", BOOT_OK, {"county": ({"data": []}, None)}, False),
    ("06-fixture-marker-absent-red", BOOT_OK, {"locations": (LOC, "Lumberjack")}, False),
]


def run_case(log_text, responses):
    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "report.log")
        with open(log, "w") as fh:
            fh.write(log_text)
        args = [sys.executable, SCRIPT, "--log", log, "--skip-port"]
        for name, (body, needle) in responses.items():
            path = os.path.join(tmp, f"{name}.json")
            with open(path, "w") as fh:
                json.dump(body, fh)
            args += ["--response", f"{name}={path}" + (f":{needle}" if needle else "")]
        proc = subprocess.run(args, capture_output=True, text=True, timeout=30)
    for line in proc.stdout.splitlines():
        if line.startswith("EMULATOR_VERIFY_JSON="):
            return json.loads(line[len("EMULATOR_VERIFY_JSON="):]), proc
    return {}, proc


def main():
    verbose = "-v" in sys.argv
    failures = 0
    print("=== klever-local-stack emulator verify evals ===")
    for name, log_text, responses, want_green in CASES:
        got, proc = run_case(log_text, responses)
        ok = got.get("green") is want_green and proc.returncode == (0 if want_green else 1)
        print(f"  {name:44} {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures += 1
            print(f"      ! green={got.get('green')!r} rc={proc.returncode} wanted {want_green}")
            print(f"      | {proc.stderr.strip()[:300]}")
        if verbose:
            print(f"      | {json.dumps(got.get('rows'))}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
