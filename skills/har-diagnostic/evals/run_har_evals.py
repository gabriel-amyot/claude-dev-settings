#!/usr/bin/env python3
"""
run_har_evals.py — deterministic eval suite for har_parse.py.

har_parse.py has no existing test coverage. This suite feeds synthetic minimal HAR
files to the actual script via subprocess and pins the real emitted markdown report
(stdout) and exit code. Several fixtures pin known GAPS in the parser, not desired
behavior — see the inline comments and the dated eval report for detail.

Usage: python3 run_har_evals.py [--script <path>] [-v]
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

DEFAULT_SCRIPT = os.path.expanduser(
    "~/.claude-shared-config/skills/har-diagnostic/scripts/har_parse.py")


def entry(method, url, status, time_ms, body="", content_type="application/json",
          size=None, encoding=None, started="2026-07-07T12:00:00.000Z", redirect_url=None):
    headers = [{"name": "Content-Type", "value": content_type}]
    if redirect_url:
        headers.append({"name": "Location", "value": redirect_url})
    content = {"mimeType": content_type, "text": body}
    content["size"] = len(body.encode("utf-8")) if size is None else size
    if encoding:
        content["encoding"] = encoding
    return {
        "startedDateTime": started,
        "time": time_ms,
        "request": {"method": method, "url": url, "headers": []},
        "response": {"status": status, "headers": headers, "content": content},
    }


def har(entries):
    return json.dumps({"log": {"version": "1.2", "entries": entries}})


SSE_BODY = (
    "event: step\ndata: {\"step\": 1, \"type\": \"thinking\", \"content\": \"analyzing query\"}\n\n"
    "data: {\"step\": 2, \"type\": \"answer\", \"content\": \"here is the result\"}\n\n"
)

# name -> (extra_args, har_text, is_valid_json, check(stdout, returncode) -> (bool, str))
FIXTURES = {}

# SSE responses are classified by the SAME success/slow/error/empty heuristic as normal
# JSON responses (classify() runs unconditionally before the SSE branch), so a fast,
# non-empty SSE body lands in the "success" bucket AND gets its own SSE section. Pinning:
# with 1 error + 1 slow + 1 SSE entry, Healthy is 1 (the SSE entry double-counted as
# healthy), not 0 — an agent reading only the Summary tally would miss that "Healthy: 1"
# is actually the streaming response, not an extra confirmed-good call.
FIXTURES["01-error-slow-sse-mix"] = (
    [], har([
        entry("GET", "https://portal.dev.beklever.com/api/map/pois", 500, 120,
              body='{"error": "internal server error"}'),
        entry("GET", "https://portal.dev.beklever.com/api/map/flowlines", 200, 3200,
              body=json.dumps({"lines": list(range(50))})),
        entry("POST", "https://portal.dev.beklever.com/api/chatbot/stream", 200, 850,
              body=SSE_BODY, content_type="text/event-stream"),
    ]), True,
    lambda out, rc: (
        "Errors: 1" in out and "Slow (>2000ms): 1" in out and "SSE responses: 1" in out
        and "Healthy: 1" in out and "Events parsed: 2" in out
        and "GET /api/map/pois" in out and "500" in out,
        f"mixed classification counts wrong; output:\n{out}",
    ),
)

FIXTURES["02-empty-body"] = (
    [], har([
        entry("GET", "https://portal.dev.beklever.com/api/map/pois", 200, 45, body=""),
    ]), True,
    lambda out, rc: (
        "Empty Responses" in out and "Empty: 1" in out and "Errors: 0" in out,
        f"empty-body classification wrong; output:\n{out}",
    ),
)

FIXTURES["03-all-healthy"] = (
    [], har([
        entry("GET", "https://portal.dev.beklever.com/api/map/pois", 200, 300,
              body=json.dumps({"pois": [{"id": 1}, {"id": 2}]})),
        entry("GET", "https://portal.dev.beklever.com/api/map/flowlines", 200, 500,
              body=json.dumps({"lines": [{"id": 1}, {"id": 2}]})),
        entry("GET", "https://portal.dev.beklever.com/static/logo.png", 200, 20,
              body="binarydata", content_type="image/png"),
    ]), True,
    lambda out, rc: (
        "Errors: 0" in out and "Empty: 0" in out and "Slow (>2000ms): 0" in out
        and "Healthy: 2" in out and "1 filtered as noise" in out
        and "### Critical Issues" not in out,
        f"all-healthy HAR raised a false alarm or missed noise filtering; output:\n{out}",
    ),
)

# GAP: entries with a missing/absent "response" (status defaults to 0) match none of
# classify()'s status bands and fall through to "other", which is not in `buckets` — so
# they never appear in any report section (not even as an error) and are NOT reflected
# in the Summary tally, even though they ARE included in the "N analyzed" header count.
# Of 3 malformed entries here, only 1 (missing "request", status=200 present) surfaces
# as Empty; the other 2 (status-0 / fully empty) vanish silently. No crash either way.
FIXTURES["04-malformed-entries"] = (
    [], json.dumps({"log": {"entries": [
        {"request": {"url": "https://x.com/api/thing"}},
        {"response": {"status": 200}},
        {},
    ]}}), True,
    lambda out, rc: (
        rc == 0 and "3 analyzed" in out and "Empty: 1" in out and "Errors: 0" in out,
        f"expected no crash, 3 analyzed, only 1 of 3 malformed entries surfaced (gap "
        f"pin); output:\n{out}",
    ),
)

# GAP: classify() computes a "redirect" bucket for 3xx responses, but print_report()
# has NO section for it and the Summary block never mentions redirect count at all.
# A 301->302->200 chain is completely invisible in the output — only the final 200
# shows up as Healthy. This matters because IAP auth failures manifest as redirects
# (see gitlab_skill.py's own "IAP auth failed (redirect)" check) and this tool gives
# zero signal that a redirect happened at all.
FIXTURES["05-3xx-chain-gap"] = (
    [], har([
        entry("GET", "https://portal.dev.beklever.com/old-path", 301, 30, body="",
              redirect_url="/new-path"),
        entry("GET", "https://portal.dev.beklever.com/new-path", 302, 25, body="",
              redirect_url="/final-path"),
        entry("GET", "https://portal.dev.beklever.com/final-path", 200, 200,
              body=json.dumps({"ok": True})),
    ]), True,
    lambda out, rc: (
        "redirect" not in out.lower() and "301" not in out and "302" not in out
        and "Healthy: 1" in out,
        f"expected the documented gap (redirects invisible in the report): output:\n{out}",
    ),
)

FIXTURES["06-unauthorized-401"] = (
    [], har([
        entry("GET", "https://portal.dev.beklever.com/api/user-management/permissions",
              401, 60, body='{"error": "unauthorized"}'),
    ]), True,
    lambda out, rc: (
        "Errors: 1" in out and "401" in out and "permissions" in out,
        f"401 not classified as an error; output:\n{out}",
    ),
)

FIXTURES["07-noise-filtering"] = (
    [], har([
        entry("GET", "https://api.mapbox.com/styles/v1/mapbox/streets-v11", 200, 50, body="{}"),
        entry("GET", "https://portal.dev.beklever.com/app.js", 200, 80, body="console.log(1)",
              content_type="application/javascript"),
        entry("GET", "https://www.google-analytics.com/collect", 200, 10, body=""),
        entry("GET", "https://portal.dev.beklever.com/api/map/pois", 200, 150,
              body=json.dumps({"pois": []})),
    ]), True,
    lambda out, rc: (
        "3 filtered as noise" in out and "1 analyzed" in out and "Healthy: 1" in out,
        f"noise filtering did not exclude mapbox/analytics/static assets; output:\n{out}",
    ),
)

FIXTURES["08-invalid-json-file"] = (
    [], "{not valid json at all,,,", False,
    lambda out, rc: (
        rc == 1 and "ERROR: could not read HAR" in out,
        f"expected a clean exit-1 error for unparseable JSON, got rc={rc}; output:\n{out}",
    ),
)


def run_case(script, workdir, name, args_extra, har_text):
    har_path = os.path.join(workdir, f"{name}.har")
    with open(har_path, "w", encoding="utf-8") as fh:
        fh.write(har_text)
    proc = subprocess.run([sys.executable, script, har_path] + args_extra,
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=DEFAULT_SCRIPT)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.script):
        print(f"target script not found: {args.script}", file=sys.stderr)
        return 1

    failures = 0
    with tempfile.TemporaryDirectory() as workdir:
        print(f"{'case':32} {'rc':>3}  result")
        print("-" * 60)
        for name, (extra_args, har_text, _is_valid, check) in FIXTURES.items():
            rc, out = run_case(args.script, workdir, name, extra_args, har_text)
            ok, reason = check(out, rc)
            print(f"{name:32} {rc:>3}  {'PASS' if ok else 'FAIL'}")
            if not ok:
                failures += 1
                print(f"    (reason: {reason})")
            if args.verbose:
                print("    | " + out.replace("\n", "\n    | "))

    total = len(FIXTURES)
    print("-" * 60)
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
