#!/usr/bin/env python3
"""Layer A fixtures for skills/git/scripts/git_lint.py.

Deterministic, judge-free, no model calls. Safe for the unattended sweep.

Each case asserts the exact set of violation codes a command produces, so a rule
that stops firing fails loudly instead of degrading into prose nobody tests.

Usage: python3 run_git_evals.py [-v]
Exits non-zero on any failure.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import git_lint  # noqa: E402

KLEVER = "cicd.prod.datasophia.com"

CASES = [
    # --- KLEVER_CLONE_SCHEME: the regression this suite exists for -------------
    {
        "name": "01-clone-https-iap-blocked",
        "why": "warm-finch 2026-09-09: this exact command cost a red pipeline and a "
               "wrong wiki 'reconfirm'. Seven prose entries never stopped it.",
        "cmd": f"git clone https+iap://{KLEVER}/grp-cst/grp-beklever-com/grp-faas/grp-cfg/cfg-iac-rnd.git",
        "expect": ["KLEVER_CLONE_SCHEME"],
    },
    {
        "name": "02-clone-plain-https-clean",
        "why": "the documented primary fix must not be flagged",
        "cmd": f"git clone https://{KLEVER}/grp-cst/grp-beklever-com/grp-faas/grp-cfg/cfg-iac-rnd.git",
        "expect": [],
    },
    {
        "name": "03-remote-add-https-iap-clean",
        "why": "an https+iap remote on an existing repo is legitimate; only clone fails",
        "cmd": f"git remote add origin https+iap://{KLEVER}/a/b.git",
        "expect": [],
    },
    {
        "name": "04-clone-other-host-clean",
        "why": "the scheme rule is Klever-host specific",
        "cmd": "git clone https+iap://gitlab.prod.origin8cares.com/a/b.git",
        "expect": [],
    },

    # --- HISTORY_REWRITE ------------------------------------------------------
    {
        "name": "10-force-push-blocked",
        "why": "absolute rule, even on approval",
        "cmd": "git push --force origin dev",
        "expect": ["HISTORY_REWRITE_FORCE_PUSH"],
    },
    {
        "name": "11-force-push-short-flag-blocked",
        "why": "-f is the same action",
        "cmd": "git push -f origin dev",
        "expect": ["HISTORY_REWRITE_FORCE_PUSH"],
    },
    {
        "name": "12-force-with-lease-blocked",
        "why": "still rewrites published history",
        "cmd": "git push --force-with-lease origin main",
        "expect": ["HISTORY_REWRITE_FORCE_PUSH"],
    },
    {
        "name": "13-filter-branch-blocked",
        "why": "rewrites every commit it touches",
        "cmd": "git filter-branch --tree-filter 'rm -f secret' HEAD",
        "expect": ["HISTORY_REWRITE_FILTER"],
    },
    {
        "name": "14-reset-hard-to-remote-blocked",
        "why": "discards pushed commits",
        "cmd": "git reset --hard origin/main",
        "expect": ["HISTORY_REWRITE_RESET"],
    },
    {
        "name": "15-reset-hard-bare-clean",
        "why": "discarding local uncommitted work is routine and allowed",
        "cmd": "git reset --hard",
        "expect": [],
    },
    {
        "name": "16-amend-warns-only",
        "why": "forbidden once pushed, but pushed-ness is not knowable statically",
        "cmd": "git commit --amend -m 'fix'",
        "expect": ["AMEND_MAY_REWRITE"],
    },
    {
        "name": "17-rebase-warns-only",
        "why": "forbidden on shared branches only",
        "cmd": "git rebase origin/dev",
        "expect": ["REBASE_MAY_REWRITE"],
    },
    {
        "name": "18-normal-push-clean",
        "why": "the common case must stay silent or the lint gets ignored",
        "cmd": "git push origin KTP-571-zip-codec",
        "expect": [],
    },

    # --- DAC_PUSH_TARGET ------------------------------------------------------
    {
        "name": "20-dac-push-main-blocked",
        "why": "DAC repos: dev only, promote by MR",
        "cmd": "git -C ~/Developer/grp-beklever-com/grp-dac/grp-dac-env-back/dac-gcp-back-proxrp push origin main",
        "expect": ["DAC_PUSH_TARGET"],
    },
    {
        "name": "21-dac-push-uat-blocked",
        "why": "uat is equally human-initiated",
        "cmd": "git push origin uat",
        "repo": "~/Developer/grp-beklever-com/grp-dac/grp-dac-env-back/dac-gcp-back-proxrp",
        "expect": ["DAC_PUSH_TARGET"],
    },
    {
        "name": "22-dac-push-dev-clean",
        "why": "dev is the sanctioned DAC target",
        "cmd": "git -C ~/Developer/grp-beklever-com/grp-dac/x/dac-gcp-back-proxrp push origin dev",
        "expect": [],
    },
    {
        "name": "23-non-dac-push-main-clean",
        "why": "plenty of repos legitimately use main as default",
        "cmd": "git -C ~/Developer/grp-beklever-com/project-management push origin main",
        "expect": [],
    },

    # --- BRANCH_NAME ----------------------------------------------------------
    {
        "name": "30-feature-prefix-blocked",
        "why": "convention is {TICKET-ID}-short-description",
        "cmd": "git checkout -b feature/add-zip-codec",
        "expect": ["BRANCH_NAME_PREFIX"],
    },
    {
        "name": "31-fix-prefix-blocked",
        "why": "same rule, different prefix",
        "cmd": "git switch -c fix/broken-map",
        "expect": ["BRANCH_NAME_PREFIX"],
    },
    {
        "name": "32-ticket-branch-clean",
        "why": "the correct shape",
        "cmd": "git checkout -b KTP-571-zip-codec",
        "expect": [],
    },
    {
        "name": "33-descriptive-branch-clean",
        "why": "ticketless repos (e.g. app-agent-skills) use descriptive names",
        "cmd": "git checkout -b add-rnd-fahren",
        "expect": [],
    },

    # --- no cross-firing ------------------------------------------------------
    {
        "name": "40-read-only-clean",
        "why": "queries must never be flagged",
        "cmd": "git log --oneline -5 | head",
        "expect": [],
    },
    {
        "name": "41-two-rules-both-fire",
        "why": "findings accumulate rather than short-circuit",
        "cmd": f"git clone https+iap://{KLEVER}/a/b.git && git push --force origin main",
        "expect": ["KLEVER_CLONE_SCHEME", "HISTORY_REWRITE_FORCE_PUSH"],
    },
]


def run(verbose=False):
    failures = []
    for case in CASES:
        findings = git_lint.lint(case["cmd"], case.get("repo"))
        got = sorted(f["code"] for f in findings)
        want = sorted(case["expect"])
        ok = got == want
        if not ok:
            failures.append((case, want, got))
        if verbose or not ok:
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {case['name']}")
            if not ok:
                print(f"        want: {want or '(clean)'}")
                print(f"        got:  {got or '(clean)'}")
                print(f"        cmd:  {case['cmd']}")
                print(f"        why:  {case['why']}")

    total = len(CASES)
    print(f"\ngit/lint: {total - len(failures)}/{total} passed")
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    return run(args.verbose)


if __name__ == "__main__":
    sys.exit(main())
