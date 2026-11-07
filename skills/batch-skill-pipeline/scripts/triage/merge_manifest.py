#!/usr/bin/env python3
"""P7 of the skill-proposal triage: merge the apply agents' eval suite blocks into the manifest.

Apply agents never edit evals/manifest.yaml. They write YAML suite blocks (same shape as the
manifest entries, `~/.claude-shared-config/...` runner paths, no last_green) to
<run>/apply/manifest-additions/<package>.yaml. This script inserts each new block before the
top-level `exclusions:` key, skips targets that already exist, then runs every added Layer A
runner with the live harness path mapped to the worktree, and writes a PASS/FAIL table.

Usage: merge_manifest.py --run-dir DIR --worktree DIR [--additions DIR] [--live-root PATH]
                         [--no-run] [--dry-run]
"""
import argparse
import datetime
import glob
import os
import re
import subprocess
import sys


def parse_blocks(src):
    for b in re.split(r"(?m)^(?=\s*-\s*target:)", src):
        m = re.search(r"-\s*target:\s*(\S+)", b)
        if not m:
            continue
        lines = [ln for ln in b.rstrip().splitlines() if not ln.lstrip().startswith("#")]
        indent = len(lines[0]) - len(lines[0].lstrip())
        body = "\n".join(("  " + ln[indent:]) if ln.strip() else ln for ln in lines)
        yield m.group(1), body


def run_suite(cmd, live_root, worktree):
    cmd = cmd.replace(live_root, worktree)
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600,
                           executable="/bin/bash", stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    tail = ((p.stdout + p.stderr).strip().splitlines() or [""])[-1][:110]
    return ("PASS" if p.returncode == 0 else f"FAIL({p.returncode})"), tail


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--worktree", required=True, help="harness repo worktree that holds evals/manifest.yaml")
    ap.add_argument("--additions", help="default: <run>/apply/manifest-additions")
    ap.add_argument("--live-root", default="~/.claude-shared-config")
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the blocks, do not write")
    args = ap.parse_args()
    run = os.path.abspath(os.path.expanduser(args.run_dir))
    wt = os.path.abspath(os.path.expanduser(args.worktree))
    manifest = os.path.join(wt, "evals", "manifest.yaml")
    text = open(manifest).read()
    if "\nexclusions:" not in text:
        sys.exit("manifest has no top-level exclusions: key")
    existing = set(re.findall(r"^\s*-\s*target:\s*(\S+)", text, re.M))

    blocks = []
    for f in sorted(glob.glob(os.path.join(args.additions or os.path.join(run, "apply", "manifest-additions"), "*.yaml"))):
        for tgt, body in parse_blocks(open(f).read()):
            if tgt in existing:
                print("skip existing", tgt)
                continue
            blocks.append((tgt, body))
            existing.add(tgt)
    if not blocks:
        print("no new suites")
        return
    if args.dry_run:
        print("\n\n".join(b for _, b in blocks))
        return
    header = f"\n  # --- added {datetime.date.today()} by the skill-proposal triage apply ---\n"
    idx = text.index("\nexclusions:")
    text = text[:idx].rstrip("\n") + "\n" + header + "\n\n".join(b for _, b in blocks) + "\n\n" + text[idx + 1:]
    with open(manifest, "w") as fh:
        fh.write(text)
    print(f"added {len(blocks)} suites to {manifest}")
    if args.no_run:
        return

    rows = []
    for tgt, body in blocks:
        m = re.search(r"runner:\s*(.+)", body)
        if not re.search(r"layer:\s*A\b", body) or not m:
            rows.append((tgt, "not run (layer B)", ""))
            continue
        rows.append((tgt, *run_suite(m.group(1).strip().strip('"'), args.live_root, wt)))
    out = os.path.join(run, "apply", "eval-run.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        fh.write("| Suite | Result | Last line |\n|---|---|---|\n")
        fh.writelines(f"| {a} | {b} | {c} |\n" for a, b, c in rows)
    for r in rows:
        print(" | ".join(r))
    print(f"table: {out}")
    if any(not r[1].startswith(("PASS", "not run")) for r in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
