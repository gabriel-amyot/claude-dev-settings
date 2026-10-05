#!/usr/bin/env python3
"""Mine the dark-factory run telemetry in runs/*.yaml.

The factory's auto-improve loop claims each run makes the next one better. That claim is
testable: if it holds, an improvement proposed by a retro should stop being proposed once it
lands. An improvement re-proposed across many runs over many weeks is the loop FAILING to
close, and it is the single most useful thing this telemetry can tell us.

Usage:
    python3 tools/mine-telemetry.py            # full report
    python3 tools/mine-telemetry.py --since 2026-08-01
"""
import argparse
import pathlib
import re
import sys
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml: python3 -m pip install --user pyyaml")

RUNS = pathlib.Path(__file__).resolve().parent.parent / "runs"

# Recurring-theme buckets, matched against improvement TITLES only.
#
# An earlier version matched titles+details+red_flags with loose keywords and reported that 52 of
# 52 runs raised the "tdd-ledger" theme. That was the regex matching the word "RED" in ordinary
# prose, not a real finding. A theme that matches every single run is measuring nothing. Titles
# are the retro's own one-line statement of the ask, so they carry far less incidental vocabulary.
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

# A retro that says "this is a repeat" is the strongest available evidence that the loop is not
# closing — it is the system reporting its own failure, not an analyst inferring one.
REPEAT_RX = re.compile(
    r"verbatim repeat|already (filed|written|proposed)|prior retro|previous retro|"
    r"re-?proposed|same improvement|filed by the .* retro|still (open|not|has)|"
    r"(two|three|four|five|\d+) (runs|retros), ",
    re.I,
)


def load():
    out = []
    for f in sorted(RUNS.glob("run-*.yaml")):
        try:
            d = yaml.safe_load(f.read_text()) or {}
        except yaml.YAMLError as e:
            print(f"  !! unparseable {f.name}: {e}", file=sys.stderr)
            continue
        d["_file"] = f.name
        out.append(d)
    return out


def flatten(v):
    """Improvements/red_flags appear as strings, lists, or lists of dicts across runs."""
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return [" ".join(str(x) for x in v.values())]
    if isinstance(v, list):
        out = []
        for i in v:
            out.extend(flatten(i))
        return out
    return [str(v)]


def titles(run):
    """Just the one-line asks, which is where the signal lives."""
    out = []
    for i in run.get("improvements") or []:
        if isinstance(i, dict):
            t = i.get("title")
            if t:
                out.append(str(t))
        elif isinstance(i, str):
            out.append(i.split("\n")[0])
    return out


def details(run):
    out = []
    for i in run.get("improvements") or []:
        if isinstance(i, dict) and i.get("detail"):
            out.append(str(i["detail"]))
    return out


def score_of(run, key):
    s = run.get("scores")
    if isinstance(s, dict):
        val = s.get(key)
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            m = re.search(r"\d+", val)
            if m:
                return int(m.group())
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None, help="YYYY-MM-DD")
    args = ap.parse_args()

    runs = load()
    if args.since:
        runs = [r for r in runs if str(r.get("date", "")) >= args.since]
    if not runs:
        sys.exit("no runs matched")

    print(f"# dark-factory telemetry — {len(runs)} runs "
          f"({runs[0].get('date')} → {runs[-1].get('date')})\n")

    print("## Terminal states")
    for st, n in Counter(str(r.get("terminal_status", "?")) for r in runs).most_common():
        print(f"  {n:3}  {st}")

    print("\n## Scores over time (task_confidence / factory_fitness)")
    by_month = defaultdict(list)
    for r in runs:
        by_month[str(r.get("date", "?"))[:7]].append(r)
    for month in sorted(by_month):
        rs = by_month[month]
        tc = [v for v in (score_of(r, "task_confidence") for r in rs) if v is not None]
        ff = [v for v in (score_of(r, "factory_fitness") for r in rs) if v is not None]
        avg = lambda xs: f"{sum(xs)/len(xs):5.1f}" if xs else "    -"
        print(f"  {month}  n={len(rs):2}  task {avg(tc)}   fitness {avg(ff)}")

    scored = [r for r in runs if titles(r)]
    print(f"\n## Recurring improvement themes  (titles only, {len(scored)} runs with improvements)")
    print("  'runs' = how many runs raised the theme. Re-raised after a fix landed = not absorbed.\n")
    rows = []
    for theme, pat in THEMES.items():
        rx = re.compile(pat, re.I)
        hits = [r for r in scored if any(rx.search(t) for t in titles(r))]
        if hits:
            dates = sorted(str(h.get("date", "?")) for h in hits)
            rows.append((len(hits), theme, dates[0], dates[-1]))
    for n, theme, first, last in sorted(rows, reverse=True):
        pct = 100 * n / len(scored)
        flag = "  <-- STILL OPEN" if last >= "2026-09-01" and n >= 3 else ""
        print(f"  {n:3} runs ({pct:4.0f}%)  {theme:22}  {first} -> {last}{flag}")

    print("\n## Retros that declare their OWN finding is a repeat")
    print("  The system reporting the loop is not closing, in its own words.\n")
    rep = 0
    for r in scored:
        for i in r.get("improvements") or []:
            if not isinstance(i, dict):
                continue
            d = str(i.get("detail", ""))
            if REPEAT_RX.search(d):
                rep += 1
                m = REPEAT_RX.search(d)
                frag = d[max(0, m.start() - 60):m.end() + 80].replace("\n", " ")
                print(f"  {r.get('date')}  {str(i.get('title'))[:62]}")
                print(f"              ...{frag.strip()}...")
    print(f"\n  {rep} self-declared repeats across {len(scored)} scored runs")

    print("\n## Most recent run's asks")
    last = runs[-1]
    print(f"  {last['_file']}  [{last.get('terminal_status')}]")
    for t in titles(last):
        print(f"    - {t.strip()[:150]}")


if __name__ == "__main__":
    main()
