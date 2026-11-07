#!/usr/bin/env python3
"""P1 of the skill-proposal triage: inventory the proposals and split them into batches.

Writes, inside the run directory:
  inventory.tsv            date, name, file, trigger snippet (newest first)
  batches/batch-aa.txt     one proposal file name per line, newest first, --size per batch
  brief.md                 the reviewer rubric, rendered from ../triage/brief.md
  codex/prompt-*.md        not here (run_codex.sh renders those)
  STATE.json               phase P1 done, batch list, skill counts

Usage:
  split_batches.py --run-dir DIR [--proposals-dir DIR] [--size 13] [--since YYYY-MM-DD]
                   [--budget 120] [--installed N] [--transcript-dir DIR ...]
                   [--knowledge-dir DIR ...] [--org-scope TEXT]
"""
import argparse
import os
import re
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage_common as tc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def batch_ids():
    for a in string.ascii_lowercase:
        for b in string.ascii_lowercase:
            yield f"batch-{a}{b}"


def trigger_snippet(text):
    for head in ("Trigger", "Problem", "Why"):
        m = re.search(r"^##+\s*" + head + r"[^\n]*\n(.*?)(?=^##|\Z)", text, re.S | re.M | re.I)
        if m and m.group(1).strip():
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return re.sub(r"\s+", " ", text[:300]).strip()


def list_proposals(proposals_dir, since):
    files = [f for f in os.listdir(proposals_dir)
             if tc.PROPOSAL_RE.match(f) and os.path.isfile(os.path.join(proposals_dir, f))]
    if since:
        files = [f for f in files if f[:10] >= since]
    return sorted(files, reverse=True)


def render_brief(args, run, installed):
    with open(os.path.join(HERE, "brief.md")) as fh:
        text = fh.read()
    bullets = lambda items: "\n".join(f"   - `{d}`" for d in items) or "   - (none given)"
    values = {
        "RUN": run, "PROPOSALS": args.proposals_dir, "BUDGET": str(args.budget),
        "INSTALLED": str(installed), "ORG_SCOPE": args.org_scope,
        "TRANSCRIPT_DIRS": bullets(args.transcript_dir), "KNOWLEDGE_DIRS": bullets(args.knowledge_dir),
    }
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    with open(os.path.join(run, "brief.md"), "w") as fh:
        fh.write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--proposals-dir", default=tc.DEFAULT_PROPOSALS)
    ap.add_argument("--size", type=int, default=13)
    ap.add_argument("--since", help="only proposals dated on or after YYYY-MM-DD")
    ap.add_argument("--budget", type=int, default=120, help="skill drift alarm")
    ap.add_argument("--installed", type=int, help="installed skill count (default: counted)")
    ap.add_argument("--transcript-dir", action="append", default=[])
    ap.add_argument("--knowledge-dir", action="append", default=[])
    ap.add_argument("--org-scope", default="the active org plus the personal harness")
    args = ap.parse_args()

    run = os.path.abspath(os.path.expanduser(args.run_dir))
    args.proposals_dir = os.path.abspath(os.path.expanduser(args.proposals_dir))
    for sub in ("batches", "results", "codex"):
        os.makedirs(os.path.join(run, sub), exist_ok=True)

    files = list_proposals(args.proposals_dir, args.since)
    if not files:
        sys.exit(f"no proposals found in {args.proposals_dir}")
    with open(os.path.join(run, "inventory.tsv"), "w") as inv:
        inv.write("date\tname\tfile\ttrigger\n")
        for f in files:
            with open(os.path.join(args.proposals_dir, f)) as fh:
                snippet = trigger_snippet(fh.read())[:200].replace("\t", " ")
            inv.write(f"{f[:10]}\t{tc.proposal_name(f)}\t{f}\t{snippet}\n")

    ids, batches = batch_ids(), {}
    for i in range(0, len(files), args.size):
        bid = next(ids)
        batches[bid] = files[i:i + args.size]
        with open(os.path.join(run, "batches", bid + ".txt"), "w") as fh:
            fh.write("\n".join(batches[bid]) + "\n")

    installed = args.installed if args.installed is not None else tc.count_installed_skills()
    render_brief(args, run, installed)
    state = tc.load_state(run)
    phases = state.get("phases", {})
    phases["P1"] = "done"
    tc.save_state(run, phase="P2", status="running", phases=phases, proposals_dir=args.proposals_dir,
                  since=args.since, budget=args.budget, skills_installed=installed,
                  total=len(files), batches={b: state.get("batches", {}).get(b, {}) for b in batches})
    print(f"{len(files)} proposals in {len(batches)} batches of <= {args.size}; brief at {run}/brief.md")
    for b, fs in batches.items():
        print(f"  {b}: {len(fs)}  newest {fs[0][:10]}  oldest {fs[-1][:10]}")


if __name__ == "__main__":
    main()
