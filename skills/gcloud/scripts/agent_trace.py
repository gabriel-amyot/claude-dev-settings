#!/usr/bin/env python3
"""agent_trace.py — rebuild what a deployed agent did in one thread, from its logs.

For agents that log through the Docker gcplogs driver: the app's structured JSON is a
STRING inside jsonPayload.message. A filter on jsonPayload.thread_id matches zero rows.
So this script pulls the log, double-parses each message, then filters by thread.

Read-only. It runs `gcloud logging read` (or reads a saved dump) and nothing else.

What it reports, per run (turn) in timestamp order: the user ask, the tools called,
tool results, the finish status, errors. Then flags:
  TOOL_FREE_TURN              the turn called no tool; prior tool results in the thread
                              are listed, because a tool-free answer can rest on them
  NO_TOOL_EVIDENCE_IN_THREAD  the turn called no tool AND no earlier turn returned a tool
                              result: any factual claim in it rests on nothing logged
  CALL_WITHOUT_RESULT         a tool was called but no tool_result was logged
  TELEMETRY_GAP               a finish with no agent_step, or the reverse
  ERROR                       an error event in the turn
The script cannot judge whether an answer makes a factual claim. Read text_preview.

Usage:
  agent_trace.py --thread <id> --input <dump.json>
  agent_trace.py --thread <id> --project <project-id> [--freshness 6h] [--log gcplogs-docker-driver]
  [--expect-tool NAME ...]   report whether these code paths were reached in the thread
Project IDs per agent: the org bibliothèque (Klever: stack/media-plan-agent-service.md).
Output: a timeline, then AGENT_TRACE_JSON={...}. Exit 0 (a probe, not a gate).
"""
import argparse
import json
import os
import subprocess
import sys
import time

OUT_DIR = "/tmp/gcloud-logs"


def app_record(entry):
    payload = entry.get("jsonPayload") or {}
    message = payload.get("message")
    record = None
    if isinstance(message, str) and message.lstrip().startswith("{"):
        try:
            record = json.loads(message)
        except ValueError:
            record = None
    if record is None and payload.get("event"):
        record = payload
    if record is None:
        return None
    record = dict(record)
    record.setdefault("_ts", entry.get("timestamp", ""))
    return record


def tool_names(record):
    calls = (record.get("context") or {}).get("tool_calls") or []
    names = []
    for call in calls:
        if isinstance(call, dict):
            names.append(call.get("name") or call.get("tool") or "?")
        else:
            names.append(str(call))
    return names


def result_name(record):
    ctx = record.get("context") or {}
    if ctx.get("tool"):
        return ctx["tool"]
    msg = str(record.get("message", ""))
    if msg.startswith("tool result:"):
        return msg[len("tool result:"):].strip().split(" ")[0]
    return "?"


def build_trace(entries, thread, expect_tools=()):
    records = [r for r in (app_record(e) for e in entries)
               if r and r.get("thread_id") == thread]
    records.sort(key=lambda r: r.get("_ts", ""))
    runs, order = {}, []
    for r in records:
        run_id = r.get("run_id", "?")
        if run_id not in runs:
            runs[run_id] = {"run_id": run_id, "ts": r.get("_ts", ""), "ask": None, "steps": 0,
                            "tools": [], "results": [], "finish": None, "errors": [],
                            "text_preview": None}
            order.append(run_id)
        run = runs[run_id]
        event = r.get("event")
        if event == "agent_step":
            run["steps"] += 1
            run["tools"] += tool_names(r)
            preview = (r.get("context") or {}).get("text_preview")
            if preview:
                run["text_preview"] = preview[:160]
        elif event == "tool_result":
            run["results"].append(result_name(r))
        elif event == "finish":
            run["finish"] = r.get("status")
            run["ask"] = (r.get("context") or {}).get("ask")
        elif event == "error":
            run["errors"].append(str(r.get("message", ""))[:160])
    prior_results = []
    turns = []
    for run_id in order:
        run = runs[run_id]
        flags = []
        if not run["tools"] and run["steps"]:
            flags.append("TOOL_FREE_TURN" if prior_results else "NO_TOOL_EVIDENCE_IN_THREAD")
        missing = [t for t in run["tools"] if t not in run["results"]]
        if missing:
            flags.append("CALL_WITHOUT_RESULT")
        if (run["finish"] is not None) != (run["steps"] > 0):
            flags.append("TELEMETRY_GAP")
        if run["errors"]:
            flags.append("ERROR")
        run["flags"] = flags
        run["prior_tool_results"] = sorted(set(prior_results))
        turns.append(run)
        prior_results += run["results"]
    called = {t for run in turns for t in run["tools"]}
    return {"thread_id": thread, "records": len(records), "turns": turns,
            "tools_reached": sorted(called),
            "expected_not_reached": [t for t in expect_tools if t not in called]}


def fetch(project, log_name, freshness):
    os.makedirs(OUT_DIR, exist_ok=True)
    flt = f'logName="projects/{project}/logs/{log_name}"'
    proc = subprocess.run(["gcloud", "logging", "read", flt, "--project", project,
                           f"--freshness={freshness}", "--format=json", "--limit=5000"],
                          capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        print("gcloud logging read failed: " + proc.stderr.strip()[:300], file=sys.stderr)
        sys.exit(1)
    path = os.path.join(OUT_DIR, f"agent-trace_{project}_{int(time.time())}.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(proc.stdout)
    return json.loads(proc.stdout or "[]"), path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thread", required=True)
    ap.add_argument("--input")
    ap.add_argument("--project")
    ap.add_argument("--freshness", default="6h")
    ap.add_argument("--log", default="gcplogs-docker-driver")
    ap.add_argument("--expect-tool", action="append", default=[])
    args = ap.parse_args()
    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            entries, source = json.load(fh), args.input
    elif args.project:
        entries, source = fetch(args.project, args.log, args.freshness)
    else:
        ap.error("give --input or --project")
    trace = build_trace(entries, args.thread, args.expect_tool)
    trace["source"] = source
    print(f"── agent trace {args.thread}: {trace['records']} records, "
          f"{len(trace['turns'])} turns (raw: {source}) ──")
    for t in trace["turns"]:
        print(f"  {t['ts'][:19]} run {t['run_id']} finish={t['finish']} "
              f"tools={t['tools'] or 'none'} {' '.join(t['flags'])}")
        if t["ask"]:
            print(f"      ask: {str(t['ask'])[:120]!r}")
        if "TOOL_FREE_TURN" in t["flags"]:
            print(f"      prior tool results in thread: {', '.join(t['prior_tool_results'])}")
    if trace["expected_not_reached"]:
        print("  NOT REACHED: " + ", ".join(trace["expected_not_reached"]))
    if not trace["records"]:
        print("  no records for this thread: check the window, the project and the log name")
    print("AGENT_TRACE_JSON=" + json.dumps(trace, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
