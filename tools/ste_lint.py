#!/usr/bin/env python3
"""ste-lint — deterministic anti-slop linter (ASD-STE100 mechanical subset).

Scores text by violations per 100 words. Lower is cleaner. Eleven checks cover
the six AI-slop patterns (synonym rotation is handled behaviorally, not here):
run-ons, hedging, frozen verbs / nominalizations, marketing adjectives, phrasal
verbs, plus passive voice, contractions, semicolons, and progressive main verbs.

Rule set ported from woosal1337/blog ep01 "the cure for ai slop" (ste-lint.py),
extended with a software-term allowlist, an em-dash soft marker, a threshold
exit code, and a pass-marker for the external-post gate.

Usage:
    ste-lint.py [FILE ...]                 # lint files (or stdin), print report
    cat draft.md | ste-lint.py             # lint stdin
    ste-lint.py --json draft.md            # machine-readable report
    ste-lint.py --threshold 6 draft.md     # exit 1 if score > 6 per 100w
    ste-lint.py --threshold 6 --marker /tmp/.ste-lint-pass draft.md
    ste-lint.py --allowlist path.txt draft.md

Exit codes: 0 = clean (or advisory, no threshold). 1 = score over threshold.
2 = usage / IO error.
"""
import argparse
import glob as globlib
import json
import os
import re
import sys
import time

DEFAULT_ALLOWLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "ste-software-allowlist.txt")

# The six AI-slop patterns. The hard gate defaults to this subset because these
# checks target machine-generated drift, not a human's grammar or voice.
SLOP_CHECKS = {"marketing_adjective", "modal_hedge", "phrasal_verb",
               "banned_word", "nominalization"}
GATE_MODES = {
    "full": lambda k: True,
    "no-contraction": lambda k: k != "contraction",
    "slop-subset": lambda k: k in SLOP_CHECKS,
}

BANNED = [
    "begin", "begins", "commence", "commences", "initiate", "initiates", "originate",
    "utilize", "utilizes", "utilizing", "leverage", "leverages", "leveraging",
    "facilitate", "facilitates", "ensure", "ensures", "ensuring", "prior to",
    "subsequent to", "obtain", "obtains", "acquire", "acquires", "demonstrate",
    "demonstrates", "additionally", "furthermore", "moreover", "comprehensive",
    "comprehensively", "utilization", "aforementioned", "henceforth", "therein",
    "whilst", "amongst", "numerous", "myriad", "plethora", "in order to",
    "a variety of", "in the event that", "due to the fact that",
]

MARKETING = [
    "seamless", "seamlessly", "robust", "powerful", "cutting-edge", "effortless",
    "effortlessly", "world-class", "next-generation", "revolutionary", "blazing",
    "lightning-fast", "elegant", "delightful", "turnkey", "best-in-class",
    "state-of-the-art", "game-changing", "first-class", "battle-tested",
    "enterprise-grade", "supercharge", "unlock", "unleash", "empower", "empowers",
]

PHRASAL = [
    "spin up", "spin down", "reach out", "dive into", "dives into", "diving into",
    "kick off", "kicks off", "roll out", "rolls out", "tear down", "ramp up",
    "circle back", "drill down", "spun up", "reaching out",
]

MODAL_HEDGE = [
    "it is important to note", "it should be noted", "it is worth noting",
    "please note that", "as mentioned", "as noted above", "it may potentially",
    "this may potentially",
]

BE = r"(?:am|is|are|was|were|be|been|being)"
PP_IRREG = (r"(?:done|made|sent|read|built|kept|held|set|put|run|written|shown|"
            r"given|taken|found|got|gotten|seen|known|thrown|drawn)")
PASSIVE_RE = re.compile(rf"\b{BE}\s+(?:\w+ed|{PP_IRREG})\b", re.IGNORECASE)
ING_MAIN_RE = re.compile(rf"\b{BE}\s+(\w+ing)\b", re.IGNORECASE)
CONTRACTION_RE = re.compile(r"\b\w+[’'](?:t|re|ve|ll|d|s|m)\b", re.IGNORECASE)
NOMINAL_VERB_RE = re.compile(
    r"\b(?:perform(?:s|ed)?|conduct(?:s|ed)?|provide(?:s|d)?|carry out|"
    r"carries out|make use of|makes use of)\b", re.IGNORECASE)
NOMINAL_OF_RE = re.compile(r"\b(\w{4,}(?:tion|ment|ance|ence))\s+of\b", re.IGNORECASE)
EM_DASH_RE = re.compile(r"[—–]|--")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
SENT_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")


def load_allowlist(path):
    terms = set()
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip().lower()
                if line:
                    terms.add(line)
    return terms


def phrase_re(phrase):
    return re.compile(r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b",
                      re.IGNORECASE)


BANNED_RES = [(w, phrase_re(w)) for w in BANNED]
MARKETING_RES = [(w, phrase_re(w)) for w in MARKETING]
PHRASAL_RES = [(w, phrase_re(w)) for w in PHRASAL]
HEDGE_RES = [(w, phrase_re(w)) for w in MODAL_HEDGE]


def words(text):
    return WORD_RE.findall(text)


def sentences(text):
    parts = [s.strip() for s in SENT_SPLIT_RE.split(text)]
    return [s for s in parts if s]


def paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def _list_hits(text, res, allowlist=None):
    hits = []
    for term, rx in res:
        if allowlist and term in allowlist:
            continue
        hits.extend(m.group(0) for m in rx.finditer(text))
    return hits


def lint(text, allowlist=None):
    allowlist = allowlist or set()
    checks = {}
    longest = 0
    long_sentences = 0
    for s in sentences(text):
        n = len(words(s))
        longest = max(longest, n)
        if n > 20:
            long_sentences += 1
    checks["long_sentence(>20w)"] = long_sentences
    checks["long_paragraph(>6s)"] = sum(
        1 for p in paragraphs(text) if len(sentences(p)) > 6)
    checks["semicolon"] = text.count(";")
    checks["contraction"] = len(CONTRACTION_RE.findall(text))
    checks["passive_voice"] = len(PASSIVE_RE.findall(text))
    checks["ing_main_verb"] = len(ING_MAIN_RE.findall(text))
    nominal = len(NOMINAL_VERB_RE.findall(text))
    nominal += sum(1 for m in NOMINAL_OF_RE.finditer(text)
                   if m.group(1).lower() not in allowlist)
    checks["nominalization"] = nominal
    checks["phrasal_verb"] = len(_list_hits(text, PHRASAL_RES))
    checks["banned_word"] = len(_list_hits(text, BANNED_RES, allowlist))
    checks["marketing_adjective"] = len(_list_hits(text, MARKETING_RES))
    checks["modal_hedge"] = len(_list_hits(text, HEDGE_RES))

    total = sum(checks.values())
    wc = len(words(text)) or 1
    return {
        "words": len(words(text)),
        "violations": checks,
        "total": total,
        "score_per_100w": round(total * 100.0 / wc, 2),
        "em_dash_soft_marker": len(EM_DASH_RE.findall(text)),
        "longest_sentence_words": longest,
    }


def gate_score(r, mode):
    keep = GATE_MODES[mode]
    total = sum(v for k, v in r["violations"].items() if keep(k))
    wc = r["words"] or 1
    return round(total * 100.0 / wc, 2)


def format_report(name, r):
    lines = [f"{name}: {r['words']} words · {r['total']} violations · "
             f"{r['score_per_100w']} per 100w"]
    for check, n in r["violations"].items():
        if n:
            lines.append(f"    {n:>3}  {check}")
    if r["em_dash_soft_marker"]:
        lines.append(f"    {r['em_dash_soft_marker']:>3}  em_dash (soft marker, not scored)")
    lines.append(f"    longest sentence: {r['longest_sentence_words']} words")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Anti-slop STE linter.")
    ap.add_argument("files", nargs="*", help="files to lint (default: stdin)")
    ap.add_argument("--allowlist", default=DEFAULT_ALLOWLIST)
    ap.add_argument("--threshold", type=float, default=None,
                    help="fail (exit 1) if any file scores above this per-100w value")
    ap.add_argument("--marker", default=None,
                    help="write this marker file when all files pass the threshold")
    ap.add_argument("--gate-mode", choices=sorted(GATE_MODES), default="full",
                    help="which checks count toward the threshold (default: full). "
                         "slop-subset gates only the six AI-slop patterns.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    allowlist = load_allowlist(args.allowlist)

    inputs = []
    if args.files:
        expanded = []
        for pat in args.files:
            expanded.extend(globlib.glob(pat) or [pat])
        for path in expanded:
            try:
                with open(path, encoding="utf-8") as fh:
                    inputs.append((path, fh.read()))
            except OSError as exc:
                print(f"ste-lint: cannot read {path}: {exc}", file=sys.stderr)
                return 2
    else:
        inputs.append(("<stdin>", sys.stdin.read()))

    results = [(name, lint(text, allowlist)) for name, text in inputs]
    for _, r in results:
        r["gate_mode"] = args.gate_mode
        r["gate_score"] = gate_score(r, args.gate_mode)
    worst = max((r["gate_score"] for _, r in results), default=0.0)

    if args.json:
        print(json.dumps({"results": [{"file": n, **r} for n, r in results],
                          "worst_score": worst,
                          "gate_mode": args.gate_mode,
                          "threshold": args.threshold}, indent=2))
    else:
        for name, r in results:
            print(format_report(name, r))
        if args.threshold is not None:
            print(f"\ngate-mode {args.gate_mode} · worst gated score {worst} "
                  f"per 100w · threshold {args.threshold}")

    passed = args.threshold is None or worst <= args.threshold
    if args.marker and passed:
        try:
            with open(args.marker, "w", encoding="utf-8") as fh:
                fh.write(f"{int(time.time())} ste-lint pass mode={args.gate_mode} "
                         f"worst={worst} threshold={args.threshold}\n")
        except OSError as exc:
            print(f"ste-lint: cannot write marker {args.marker}: {exc}", file=sys.stderr)
            return 2

    if args.threshold is not None and worst > args.threshold:
        if not args.json:
            print("FAIL: score over threshold", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
