#!/usr/bin/env python3
"""P6 of the skill-proposal triage: archive the ARCHIVE-verdict proposals.

Dry run by default: prints what would move and changes nothing.
With --apply:
  1. writes a tarball backup of the proposals directory (the .triage run dirs excluded),
  2. moves each proposal whose FINAL verdict is ARCHIVE into <proposals>/archive/,
  3. appends one audit section to <proposals>/archive/REJECTION-LOG.md.
HOLD, overridden and non-ARCHIVE proposals never move. Run final_verdicts.py first.

Usage: archive.py --run-dir DIR [--proposals-dir DIR] [--backup-dir DIR] [--apply]
"""
import argparse
import datetime
import os
import shutil
import sys
import tarfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage_common as tc  # noqa: E402


def cell(text):
    return " ".join(str(text or "").replace("|", "/").split())


def backup(proposals, backup_dir, stamp):
    os.makedirs(backup_dir, exist_ok=True)
    path = os.path.join(backup_dir, f"skill-proposals-{stamp}.tgz")
    skip = lambda ti: None if "/.triage" in ti.name or ti.name.endswith(".triage") else ti
    with tarfile.open(path, "w:gz") as t:
        t.add(proposals, arcname="skill-proposals", filter=skip)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--proposals-dir")
    ap.add_argument("--backup-dir", help="default: <run>/backups")
    ap.add_argument("--apply", action="store_true", help="move files (default is a dry run)")
    args = ap.parse_args()
    run = os.path.abspath(os.path.expanduser(args.run_dir))
    state = tc.load_state(run)
    proposals = os.path.abspath(os.path.expanduser(
        args.proposals_dir or state.get("proposals_dir") or tc.DEFAULT_PROPOSALS))
    final = tc.read_json(os.path.join(run, "final-verdicts.json"))
    if not isinstance(final, dict):
        sys.exit("final-verdicts.json missing: run final_verdicts.py first")
    claude, codex = tc.load_claude(run), tc.load_codex(run)

    todo = []
    for fn, v in sorted(final.items()):
        if tc.verdict_class(v.get("verdict")) != "ARCHIVE":
            continue
        if not os.path.exists(os.path.join(proposals, fn)):
            print(f"  skip (not in inbox): {fn}")
            continue
        todo.append(fn)
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"{mode}: {len(todo)} proposal(s) to archive from {proposals}")
    for fn in todo:
        print(f"  {fn}")
    if not args.apply or not todo:
        return

    now = datetime.datetime.now()
    tgz = backup(proposals, args.backup_dir or os.path.join(run, "backups"), now.strftime("%Y%m%d-%H%M%S"))
    arch = os.path.join(proposals, "archive")
    os.makedirs(arch, exist_ok=True)
    rows = []
    for fn in todo:
        shutil.move(os.path.join(proposals, fn), os.path.join(arch, fn))
        c, x, v = claude.get(fn, {}), codex.get(fn, {}), final[fn]
        why = v.get("note") or x.get("summary") or c.get("rationale", "")
        over = ", ".join(c.get("overlap", [])[:3])
        rows.append(f"| {fn[:-3]} | {cell(over) or 'none'} | {cell(why)} |")

    log = os.path.join(arch, "REJECTION-LOG.md")
    text = open(log).read() if os.path.exists(log) else "# Skill proposal rejection log\n"
    if not text.endswith("\n"):
        text += "\n"
    text += (
        f"\n## Audit {now:%Y-%m-%d}: adversarial triage (Claude first pass, Codex second pass)\n\n"
        f"Context: {state.get('skills_installed', '?')} skills installed, drift alarm at "
        f"{state.get('budget', 120)}. Each proposal was checked for overlap and for recurrence in "
        f"transcript history, then re-attacked by Codex. Codex verdict final on conflict; human "
        f"decisions applied. Run: {run} (report {run}/triage.html). Backup: {tgz}\n\n"
        "| Proposal | Covered by | Why archived |\n|---|---|---|\n" + "\n".join(rows) + "\n"
    )
    with open(log, "w") as fh:
        fh.write(text)
    print(f"archived {len(rows)}; backup {tgz}; log {log}")


if __name__ == "__main__":
    main()
