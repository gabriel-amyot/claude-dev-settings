#!/usr/bin/env python3
"""claude-md-gate.py — Gate 7 helper: lint a repo CLAUDE.md only for what this MR changes.

Runs the repo CLAUDE.md schema linter (schema v1, rule IDs S*, C*, P*, B*, M*) on the base
ref and on the head ref, then reports the violations the MR introduces. Pre-existing
violations are listed as a count only. They are not this MR's job.

The gate runs only when the diff touches the root CLAUDE.md, AGENTS.md, GEMINI.md, or any
path under docs/ (a docs move can kill a CLAUDE.md pointer). It never edits CLAUDE.md.

Usage:
  claude-md-gate.py --repo <path> [--base origin/dev] [--head HEAD] [--linter <path>]

Linter lookup order: --linter, $KLEVER_CLAUDE_MD_LINT, then the prototype path below.

Exit: 0 skipped or no new violation, 1 new violations (show them to the human),
      2 usage, 3 CANT_VERIFY (linter missing or failed).
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

DEFAULT_LINTER = ("~/Developer/grp-beklever-com/project-management/general/harness/"
                  "2026-11-04-portal-claude-md-index/repo-claude-md-lint.py")
TRIGGER_FILES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md"}
MEASURED_RULES = {"B1", "B2", "S1", "S3", "S5"}  # messages carry counts that move without a new defect


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def is_trigger(path):
    return path in TRIGGER_FILES or path.startswith("docs/")


def lint(linter, repo, ref):
    r = subprocess.run([sys.executable, linter, "--repo", repo, "--ref", ref], capture_output=True, text=True)
    if r.returncode not in (0, 1):
        return None, r.stderr.strip() or r.stdout.strip()
    if r.stdout.strip() == "no CLAUDE.md":
        return Counter(), None
    found = Counter()
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            found[violation_key(parts[0], parts[2])] += 1  # line numbers shift between refs
    return found, None


def violation_key(rule, msg):
    if rule in MEASURED_RULES:
        msg = re.sub(r"\d+", "#", msg)  # "510 lines > 100" on a file that had 500 is not new
    return rule, msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", default="origin/dev")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--linter")
    a = ap.parse_args()

    diff = git(a.repo, "diff", "--name-only", f"{a.base}...{a.head}")
    if diff.returncode != 0:
        print(f"CANT_VERIFY: git diff {a.base}...{a.head} failed: {diff.stderr.strip()}")
        return 3
    touched = [p for p in diff.stdout.split() if is_trigger(p)]
    if not touched:
        print("SKIP: the MR does not touch CLAUDE.md, AGENTS.md, GEMINI.md or docs/")
        return 0

    linter = os.path.expanduser(a.linter or os.environ.get("KLEVER_CLAUDE_MD_LINT") or DEFAULT_LINTER)
    if not Path(linter).is_file():
        print(f"CANT_VERIFY: linter not found at {linter}")
        return 3

    base, err = lint(linter, a.repo, a.base)
    if base is None:
        print(f"CANT_VERIFY: linter failed on {a.base}: {err}")
        return 3
    head, err = lint(linter, a.repo, a.head)
    if head is None:
        print(f"CANT_VERIFY: linter failed on {a.head}: {err}")
        return 3

    new = sorted((head - base).elements())
    fixed = sum((base - head).values())
    print(f"Touched: {', '.join(touched)}")
    print(f"Pre-existing violations (not this MR's job): {sum((head & base).values())}")
    if fixed:
        print(f"Violations this MR fixes: {fixed}")
    if not new:
        print("RESULT: OK (no new CLAUDE.md schema violation)")
        return 0
    for rule, msg in new:
        print(f"NEW\t{rule}\t{msg}")
    print(f"RESULT: {len(new)} new violation(s). Show them to the human. Do not edit CLAUDE.md without approval.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
