#!/usr/bin/env python3
"""Layer A evals for architect-lens: deterministic, judge-free, seconds.

Checks the skill's structure, its knowledge-base routes, the Winston wiring,
the Codex registry, the worksheet import format, a pinned method-fidelity fix,
and a copyright guard (no book text in this public repo).

Cases that need the local FoSA knowledge base SKIP when it is absent, so the
sweep stays safe on any machine. Exit 1 on any FAIL.

Run: python3 ~/.claude-shared-config/skills/architect-lens/evals/run_layer_a.py [-v]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
REPO = SKILL.parent.parent
KB = Path(os.environ.get("FOSA_KB", Path.home() / "Developer/gabriel-amyot/resources/Fundamentals of Software Architecture/kb"))
STEP_IDS = ["drivers", "candidates", "top3", "measures", "fitness", "quanta", "components", "styles", "tradeoffs", "risks"]
SHINGLE = 10
VERBOSE = "-v" in sys.argv
results: list[tuple[str, str, str]] = []


def case(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))


def check(name: str, ok: bool, detail: str = "") -> None:
    case(name, "PASS" if ok else "FAIL", detail)


def frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else ""


skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
front = frontmatter(skill_md)

# 1. structure
check("frontmatter has name architect-lens", re.search(r"^name: architect-lens$", front, re.M) is not None)
check("frontmatter has a description with trigger phrases", re.search(r"^description: .*least worst.*", front, re.M) is not None)
check("nav block has bay, when, when_not", all(re.search(rf"^\s+{k}:", front, re.M) for k in ("bay", "when", "when_not")))
check("Host compatibility section present", "## Host compatibility" in skill_md)
linked = re.findall(r"\]\(((?:references|templates)/[^)]+)\)", skill_md)
missing = [p for p in linked if not (SKILL / p).exists()]
check("every linked reference and template exists", linked and not missing, f"missing={missing}")

# 2. method fidelity pin (Codex review F04)
method = (SKILL / "references" / "method.md").read_text(encoding="utf-8")
check("F04 pin: method keeps 'critical or important'", "critical or important" in method)
check("F04 pin: top 3 chosen from the justified list", "From that final list" in method)
check("F04 pin: the 7-item rule is labeled a heuristic", "Coaching heuristic, not a book rule" in method)
check("F04 pin: no hard 'more than three critical' rejection", "more than three \"critical\": push back" not in method and "more than three as \"critical\"" not in skill_md)

# 3. worksheet import format matches the study site's journal steps
template = (SKILL / "templates" / "worksheet.md").read_text(encoding="utf-8")
block = re.search(r"```json\n(.*?)```", template, re.S)
try:
    sample = json.loads(block.group(1)) if block else None
    journal = next(iter(sample["journals"].values()))
    check("worksheet JSON parses and uses the site step ids", sorted(journal["fields"]) == sorted(STEP_IDS), f"fields={sorted(journal['fields'])}")
    check("worksheet JSON journal id is letter-first (site import rule)", re.match(r"^[A-Za-z][\w-]{0,63}$", journal["id"]) is not None)
except (ValueError, KeyError, StopIteration, AttributeError) as error:
    check("worksheet JSON parses and uses the site step ids", False, str(error))

# 4. Winston wiring
architect = REPO / "bmad" / "runtime" / "bmm" / "agents" / "architect.md"
text = architect.read_text(encoding="utf-8")
check("Winston principle points to the FoSA KB index", "FOSA_KB" in text and "INDEX.md" in text)
check("Winston menu has [AL] Architect Lens", "[AL] Architect Lens" in text)
target = re.search(r'exec="([^"]*architect-lens[^"]*)"', text)
check("[AL] targets a path inside the BMAD payload", bool(target) and "{project-root}/_bmad/" in target.group(1), target.group(1) if target else "")
if target:
    run = subprocess.run([sys.executable, str(REPO / "bmad" / "bmad.py"), "read", target.group(1).split("/_bmad/", 1)[1]], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    check("bmad.py read resolves the [AL] handoff", run.returncode == 0 and "architect-lens" in run.stdout, run.stderr.strip()[:200])

# 5. Codex registry
registry = json.loads((REPO / "docs" / "codex-linked-skills.json").read_text(encoding="utf-8"))
check("Codex linked-skills record lists architect-lens", any(e.get("alias") == "architect-lens" for e in registry.get("entries", [])))

# 6. KB routes (skip without the KB)
routing = (SKILL / "references" / "kb-routing.md").read_text(encoding="utf-8")
if KB.exists():
    aliases = dict(re.findall(r"- `(\w+)` = `([\w./-]+)`", routing))
    routes = re.findall(r"`((?:[A-Z]\d+|P0|reference|part-[\w-]+)/[\w./-]+\.(?:md|json))`", routing)
    bad = [r for r in routes if not (KB / aliases.get(r.split("/", 1)[0], r.split("/", 1)[0]) / r.split("/", 1)[1]).exists()]
    check(f"all {len(routes)} KB routes resolve", routes and not bad, f"bad={bad}")
else:
    case("KB routes resolve", "SKIP", f"no KB at {KB}")

# 7. copyright guard: no 10-word run of book text in the public repo files this skill owns
owned = list(SKILL.rglob("*.md")) + [architect, REPO / "bmad" / "custom" / "architect-lens-handoff.md"]
if KB.exists():
    def words(text: str) -> list[str]:
        return re.findall(r"[a-z0-9']+", text.lower())

    book = set()
    for section in KB.rglob("[0-9][0-9]-*.md"):
        tokens = words(section.read_text(encoding="utf-8"))
        book.update(" ".join(tokens[i:i + SHINGLE]) for i in range(len(tokens) - SHINGLE + 1))
    leaks = []
    for path in owned:
        tokens = words(path.read_text(encoding="utf-8"))
        hits = {" ".join(tokens[i:i + SHINGLE]) for i in range(len(tokens) - SHINGLE + 1)} & book
        leaks += [f"{path.name}: {h}" for h in sorted(hits)[:3]]
    check(f"copyright guard: no {SHINGLE}-word book run in {len(owned)} public files", not leaks, "; ".join(leaks[:5]))
else:
    case("copyright guard", "SKIP", f"no KB at {KB}")

failed = [r for r in results if r[1] == "FAIL"]
for name, status, detail in results:
    if VERBOSE or status != "PASS":
        print(f"{status} {name}" + (f"  ({detail})" if detail and status != "PASS" else ""))
print(f"architect-lens layer A: {sum(r[1] == 'PASS' for r in results)} pass, {len(failed)} fail, {sum(r[1] == 'SKIP' for r in results)} skip")
sys.exit(1 if failed else 0)
