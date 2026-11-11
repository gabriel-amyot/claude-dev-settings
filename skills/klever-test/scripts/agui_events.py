#!/usr/bin/env python3
"""agui_events.py — summarize and check a captured AG-UI SSE stream.

Reads the raw text of an SSE response from an agent's POST /agent (saved with
`curl -sN ... > stream.txt`). It does not open a connection.

Checks:
  * the stream ends in RUN_FINISHED or RUN_ERROR (else it was cut: UNPROVEN)
  * every TOOL_CALL_START carries toolCallName (a `toolName` key breaks the portal's
    Zod validation, a known past bug)
  * at least one non-empty TEXT_MESSAGE_CONTENT delta, unless --allow-no-text
  * --expect-tool NAME: that tool was called; --expect-no-tools: no tool was called

Usage: agui_events.py <stream.txt> [--expect-tool NAME ...] [--expect-no-tools] [--allow-no-text]
Output: a report, then AGUI_JSON={...}. Exit 0 PASS, 1 FAIL, 2 UNPROVEN.
"""
import argparse
import json
import sys


def parse_events(text):
    events, bad = [], 0
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload:
            continue
        try:
            events.append(json.loads(payload))
        except ValueError:
            bad += 1
    return events, bad


def check(events, bad, expect_tools=(), expect_no_tools=False, allow_no_text=False):
    types = [e.get("type", "?") for e in events]
    tools, problems = [], []
    for e in events:
        if e.get("type") == "TOOL_CALL_START":
            if e.get("toolCallName"):
                tools.append(e["toolCallName"])
            else:
                key = "toolName" if "toolName" in e else "no name key"
                problems.append(f"TOOL_CALL_START without toolCallName ({key})")
    text = "".join(str(e.get("delta", "")) for e in events if e.get("type") == "TEXT_MESSAGE_CONTENT")
    errors = [e for e in events if e.get("type") == "RUN_ERROR"]
    terminal = types[-1] if types else None
    unproven = []
    if not events:
        unproven.append("no SSE data events in the capture")
    elif terminal not in ("RUN_FINISHED", "RUN_ERROR"):
        unproven.append(f"stream ends with {terminal}, not a terminal event (cut or timed out)")
    if bad:
        problems.append(f"{bad} data line(s) are not valid JSON")
    for err in errors:
        problems.append("RUN_ERROR: " + str(err.get("message") or err.get("code") or "no message"))
    if terminal == "RUN_FINISHED" and not text.strip() and not allow_no_text:
        problems.append("no TEXT_MESSAGE_CONTENT text")
    for name in expect_tools:
        if name not in tools:
            problems.append(f"expected tool {name} was not called")
    if expect_no_tools and tools:
        problems.append("expected no tool calls, got: " + ", ".join(tools))
    verdict = "FAIL" if problems else ("UNPROVEN" if unproven else "PASS")
    return {"verdict": verdict, "event_types": types, "tools": tools,
            "text_chars": len(text), "problems": problems, "unproven": unproven}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stream")
    ap.add_argument("--expect-tool", action="append", default=[])
    ap.add_argument("--expect-no-tools", action="store_true")
    ap.add_argument("--allow-no-text", action="store_true")
    args = ap.parse_args()
    with open(args.stream, encoding="utf-8", errors="replace") as fh:
        events, bad = parse_events(fh.read())
    out = check(events, bad, args.expect_tool, args.expect_no_tools, args.allow_no_text)
    print(f"── AG-UI stream: {len(events)} events, tools={out['tools'] or 'none'}, "
          f"text={out['text_chars']} chars ──")
    for p in out["problems"]:
        print(f"  FAIL      {p}")
    for u in out["unproven"]:
        print(f"  UNPROVEN  {u}")
    print(f"  VERDICT = {out['verdict']}")
    print("AGUI_JSON=" + json.dumps(out, sort_keys=True))
    return {"PASS": 0, "FAIL": 1}.get(out["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
