#!/usr/bin/env python3
"""verify_emulator_stack.py — headless check that proximity-report serves EMULATOR data.

The orchestrator falls back to live dev BigQuery when the emulator cannot start. A
200 with non-empty data can then come from the wrong source. This check therefore
proves the data source first, then the endpoints.

Checks:
  1. emulator port listening (default 9050)
  2. proximity-report boot log contains "EMULATOR mode active" (else: live-BQ fallback)
  3. log scan: BigQuery failures classified as GRACEFUL (crosswalk / insights tables,
     which the emulator does not host) or ERROR (anything else)
  4. optional saved endpoint responses (--response NAME=FILE[:NEEDLE]): body has
     non-empty `data` (or is a non-empty list) and, when given, contains NEEDLE, a
     value that only the committed fixtures carry

It sends no request itself. Capture responses with curl first (request shapes: the
repo's API tests, see klever-test backend-api-tests.md).

Usage: verify_emulator_stack.py [--log PATH] [--port N] [--skip-port] [--response ...]
Output: a table, then EMULATOR_VERIFY_JSON={...}. Exit 0 all green, 1 otherwise.
"""
import argparse
import json
import re
import socket
import sys

DEFAULT_LOG = "/tmp/klever-local-report.log"
ACTIVE_MARKER = "EMULATOR mode active"
FAILURE = re.compile(r"Failed to execute BigQuery|failed to analyze|BigQueryException", re.I)
GRACEFUL = re.compile(r"crosswalk|insigt|insights|dts_external_data", re.I)


def classify_log(text):
    active = ACTIVE_MARKER in text
    graceful, errors = [], []
    for line in text.splitlines():
        if FAILURE.search(line) or ("WARN" in line and GRACEFUL.search(line)):
            (graceful if GRACEFUL.search(line) else errors).append(line.strip()[:200])
    return {"emulator_active": active, "graceful": graceful, "errors": errors}


def check_response(body, needle=None):
    data = body.get("data") if isinstance(body, dict) else body
    if data in (None, [], {}, ""):
        return False, "empty data"
    if needle and needle not in json.dumps(body):
        return False, f"fixture marker '{needle}' absent: data may not come from the emulator"
    return True, "non-empty" + (f", contains '{needle}'" if needle else "")


def port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0


def evaluate(log_text, port_state, responses):
    rows = []
    if port_state is not None:
        rows.append(("emulator port", port_state, "listening" if port_state else "not listening"))
    log = classify_log(log_text) if log_text is not None else None
    if log is None:
        rows.append(("data source", False, "report log unreadable"))
    else:
        rows.append(("data source", log["emulator_active"],
                     "EMULATOR mode active" if log["emulator_active"]
                     else "marker absent: live-BQ fallback or not booted"))
        rows.append(("bigquery errors", not log["errors"],
                     f"{len(log['errors'])} error(s), {len(log['graceful'])} graceful fallback(s)"))
    for name, body, needle in responses:
        ok, why = check_response(body, needle) if body is not None else (False, "unreadable")
        rows.append((f"endpoint {name}", ok, why))
    green = all(ok for _, ok, _ in rows)
    return {"green": green, "rows": [{"check": c, "ok": ok, "detail": d} for c, ok, d in rows],
            "log_errors": (log or {}).get("errors", []),
            "log_graceful": (log or {}).get("graceful", [])}


def parse_response_arg(arg):
    name, _, rest = arg.partition("=")
    path, _, needle = rest.partition(":")
    try:
        with open(path, encoding="utf-8") as fh:
            body = json.load(fh)
    except (OSError, ValueError):
        body = None
    return name, body, needle or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--port", type=int, default=9050)
    ap.add_argument("--skip-port", action="store_true")
    ap.add_argument("--response", action="append", default=[])
    args = ap.parse_args()
    try:
        with open(args.log, encoding="utf-8", errors="replace") as fh:
            log_text = fh.read()
    except OSError:
        log_text = None
    port_state = None if args.skip_port else port_open(args.port)
    out = evaluate(log_text, port_state, [parse_response_arg(r) for r in args.response])
    for row in out["rows"]:
        print(f"  {'OK ' if row['ok'] else 'RED'}  {row['check']:28} {row['detail']}")
    for line in out["log_errors"][:5]:
        print(f"       error: {line}")
    print(f"  {'GREEN' if out['green'] else 'RED'}: "
          f"{'gate the frontend render on this' if out['green'] else 'do not start the visual check'}")
    print("EMULATOR_VERIFY_JSON=" + json.dumps(out, sort_keys=True))
    return 0 if out["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
