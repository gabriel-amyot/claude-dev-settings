#!/usr/bin/env python3
"""run_agent_trace_evals.py — Layer A suite for gcloud/scripts/agent_trace.py.

The fixture mirrors the real gcplogs-docker-driver shape observed 2026-08-26: the app
JSON is a string inside jsonPayload.message, and uvicorn access lines are plain text.

Pinned behaviors:
  * double-parse: records are found although jsonPayload has no thread_id key
  * a tool-free turn with NO earlier tool result is NO_TOOL_EVIDENCE_IN_THREAD
  * a tool-free turn AFTER a tool result is only TOOL_FREE_TURN, with the prior
    results listed (Codex finding: tool_calls=none alone does not prove the answer
    consulted nothing)
  * a call with no logged result is CALL_WITHOUT_RESULT
  * an expected tool that never ran is reported as not reached

Usage: python3 run_agent_trace_evals.py [-v]. Exit 0 if all pass, 1 otherwise.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "agent_trace.py")
THREAD = "f1ba1dc8-37fd-4299-a022-25693acda6a2"


def entry(ts, record=None, raw=None):
    message = json.dumps(record) if record is not None else raw
    return {"timestamp": ts, "jsonPayload": {"message": message},
            "logName": "projects/p/logs/gcplogs-docker-driver"}


def step(ts, run, tools, preview=None, thread=THREAD):
    ctx = {"tool_calls": tools}
    if preview:
        ctx["text_preview"] = preview
    return entry(ts, {"event": "agent_step", "run_id": run, "thread_id": thread,
                      "message": f"agent step: tool_calls={tools or 'none'}", "context": ctx})


def result(ts, run, tool):
    return entry(ts, {"event": "tool_result", "run_id": run, "thread_id": THREAD,
                      "message": f"tool result: {tool} (2495 chars)"})


def finish(ts, run, ask):
    return entry(ts, {"event": "finish", "run_id": run, "thread_id": THREAD, "status": "done",
                      "context": {"ask": ask, "graph": "deep"}})


ENTRIES = [
    # run A: assured geo claim, no tool at all, first turn in the thread
    step("2026-08-26T18:00:01Z", "runA", [],
         "Every line item is strictly targeted to the city of St. John's"),
    finish("2026-08-26T18:00:02Z", "runA", "are we targeting St. John's city?"),
    entry("2026-08-26T18:00:03Z", raw='INFO: 10.0.0.1 - "POST /agent HTTP/1.1" 200 OK'),
    # run B: tool call with result
    step("2026-08-26T18:01:00Z", "runB", [{"name": "extract_rfp", "args": {}}]),
    result("2026-08-26T18:01:05Z", "runB", "extract_rfp"),
    step("2026-08-26T18:01:06Z", "runB", []),
    finish("2026-08-26T18:01:07Z", "runB", "here is the RFP"),
    # run C: tool-free answer after an earlier tool result
    step("2026-08-26T18:02:00Z", "runC", [], "Budget is 150000"),
    finish("2026-08-26T18:02:01Z", "runC", "what is the budget?"),
    # run D: call without result
    step("2026-08-26T18:03:00Z", "runD", ["draft_plan"]),
    finish("2026-08-26T18:03:09Z", "runD", "draft it"),
    # other thread, must be ignored
    step("2026-08-26T18:04:00Z", "runX", ["grep"], thread="other-thread"),
]


def turn(trace, run_id):
    return next((t for t in trace.get("turns", []) if t["run_id"] == run_id), {})


CHECKS = [
    ("01-double-parse-finds-thread-records", lambda t: t.get("records") == 10),
    ("02-other-thread-ignored", lambda t: "runX" not in [x["run_id"] for x in t.get("turns", [])]),
    ("03-first-turn-tool-free-no-evidence",
     lambda t: "NO_TOOL_EVIDENCE_IN_THREAD" in turn(t, "runA").get("flags", [])),
    ("04-later-tool-free-turn-lists-prior-results",
     lambda t: turn(t, "runC").get("flags") == ["TOOL_FREE_TURN"]
     and turn(t, "runC").get("prior_tool_results") == ["extract_rfp"]),
    ("05-tool-turn-with-result-not-flagged", lambda t: turn(t, "runB").get("flags") == []),
    ("06-call-without-result-flagged",
     lambda t: "CALL_WITHOUT_RESULT" in turn(t, "runD").get("flags", [])),
    ("07-expected-tool-not-reached-reported",
     lambda t: t.get("expected_not_reached") == ["resolve_geo"]),
    ("08-ask-captured-from-finish",
     lambda t: turn(t, "runA").get("ask") == "are we targeting St. John's city?"),
]


def main():
    verbose = "-v" in sys.argv
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(ENTRIES, fh)
        path = fh.name
    try:
        proc = subprocess.run([sys.executable, SCRIPT, "--thread", THREAD, "--input", path,
                               "--expect-tool", "resolve_geo", "--expect-tool", "extract_rfp"],
                              capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(path)
    trace = {}
    for line in proc.stdout.splitlines():
        if line.startswith("AGENT_TRACE_JSON="):
            trace = json.loads(line[len("AGENT_TRACE_JSON="):])
    print("=== gcloud agent_trace evals ===")
    if verbose or not trace:
        print(proc.stdout[-2000:], proc.stderr[-500:])
    failures = 0
    for name, check in CHECKS:
        ok = bool(trace) and check(trace)
        print(f"  {name:48} {'PASS' if ok else 'FAIL'}")
        failures += 0 if ok else 1
    print(f"\n{len(CHECKS) - failures}/{len(CHECKS)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
