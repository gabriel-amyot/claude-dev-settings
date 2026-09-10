#!/usr/bin/env python3
"""Lint a proposed git command against the Klever/harness git rules.

Covers only rules that no evalled hook already enforces. worktree placement,
protected-branch edits and piped mutations belong to worktree-guard,
branch-guard and git-pipe-guard respectively.

Usage:
    python3 git_lint.py "git clone https+iap://cicd.prod.datasophia.com/a/b.git"
    python3 git_lint.py --json "git push --force origin dev"
    echo "<cmd>" | python3 git_lint.py

Exit 1 when any error-level violation is found, else 0.
"""

import argparse
import json
import re
import sys

KLEVER_HOST = "cicd.prod.datasophia.com"

ERROR = "error"
WARN = "warn"


def _finding(code, level, message, fix):
    return {"code": code, "level": level, "message": message, "fix": fix}


def check_klever_clone_scheme(cmd):
    if not re.search(r"\bgit\s+(?:-C\s+\S+\s+)*clone\b", cmd):
        return []
    if f"https+iap://{KLEVER_HOST}" not in cmd:
        return []
    return [_finding(
        "KLEVER_CLONE_SCHEME",
        ERROR,
        f"Cloning {KLEVER_HOST} over https+iap:// fails with "
        "'ConfigGetURLMatch - could not read config http.cookieFile'.",
        f"Clone with plain https://{KLEVER_HOST}/... . The includeIf glob matches "
        "the https:// URL and rewrites the remote to https+iap:// automatically.",
    )]


def check_history_rewrite(cmd):
    findings = []
    if re.search(r"\bgit\s+(?:-C\s+\S+\s+)*push\b[^|&;\n]*\s(?:--force(?:-with-lease)?|-f)\b", cmd):
        findings.append(_finding(
            "HISTORY_REWRITE_FORCE_PUSH", ERROR,
            "Force-pushing rewrites published history.",
            "Do not run it. Hand Gabriel the exact command with branch, remote and "
            "paths so he can decide and run it himself.",
        ))
    if "filter-branch" in cmd or "filter-repo" in cmd:
        findings.append(_finding(
            "HISTORY_REWRITE_FILTER", ERROR,
            "filter-branch/filter-repo rewrites every commit it touches.",
            "Do not run it. Escalate to Gabriel.",
        ))
    if re.search(r"\bgit\s+(?:-C\s+\S+\s+)*reset\s+--hard\s+(?:origin/|\S+~\d|HEAD~\d)", cmd):
        findings.append(_finding(
            "HISTORY_REWRITE_RESET", ERROR,
            "reset --hard to a pushed ref discards published commits.",
            "Use `git revert` to undo a pushed commit, which adds history "
            "instead of rewriting it.",
        ))
    if re.search(r"\bgit\s+(?:-C\s+\S+\s+)*commit\b[^|&;\n]*--amend", cmd):
        findings.append(_finding(
            "AMEND_MAY_REWRITE", WARN,
            "commit --amend rewrites the last commit, which is forbidden once pushed.",
            "Confirm the commit is unpushed. If it is pushed, add a new commit instead.",
        ))
    if re.search(r"\bgit\s+(?:-C\s+\S+\s+)*rebase\b", cmd):
        findings.append(_finding(
            "REBASE_MAY_REWRITE", WARN,
            "Rebase rewrites history and is forbidden on shared branches.",
            "Confirm the branch is unshared. Prefer a merge on anything pushed.",
        ))
    return findings


def check_dac_push_target(cmd, repo_path):
    context = f"{cmd} {repo_path or ''}"
    if "grp-dac" not in context:
        return []
    push = re.search(r"\bgit\s+(?:-C\s+\S+\s+)*push\b([^|&;\n]*)", cmd)
    if not push:
        return []
    if not re.search(r"\b(main|uat|master)\b", push.group(1)):
        return []
    return [_finding(
        "DAC_PUSH_TARGET", ERROR,
        "DAC repos deploy per branch and only dev accepts a direct push.",
        "Push to dev, then promote with a merge request. Hotfixes to uat or main "
        "are human-initiated.",
    )]


BANNED_BRANCH_PREFIXES = ("fix/", "feature/", "feat/", "chore/", "bugfix/", "hotfix/", "release/")


def check_branch_name(cmd):
    match = re.search(
        r"\bgit\s+(?:-C\s+\S+\s+)*(?:checkout\s+-b|switch\s+-c|branch)\s+(\S+)", cmd)
    if not match:
        return []
    name = match.group(1)
    if name.startswith("-"):
        return []
    if not name.lower().startswith(BANNED_BRANCH_PREFIXES):
        return []
    return [_finding(
        "BRANCH_NAME_PREFIX", ERROR,
        f"Branch '{name}' uses a folder-style prefix.",
        "Name it {TICKET-ID}-short-description, e.g. KTP-571-zip-codec. "
        "No fix/, feature/ or chore/ prefixes.",
    )]


def lint(cmd, repo_path=None):
    findings = []
    findings += check_klever_clone_scheme(cmd)
    findings += check_history_rewrite(cmd)
    findings += check_dac_push_target(cmd, repo_path)
    findings += check_branch_name(cmd)
    return findings


def has_error(findings):
    return any(f["level"] == ERROR for f in findings)


def render(findings):
    if not findings:
        return "git-lint: clean"
    lines = []
    for f in findings:
        lines.append(f"[{f['level'].upper()}] {f['code']}: {f['message']}")
        lines.append(f"    fix: {f['fix']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", nargs="?", help="the git command to lint")
    ap.add_argument("--repo", help="repo path for context (DAC detection)")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = ap.parse_args()

    cmd = args.command if args.command is not None else sys.stdin.read()
    findings = lint(cmd, args.repo)

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        print(render(findings))

    return 1 if has_error(findings) else 0


if __name__ == "__main__":
    sys.exit(main())
