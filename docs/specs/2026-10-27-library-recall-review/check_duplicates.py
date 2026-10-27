#!/usr/bin/env python3
"""Count recall-hook outputs per real prompt, to tell a double-registered hook from a counting bug."""
import collections
import glob
import json
import os

HOME = os.path.expanduser("~")
runs_per_prompt = collections.Counter()
commands = collections.Counter()
example = None
for f in glob.glob(HOME + "/.claude/projects/-Users-gamyot-Developer-grp-beklever-com*/*.jsonl"):
    last = None
    for line in open(f, errors="replace"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "user" and isinstance(d.get("message", {}).get("content"), str):
            last = (os.path.basename(f), d.get("uuid"))
        a = d.get("attachment") or {}
        if a.get("hookEvent") == "UserPromptSubmit" and "bibliotheque-recall" in (a.get("command") or "") and (a.get("stdout") or "").strip():
            runs_per_prompt[last] += 1
            commands[a.get("command")] += 1
            if runs_per_prompt[last] == 2 and example is None:
                example = last
dist = collections.Counter(runs_per_prompt.values())
print("commands:", dict(commands))
print("outputs-per-prompt distribution:", dict(dist))
print("example prompt with >1 output:", example)
