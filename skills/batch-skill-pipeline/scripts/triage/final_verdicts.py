#!/usr/bin/env python3
"""P5 of the skill-proposal triage: merge both passes and the human decisions into one verdict.

Rules:
  - Codex verdict and invocation win on conflict (the second pass attacked the first).
  - When the Codex output for a proposal is missing or unparsable, the Claude verdict stands.
  - final_score = mean(Claude score, Codex score); the Claude score alone when Codex is missing.
  - decisions.json (exported from triage.html) applies last: "override" replaces the verdict,
    "hold" sets HOLD (the apply phase skips it), "accept" keeps the merged verdict.

Writes <run>/final-verdicts.json: {file: {name, verdict, invocation, final_score, source,
claude_verdict, codex_verdict, agree, note}}.

Usage: final_verdicts.py --run-dir DIR [--decisions FILE] [--out FILE]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage_common as tc  # noqa: E402


def load_decisions(path):
    data = tc.read_json(path, {}) or {}
    if isinstance(data, dict) and isinstance(data.get("decisions"), dict):
        data = data["decisions"]
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def merge(claude, codex, decisions):
    out = {}
    for fn in sorted(set(claude) | set(codex), reverse=True):
        c, x = claude.get(fn, {}), codex.get(fn, {})
        if not c and not x:
            continue
        cv, xv = c.get("verdict"), x.get("codex_verdict")
        scores = [s for s in (c.get("score"), x.get("codex_score")) if isinstance(s, (int, float))]
        row = {
            "name": c.get("name") or tc.proposal_name(fn),
            "verdict": xv or cv or "PENDING",
            "invocation": x.get("codex_invocation") or c.get("invocation") or "manual",
            "final_score": round(sum(scores) / len(scores)) if scores else None,
            "source": "codex" if xv else "claude",
            "claude_verdict": cv,
            "codex_verdict": xv,
            "agree": (tc.verdict_class(cv) == tc.verdict_class(xv)) if (cv and xv) else None,
        }
        d = decisions.get(fn)
        if d:
            action = (d.get("action") or "accept").lower()
            if action == "override" and d.get("verdict"):
                row.update(verdict=d["verdict"], source="human")
            elif action == "hold":
                row.update(verdict="HOLD", source="human")
            if d.get("note"):
                row["note"] = d["note"]
        out[fn] = row
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--decisions", help="default: <run>/decisions.json when present")
    ap.add_argument("--out")
    args = ap.parse_args()
    run = os.path.abspath(os.path.expanduser(args.run_dir))
    problems = []
    claude, codex = tc.load_claude(run), tc.load_codex(run, problems)
    dpath = args.decisions or os.path.join(run, "decisions.json")
    decisions = load_decisions(dpath) if os.path.exists(dpath) else {}
    final = merge(claude, codex, decisions)
    out = args.out or os.path.join(run, "final-verdicts.json")
    tc.write_json(out, final)

    expected = {f for fs in tc.batch_files(run).values() for f in fs}
    no_claude = sorted(expected - set(claude))
    no_codex = sorted(set(claude) - set(codex))
    counts = {}
    for r in final.values():
        k = tc.verdict_class(r["verdict"])
        counts[k] = counts.get(k, 0) + 1
    print(f"{len(final)} verdicts -> {out}")
    print("  " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"  codex wins {sum(1 for r in final.values() if r['agree'] is False)} conflicts; "
          f"claude-only {len(no_codex)}; human decisions {len(decisions)}")
    for p in problems:
        print("  WARN " + p)
    if no_claude:
        print(f"  WARN no Claude result for {len(no_claude)}: {', '.join(no_claude[:5])}")


if __name__ == "__main__":
    main()
