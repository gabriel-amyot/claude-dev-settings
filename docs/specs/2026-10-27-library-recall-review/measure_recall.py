#!/usr/bin/env python3
"""Measure the bibliotheque-recall hook against real Klever session transcripts.

For every real user prompt in the Klever project transcripts:
  - what the recall hook actually injected (from the recorded UserPromptSubmit hook output)
  - which library pages the agent then opened during that turn (Read, Bash, Grep, Agent prompt)
Outputs:
  - recall-metrics.json   aggregate numbers
  - recall-turns.jsonl    one row per prompt (prompt excerpt, injected, opened)
  - recall-report.md      readable summary
Also measures ALIASES.md structure and auto-memory writes vs library writes.

Run: python3 measure_recall.py [--days 45]
Only reads ~/.claude/projects/-Users-gamyot-Developer-grp-beklever-com* (Klever scope).
"""
import argparse
import glob
import json
import os
import re
import time
from collections import Counter, defaultdict

HOME = os.path.expanduser("~")
OUT = os.path.dirname(os.path.abspath(__file__))
KLEVER_LIB = f"{HOME}/Developer/grp-beklever-com/project-management/documentation/bibliotheque"
GLOBAL_LIB = f"{HOME}/.claude/library"
POINTER = re.compile(r"^\s+- \[\[(.+?)\]\] → (\S+)")
LIB_PATH = re.compile(r"(documentation/bibliotheque/[^\s'\"`)]+\.md|\.claude/library/[^\s'\"`)]+\.md)")
MEMORY_PATH = re.compile(r"/\.claude/projects/[^/]+/memory/")


def norm(p):
    p = p.replace(HOME, "~")
    m = LIB_PATH.search(p)
    return m.group(1) if m else p


def is_real_prompt(content):
    if not isinstance(content, str):
        return False
    s = content.strip()
    if len(s) < 3:
        return False
    return not s.startswith(("<task-notification", "<system-reminder", "<command-", "<local-command", "Caveat:", "[Request interrupted"))


def tool_texts(item):
    name, inp = item.get("name", ""), item.get("input", {}) or {}
    yield name, " ".join(str(v) for v in inp.values() if isinstance(v, (str, int)))


def aliases_stats(lib):
    path = os.path.join(lib, "ALIASES.md")
    if not os.path.isfile(path):
        return None
    rows, with_kw, pages = 0, 0, Counter()
    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|(?:\s*([^|]*?)\s*\|)?")
    for line in open(path):
        m = row_re.match(line)
        if not m or m.group(1).lower() in ("alias", "---", ":---") or m.group(1).startswith("-"):
            continue
        rows += 1
        pages[m.group(2)] += 1
        if (m.group(4) or "").strip():
            with_kw += 1
    md_pages = [p for p in glob.glob(f"{lib}/**/*.md", recursive=True)
                if "/_archive/" not in p and "/inbox/" not in p and os.path.basename(p) not in ("INDEX.md", "ALIASES.md", "LOG.md", "README.md", "CATALOG.md")]
    rel = {os.path.relpath(p, lib) for p in md_pages}
    return {
        "alias_rows": rows,
        "rows_with_keyword_column": with_kw,
        "distinct_pages_aliased": len(pages),
        "pages_on_disk": len(rel),
        "pages_with_no_alias_row": len(rel - set(pages)),
        "max_rows_for_one_page": pages.most_common(1)[0] if pages else None,
        "aliases_md_bytes": os.path.getsize(path),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    args = ap.parse_args()
    cutoff = time.time() - args.days * 86400

    files = [f for d in glob.glob(f"{HOME}/.claude/projects/-Users-gamyot-Developer-grp-beklever-com*")
             for f in glob.glob(f"{d}/*.jsonl") if os.path.getmtime(f) >= cutoff]

    turns = []
    machine_turns = []
    memory_writes, library_writes = [], []
    for f in files:
        cur = None
        for line in open(f, errors="replace"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            if t == "user":
                c = d.get("message", {}).get("content")
                if isinstance(c, str):
                    cur = {"file": os.path.basename(f), "ts": d.get("timestamp"), "prompt": c.strip()[:300],
                           "injected": [], "opened": set(), "hook_fired": False, "human": is_real_prompt(c)}
                    (turns if cur["human"] else machine_turns).append(cur)
            elif t == "attachment" and cur is not None:
                a = d.get("attachment", {})
                if a.get("hookEvent") == "UserPromptSubmit" and "bibliotheque-recall" in (a.get("command") or ""):
                    cur["hook_fired"] = True
                    for ln in (a.get("stdout") or "").splitlines():
                        m = POINTER.match(ln)
                        if m:
                            cur["injected"].append({"alias": m.group(1), "page": norm(m.group(2))})
            elif t == "assistant":
                for item in d.get("message", {}).get("content", []) or []:
                    if item.get("type") != "tool_use":
                        continue
                    for name, text in tool_texts(item):
                        for m in LIB_PATH.finditer(text):
                            if cur is not None and name in ("Read", "Bash", "Grep", "Agent", "Task", "Glob"):
                                cur["opened"].add(m.group(1))
                        target = (item.get("input") or {}).get("file_path", "")
                        if name in ("Write", "Edit") and MEMORY_PATH.search(target or ""):
                            memory_writes.append({"file": os.path.basename(f), "ts": d.get("timestamp"), "path": target.replace(HOME, "~")})
                        if name in ("Write", "Edit") and LIB_PATH.search(target or ""):
                            library_writes.append(target.replace(HOME, "~"))

    n = len(turns)
    fired = [x for x in turns if x["injected"]]
    pointers = [(x, p) for x in fired for p in x["injected"]]
    consumed = [(x, p) for x, p in pointers if p["page"] in x["opened"]]
    alias_counter = Counter(p["alias"] for _, p in pointers)
    page_inj = Counter(p["page"] for _, p in pointers)
    page_used = Counter(p["page"] for _, p in consumed)
    opened_without_pointer = Counter(pg for x in turns for pg in x["opened"] if pg not in {p["page"] for p in x["injected"]})
    turns_opening_library = [x for x in turns if x["opened"]]
    turns_opening_but_no_pointer = [x for x in turns_opening_library if not x["injected"]]

    metrics = {
        "window_days": args.days,
        "transcripts": len(files),
        "real_prompts": n,
        "prompts_with_injection": len(fired),
        "injection_rate": round(len(fired) / n, 3) if n else 0,
        "pointers_injected": len(pointers),
        "avg_pointers_when_fired": round(len(pointers) / len(fired), 2) if fired else 0,
        "pointers_opened_same_turn": len(consumed),
        "pointer_consumption_rate": round(len(consumed) / len(pointers), 3) if pointers else 0,
        "machine_prompts": len(machine_turns),
        "machine_prompts_with_injection": sum(1 for x in machine_turns if x["injected"]),
        "machine_pointers_injected": sum(len(x["injected"]) for x in machine_turns),
        "turns_that_opened_any_library_page": len(turns_opening_library),
        "of_those_with_no_pointer_injected": len(turns_opening_but_no_pointer),
        "top_injected_aliases": alias_counter.most_common(20),
        "top_injected_pages_never_opened": [(pg, c) for pg, c in page_inj.most_common(60) if page_used[pg] == 0][:20],
        "top_pages_opened_without_pointer": opened_without_pointer.most_common(20),
        "auto_memory_writes": len(memory_writes),
        "library_writes": len(library_writes),
        "auto_memory_write_samples": memory_writes[-15:],
        "aliases_klever": aliases_stats(KLEVER_LIB),
        "aliases_global": aliases_stats(GLOBAL_LIB),
        "memory_dirs": {os.path.basename(os.path.dirname(m)): len(glob.glob(f"{os.path.dirname(m)}/*.md"))
                        for m in glob.glob(f"{HOME}/.claude/projects/-Users-gamyot-Developer-grp-beklever-com*/memory/MEMORY.md")},
    }

    with open(os.path.join(OUT, "recall-metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=2, default=list)
    with open(os.path.join(OUT, "recall-turns.jsonl"), "w") as fh:
        for x in turns:
            fh.write(json.dumps({**x, "opened": sorted(x["opened"])}) + "\n")

    lines = [f"# Recall hook measurement ({args.days} days, Klever transcripts)", ""]
    for k in ("transcripts", "real_prompts", "prompts_with_injection", "injection_rate", "pointers_injected",
              "avg_pointers_when_fired", "machine_prompts", "machine_prompts_with_injection", "machine_pointers_injected", "pointers_opened_same_turn", "pointer_consumption_rate",
              "turns_that_opened_any_library_page", "of_those_with_no_pointer_injected", "auto_memory_writes", "library_writes"):
        lines.append(f"- **{k}**: {metrics[k]}")
    lines += ["", "## ALIASES structure", "```json", json.dumps({"klever": metrics["aliases_klever"], "global": metrics["aliases_global"]}, indent=2, default=list), "```"]
    for title, key in (("Most injected aliases", "top_injected_aliases"),
                       ("Pages injected often but never opened", "top_injected_pages_never_opened"),
                       ("Pages opened without a pointer (recall misses, proxy)", "top_pages_opened_without_pointer")):
        lines += ["", f"## {title}"] + [f"- {a} ({c})" for a, c in metrics[key]]
    lines += ["", "## Auto-memory dirs (file counts)"] + [f"- {k}: {v}" for k, v in metrics["memory_dirs"].items()]
    with open(os.path.join(OUT, "recall-report.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:16]))


if __name__ == "__main__":
    main()
