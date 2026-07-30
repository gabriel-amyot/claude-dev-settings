#!/usr/bin/env python3
"""STE linter eval suite.

Three assertions, all deterministic:

1. FIRE   — each slop fixture triggers the checks it is meant to trigger.
2. CLEAN  — the software corpus (legitimate engineering prose) scores ~0.
             This is the false-positive guard that gates the hard-gate flip.
3. DELTA  — for each (slop -> clean) pair the score drops. The mean drop is the
             improvement metric, comparable to the upstream -74% result.

Exit 0 if every FIRE and CLEAN assertion holds, 1 otherwise. The DELTA metric is
reported regardless (it is a measurement, not a pass/fail).

Run: python3 run_ste_evals.py
"""
import os
import sys

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "..", "tools"))
sys.path.insert(0, TOOLS)
import ste_lint  # noqa: E402

ALLOWLIST = ste_lint.load_allowlist(ste_lint.DEFAULT_ALLOWLIST)


def score(text):
    return ste_lint.lint(text, ALLOWLIST)


# (label, text, checks that MUST fire) — the slop half of each pair.
SLOP = [
    ("hedging",
     "It is important to note that this may potentially help the team.",
     ["modal_hedge"]),
    ("phrasal",
     "We will spin up the service and then reach out to the vendor.",
     ["phrasal_verb"]),
    ("marketing",
     "This is a seamless, robust, cutting-edge, best-in-class platform.",
     ["marketing_adjective"]),
    ("frozen_verb",
     "The team will perform an analysis of the data and conduct a review of it.",
     ["nominalization"]),
    ("banned",
     "We utilize the tool in order to leverage a comprehensive result.",
     ["banned_word"]),
    ("run_on",
     "We read the file and then we parse the rows and then we write the output "
     "and then we send the report and then we notify the owner and then we log "
     "the run and then we exit the job cleanly for the night.",
     ["long_sentence(>20w)"]),
    ("passive",
     "The file was read by the parser and the report was sent to the owner.",
     ["passive_voice"]),
    ("semicolon",
     "The parser reads the file; the writer emits the rows.",
     ["semicolon"]),
]

# Its clean rewrite — same meaning, slop removed.
CLEAN = {
    "hedging": "This helps the team.",
    "phrasal": "We start the service, then contact the vendor.",
    "marketing": "This platform serves ads and reports foot traffic.",
    "frozen_verb": "The team analyzes the data and reviews it.",
    "banned": "We use the tool to get a full result.",
    "run_on": "We read the file and parse the rows. We write the output and "
              "send the report. We notify the owner, log the run, and exit.",
    "passive": "The parser reads the file. It sends the report to the owner.",
    "semicolon": "The parser reads the file. The writer emits the rows.",
}

# Legitimate engineering prose — must score ~0 (false-positive guard).
SOFTWARE_CORPUS = [
    "The adapter reads the schema and writes one row for each store.",
    "The deployment of the service starts the job. Configuration lives in the profile.",
    "The validation of the payload runs before the transformation of each record.",
    "The BigQuery adapter selects the column from the view and returns the count.",
    "Authentication uses Auth0. The session token carries the advertiser id.",
    "The migration of the schema adds one column. The rollback drops it.",
    "The pipeline runs aggregation, then geolocation, then attribution of visits.",
]
SOFTWARE_FP_CEILING = 2.0  # per 100 words


def main():
    failures = []

    # 1. FIRE
    for label, text, must_fire in SLOP:
        r = score(text)
        for check in must_fire:
            if r["violations"].get(check, 0) < 1:
                failures.append(
                    f"FIRE {label}: expected {check} to fire, got "
                    f"{r['violations'].get(check, 0)} (score {r['score_per_100w']})")

    # 2. CLEAN (false-positive guard on the software corpus)
    for i, text in enumerate(SOFTWARE_CORPUS):
        r = score(text)
        if r["score_per_100w"] > SOFTWARE_FP_CEILING:
            failures.append(
                f"CLEAN corpus[{i}]: {r['score_per_100w']} per 100w over "
                f"{SOFTWARE_FP_CEILING} ceiling — allowlist gap. Offenders: "
                f"{ {k: v for k, v in r['violations'].items() if v} }")

    # 3. DELTA (measurement)
    deltas, drops = [], []
    print("=== lint-delta (slop -> clean) ===")
    for label, text, _ in SLOP:
        before = score(text)["score_per_100w"]
        after = score(CLEAN[label])["score_per_100w"]
        pct = 100.0 if before == 0 else round((before - after) * 100.0 / before, 1)
        deltas.append(before - after)
        drops.append(pct)
        print(f"  {label:<12} {before:>6} -> {after:>5}   ({pct:>5}% cleaner)")
        if after >= before:
            failures.append(f"DELTA {label}: score did not drop ({before} -> {after})")
    mean_drop = round(sum(drops) / len(drops), 1)
    corpus_scores = [score(t)["score_per_100w"] for t in SOFTWARE_CORPUS]
    print(f"\nmean improvement: {mean_drop}% cleaner across {len(SLOP)} pairs")
    print(f"software corpus mean score: "
          f"{round(sum(corpus_scores) / len(corpus_scores), 2)} per 100w "
          f"(ceiling {SOFTWARE_FP_CEILING})")

    print("\n=== result ===")
    if failures:
        for f in failures:
            print("FAIL:", f)
        print(f"\n{len(failures)} failure(s)")
        return 1
    print(f"all {len(SLOP)} FIRE + {len(SOFTWARE_CORPUS)} CLEAN assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
