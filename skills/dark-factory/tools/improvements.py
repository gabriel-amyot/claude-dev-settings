#!/usr/bin/env python3
"""The dark-factory improvement queue — one tracked list, deduped and counted.

Why this exists
---------------
For four months the Retro wrote its improvements to `runs/<run>.yaml` and to a markdown handoff in
whatever session folder happened to be active. 26 such handoffs accumulated; nothing read them on the
way into a run. The result (audited 2026-10-05): 13 retros independently re-filed a finding an earlier
retro had already made, and the only two themes that ever went quiet were the two someone happened to
turn into a JS gate.

A proposal written to a fresh file every time cannot accumulate evidence. The same ask filed nine
times reads as nine separate small notes instead of one loud one. This queue is the fix: ONE file,
entries deduped by key, with `times_proposed` and the run ids that proposed them. The ninth filing
bumps a counter to 9 rather than writing a ninth file.

It deliberately does NOT auto-apply anything. Landing a change is a human writing gate code, and the
audit's central finding is that only schema fields and JS gates stick. What this buys is that the
human sees "asked 9 times, still open" instead of having to re-derive it from 54 YAML files.

Usage
-----
    improvements.py add --key review-severity-gate --title "..." --detail "..." --run run-2026-10-02-KTP-1275
    improvements.py list                 # open, most-proposed first
    improvements.py list --all
    improvements.py land review-severity-gate --version 0.10.1 --note "blockingFindings()"
    improvements.py reject some-key --why "superseded by X"
    improvements.py seed                 # backfill from runs/*.yaml (one-off)
"""
import argparse
import datetime
import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml: python3 -m pip install --user pyyaml")

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "improvements" / "QUEUE.yaml"
RUNS = ROOT / "runs"

# Same theme vocabulary the miner uses, so `seed` and `add` bucket consistently.
THEMES = {
    "review-severity-gate": r"\b(fix loop|criticals?_open|severity|CRITICAL)\b",
    "confidence-is-inert": r"\bconfidence\b",
    "visual-proof": r"\b(screenshot|visual|ui-probe|render)\w*\b",
    "tdd-ledger": r"\b(tdd|ac_tdd|RED commit|red-green|ledger)\b",
    "agent-null-dispatch": r"\b(agent_null|HALT_AGENT_SKIPPED|dispatch|null return)\b",
    "branch-state-truth": r"\b(branch|origin/dev|version bump|merge state|worktree)\b",
    "spec-gate-upstream": r"\b(spec.?gate|spec_quality|acceptance criteri|AC quality)\b",
    "artifact-on-disk": r"\b(findings\.json|artifact|on disk|ticket_folder)\b",
    "scope-slicing": r"\b(slice|scope|split|too large)\b",
    "qa-blind-spot": r"\b(QA|blind spot|probe|proof layer)\b",
}


def theme_for(text):
    for key, pat in THEMES.items():
        if re.search(pat, text, re.I):
            return key
    return "unthemed"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "untitled"


# Dedupe by title similarity, not by exact slug.
#
# Exact-slug matching filed the SAME ask eight separate times because each retro phrased it slightly
# differently: "Fix session resolution so retro handoffs land in a named session folder" (Jun 11),
# "Fix session resolution for retro handoffs (third strike)" (Jul 5), "Repair the empty session_id
# once, at the source" (Aug 10), "Fix the empty session_id so handoffs stop falling back" (Oct 2).
# Nine filings over four months that each looked like a first filing. Regex themes are the opposite
# error — too coarse, bucketing unrelated asks that share a common word.
STOP = set("""a an the and or of to for in on at by with from is are be was were this that it its
into as not no do does so than then when where which who whom whose if else only just must should
can could will would may might one two three new add use using make made put set get stop start""".split())


def signature(title):
    words = re.findall(r"[a-z_]{3,}", title.lower())
    return frozenset(w for w in words if w not in STOP)


def similar(a, b, threshold=0.35):
    """Jaccard over significant words.

    Best-effort only. Measured against the 334 historical filings, no threshold collapses the
    session-id ask (filed 9 times in 9 different phrasings) below 3 buckets without starting to merge
    unrelated asks. Lexical similarity cannot do this job alone, so it is the SECOND line of defence:
    the Retro reads `list` first and passes an explicit --key, which is authoritative. An agent is far
    better at semantic matching than Jaccard is. Use `merge` to fix whatever still slips through.
    """
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= threshold


def load():
    if not QUEUE.exists():
        return {"entries": []}
    return yaml.safe_load(QUEUE.read_text()) or {"entries": []}


def save(data):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    data["entries"].sort(key=lambda e: (e.get("status") != "open", -e.get("times_proposed", 0)))
    QUEUE.write_text(
        "# dark-factory improvement queue — written by tools/improvements.py, never by hand.\n"
        "# `times_proposed` is the whole point: it is how a repeated ask stops looking like a new one.\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    )


def cmd_add(a):
    data = load()
    sig = signature(a.title)
    explicit = bool(a.key)
    key = a.key or slug(a.title)
    for e in data["entries"]:
        # An explicit --key is authoritative. Otherwise match on title similarity against any title
        # this entry has ever carried, so a rephrasing lands on the existing entry.
        if explicit:
            if e["key"] != key:
                continue
        elif not any(similar(sig, signature(t)) for t in e.get("titles", [])):
            continue
        if e.get("status") != "open":
            # A landed item being re-proposed is a REGRESSION signal, not a duplicate. Say so loudly.
            e["status"] = "open"
            e["reopened"] = True
            e.setdefault("notes", []).append(
                f"REOPENED {a.run}: re-proposed after being marked {e.get('status')} "
                f"in {e.get('landed_in', '?')} — the fix did not hold.")
        e["times_proposed"] = e.get("times_proposed", 0) + 1
        e["last_proposed"] = a.date
        e.setdefault("runs", []).append(a.run)
        e.setdefault("titles", [])
        if a.title not in e["titles"]:
            e["titles"].append(a.title)
        save(data)
        print(f"bumped {key} -> times_proposed={e['times_proposed']}"
              + ("  *** REOPENED — a landed fix regressed ***" if e.get("reopened") else ""))
        return
    data["entries"].append({
        "key": key, "theme": theme_for(a.title + " " + (a.detail or "")),
        "status": "open", "times_proposed": 1,
        "first_proposed": a.date, "last_proposed": a.date,
        "titles": [a.title], "detail": a.detail or "", "runs": [a.run],
    })
    save(data)
    print(f"added {key}")


def cmd_list(a):
    data = load()
    rows = [e for e in data["entries"] if a.all or e.get("status") == "open"]
    if not rows:
        print("queue empty")
        return
    print(f"{'times':>5}  {'status':9} {'key':24} last         title")
    for e in rows:
        print(f"{e.get('times_proposed', 0):>5}  {e.get('status', '?'):9} {e['key']:24} "
              f"{str(e.get('last_proposed', '?')):12} {(e.get('titles') or ['?'])[-1][:70]}")
    stale = [e for e in rows if e.get("status") == "open" and e.get("times_proposed", 0) >= 3]
    if stale:
        print(f"\n  {len(stale)} open item(s) proposed 3+ times. Prose has not worked on these.")
        print("  The two themes that ever went quiet were both fixed with a schema field or a JS gate.")


def _close(a, status):
    data = load()
    for e in data["entries"]:
        if e["key"] == a.key:
            e["status"] = status
            e["closed_on"] = a.date
            if status == "landed":
                e["landed_in"] = a.version
            if getattr(a, "note", None) or getattr(a, "why", None):
                e.setdefault("notes", []).append(getattr(a, "note", None) or a.why)
            save(data)
            print(f"{a.key} -> {status}")
            return
    sys.exit(f"no entry with key {a.key}")



def cmd_merge(a):
    """Collapse entries the auto-dedupe split. Lexical matching will always miss some."""
    data = load()
    target = next((e for e in data["entries"] if e["key"] == a.into), None)
    if not target:
        sys.exit(f"no entry with key {a.into}")
    merged = 0
    for key in a.keys:
        if key == a.into:
            continue
        src = next((e for e in data["entries"] if e["key"] == key), None)
        if not src:
            print(f"  skip (not found): {key}")
            continue
        target["times_proposed"] += src.get("times_proposed", 0)
        target.setdefault("titles", []).extend(t for t in src.get("titles", []) if t not in target.get("titles", []))
        target.setdefault("runs", []).extend(src.get("runs", []))
        target["first_proposed"] = min(str(target.get("first_proposed", "9999")), str(src.get("first_proposed", "9999")))
        target["last_proposed"] = max(str(target.get("last_proposed", "")), str(src.get("last_proposed", "")))
        data["entries"].remove(src)
        merged += 1
    save(data)
    print(f"merged {merged} entr(ies) into {a.into} -> times_proposed={target['times_proposed']}")

def cmd_seed(a):
    """One-off backfill so the queue starts with the history it should always have had."""
    n = 0
    for f in sorted(RUNS.glob("run-*.yaml")):
        try:
            d = yaml.safe_load(f.read_text()) or {}
        except yaml.YAMLError:
            print(f"  skip unparseable {f.name}")
            continue
        for i in d.get("improvements") or []:
            title = i.get("title") if isinstance(i, dict) else str(i).split("\n")[0]
            detail = i.get("detail", "") if isinstance(i, dict) else ""
            if not title:
                continue
            ns = argparse.Namespace(key=None, title=str(title), detail=str(detail),
                                    run=d.get("run_id", f.stem), date=str(d.get("date", "?")))
            cmd_add(ns)
            n += 1
    print(f"\nseeded from {n} improvement entries")


def main():
    today = datetime.date.today().isoformat()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add"); p.set_defaults(fn=cmd_add)
    p.add_argument("--key"); p.add_argument("--title", required=True)
    p.add_argument("--detail", default=""); p.add_argument("--run", required=True)
    p.add_argument("--date", default=today)

    p = sub.add_parser("list"); p.set_defaults(fn=cmd_list)
    p.add_argument("--all", action="store_true")

    p = sub.add_parser("land"); p.set_defaults(fn=lambda a: _close(a, "landed"))
    p.add_argument("key"); p.add_argument("--version", required=True)
    p.add_argument("--note", default=""); p.add_argument("--date", default=today)

    p = sub.add_parser("reject"); p.set_defaults(fn=lambda a: _close(a, "rejected"))
    p.add_argument("key"); p.add_argument("--why", required=True); p.add_argument("--date", default=today)

    p = sub.add_parser("merge"); p.set_defaults(fn=cmd_merge)
    p.add_argument("--into", required=True); p.add_argument("keys", nargs="+")

    p = sub.add_parser("seed"); p.set_defaults(fn=cmd_seed)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
