#!/usr/bin/env python3
"""Benchmark hard-gate settings against a real post corpus.

Answers: at threshold N, under check-set MODE, what fraction of the corpus
would the gate BLOCK, and which checks drive the blocks? This is the instrument
for choosing (and later regressing) the aggressive gate setting. It measures
disruption; it does NOT treat a low block-rate as the goal — past posts are not
the quality bar.

Check-set modes:
  full          all 11 checks (most aggressive)
  no-contraction  full minus contraction (respects the human-voice rule)
  slop-subset   only the 6 AI-slop checks: marketing, hedge, phrasal,
                banned, nominalization (the true AI-drift target)

Run: python3 gate_benchmark.py '<glob>' [...]
"""
import glob as globlib
import os
import sys

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "..", "tools"))
sys.path.insert(0, TOOLS)
import ste_lint  # noqa: E402

ALLOWLIST = ste_lint.load_allowlist(ste_lint.DEFAULT_ALLOWLIST)

SLOP_CHECKS = {"marketing_adjective", "modal_hedge", "phrasal_verb",
               "banned_word", "nominalization"}
MODES = {
    "full": lambda k: True,
    "no-contraction": lambda k: k != "contraction",
    "slop-subset": lambda k: k in SLOP_CHECKS,
}
THRESHOLDS = [0.5, 1, 2, 3, 4, 5, 6, 8]


def subset_score(r, keep):
    total = sum(v for k, v in r["violations"].items() if keep(k))
    wc = r["words"] or 1
    return round(total * 100.0 / wc, 2)


def main(argv):
    if not argv:
        print("usage: gate_benchmark.py '<glob>' [...]", file=sys.stderr)
        return 2
    paths = []
    for pat in argv:
        paths.extend(globlib.glob(pat, recursive=True))
    paths = sorted(set(p for p in paths if os.path.isfile(p)))

    results = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        r = ste_lint.lint(text, ALLOWLIST)
        if r["words"] >= 15:
            results.append(r)
    n = len(results)
    if not n:
        print("no scorable files", file=sys.stderr)
        return 2

    print(f"corpus: {n} posts (>=15 words)\n")
    print("block-rate = % of corpus that would be BLOCKED at threshold N\n")
    header = "mode".ljust(16) + "".join(f"N>{t}".rjust(8) for t in THRESHOLDS)
    print(header)
    print("-" * len(header))
    for mode, keep in MODES.items():
        scores = [subset_score(r, keep) for r in results]
        row = mode.ljust(16)
        for t in THRESHOLDS:
            blocked = sum(1 for s in scores if s > t)
            row += f"{round(blocked * 100.0 / n):>7}%"
        print(row)

    print("\nslop-subset detail: posts with ANY AI-slop hit")
    any_slop = sum(1 for r in results if subset_score(r, MODES["slop-subset"]) > 0)
    print(f"  {any_slop}/{n} posts ({round(any_slop * 100.0 / n)}%) contain "
          f"a marketing/hedge/phrasal/banned/nominalization hit")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
