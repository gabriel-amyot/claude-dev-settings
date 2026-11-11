#!/usr/bin/env python3
"""Check the Codex round-2 claims about measure_recall.py and the judge sample."""
import collections
import glob
import json
import os
import time

HOME = os.path.expanduser("~")
D = os.path.dirname(os.path.abspath(__file__))
cutoff = time.time() - 45 * 86400

list_text_users = 0
recall_after_list_text = 0
oldest_event = None
for f in glob.glob(HOME + "/.claude/projects/-Users-gamyot-Developer-grp-beklever-com*/*.jsonl"):
    if os.path.getmtime(f) < cutoff:
        continue
    last_kind = None
    for line in open(f, errors="replace"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        ts = d.get("timestamp")
        if ts and (oldest_event is None or ts < oldest_event):
            oldest_event = ts
        if d.get("type") == "user":
            c = d.get("message", {}).get("content")
            if isinstance(c, str):
                last_kind = "str"
            elif isinstance(c, list) and any(x.get("type") in ("text", "image") for x in c) and not any(x.get("type") == "tool_result" for x in c):
                last_kind = "list-text"
                list_text_users += 1
        a = d.get("attachment") or {}
        if a.get("hookEvent") == "UserPromptSubmit" and "bibliotheque-recall" in (a.get("command") or "") and (a.get("stdout") or "").strip():
            if last_kind == "list-text":
                recall_after_list_text += sum(1 for ln in a["stdout"].splitlines() if ln.startswith("  - [["))

sample = [json.loads(l) for l in open(os.path.join(D, "judge-sample.jsonl"))]
prompts = [s["prompt"] for s in sample]
print("user messages with list text/image content (not tool results):", list_text_users)
print("recall pointers following a list-content prompt (misattributed by measure_recall.py):", recall_after_list_text)
print("oldest event timestamp inside the '45-day' file window:", oldest_event)
print("judge sample: rows", len(sample), "distinct prompts", len(set(prompts)), "truncated at 300 chars", sum(1 for p in prompts if len(p) >= 300))
