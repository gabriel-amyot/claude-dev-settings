#!/usr/bin/env python3
"""Draw a reproducible random sample of (human prompt, injected pointer) pairs for relevance judging."""
import json
import os
import random

D = os.path.dirname(os.path.abspath(__file__))
KLEVER_ALIASES = os.path.expanduser("~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/ALIASES.md")
GLOBAL_ALIASES = os.path.expanduser("~/.claude/library/ALIASES.md")

notes = {}
for path in (KLEVER_ALIASES, GLOBAL_ALIASES):
    for line in open(path):
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 4 and cells[1] and not cells[1].startswith("-") and cells[1].lower() != "alias":
            notes.setdefault(cells[1], cells[3])

pairs = []
for line in open(os.path.join(D, "recall-turns.jsonl")):
    t = json.loads(line)
    for p in t["injected"]:
        pairs.append({"prompt": t["prompt"], "alias": p["alias"], "note": notes.get(p["alias"], "")[:220], "opened": p["page"] in t["opened"]})

random.seed(20261027)
sample = random.sample(pairs, min(80, len(pairs)))
with open(os.path.join(D, "judge-sample.jsonl"), "w") as fh:
    for i, s in enumerate(sample):
        fh.write(json.dumps({"id": i, **s}) + "\n")
print(f"pairs={len(pairs)} sampled={len(sample)}")
