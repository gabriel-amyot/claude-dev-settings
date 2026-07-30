#!/usr/bin/env python3
"""Calibrate the STE hard-gate threshold from a corpus of real posts.

Lints every file in the given globs, prints the score distribution, and
suggests a threshold N. The gate should sit above the bulk of Gabriel's own
approved posts so it blocks slop, not his normal voice.

Emits only scores and aggregate stats — never the post content — so a corpus
of external posts can be summarized without loading it into context.

Run: python3 calibrate.py '<glob>' ['<glob>' ...]
"""
import glob as globlib
import os
import sys

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "..", "tools"))
sys.path.insert(0, TOOLS)
import ste_lint  # noqa: E402

ALLOWLIST = ste_lint.load_allowlist(ste_lint.DEFAULT_ALLOWLIST)


def pct(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo), 2)


def main(argv):
    if not argv:
        print("usage: calibrate.py '<glob>' [...]", file=sys.stderr)
        return 2
    paths = []
    for pat in argv:
        paths.extend(globlib.glob(pat, recursive=True))
    paths = sorted(set(p for p in paths if os.path.isfile(p)))
    if not paths:
        print("no files matched", file=sys.stderr)
        return 2

    rows = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        r = ste_lint.lint(text, ALLOWLIST)
        if r["words"] < 15:
            continue  # too short to score meaningfully
        rows.append((r["score_per_100w"], r["words"], os.path.basename(p), r))

    rows.sort()
    scores = [s for s, *_ in rows]
    print(f"corpus: {len(rows)} files (>=15 words)\n")
    print(f"{'score':>7}  {'words':>5}  file")
    for s, w, name, _ in rows:
        print(f"{s:>7}  {w:>5}  {name}")

    print("\n=== distribution (score per 100 words) ===")
    for label, p in [("min", 0), ("p50", 50), ("p75", 75),
                     ("p90", 90), ("p95", 95), ("max", 100)]:
        print(f"  {label:>4}: {pct(scores, p)}")
    print(f"  mean: {round(sum(scores) / len(scores), 2)}")

    p75, p90 = pct(scores, 75), pct(scores, 90)
    print("\n=== top offending checks across corpus ===")
    agg = {}
    for _, _, _, r in rows:
        for k, v in r["violations"].items():
            agg[k] = agg.get(k, 0) + v
    for k, v in sorted(agg.items(), key=lambda kv: -kv[1]):
        if v:
            print(f"  {v:>4}  {k}")

    print("\n=== threshold recommendation ===")
    print(f"  p90 = {p90}  -> gate at ceil(p90)+margin lets ~90% of current "
          f"posts pass untouched")
    print(f"  suggested N (advisory->gate): {max(p90, p75 + 1)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
