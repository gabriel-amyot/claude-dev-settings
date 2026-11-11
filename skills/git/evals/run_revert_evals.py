#!/usr/bin/env python3
"""Layer A fixtures for skills/git/scripts/revert_check.py.

Builds throwaway git repos in a temp dir, applies a revert the right way and the
wrong ways, and asserts the exit code of revert_check.py. Deterministic, no
network, no model calls.

Why: the 2026-10-29 revert-and-isolate proposal asserted `git diff <pre-merge>
HEAD` is empty. That check fails a correct revert (the forward version bump
differs) and passes a revert that erased unrelated work. These cases pin the
change-specific check instead.

Usage: python3 run_revert_evals.py [-v]
Exits non-zero on any failure.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "revert_check.py"
ENV = dict(os.environ, GIT_AUTHOR_NAME="eval", GIT_AUTHOR_EMAIL="eval@example.com",
           GIT_COMMITTER_NAME="eval", GIT_COMMITTER_EMAIL="eval@example.com",
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)


def g(repo, *args):
    out = subprocess.run(["git", "-C", repo, "-c", "core.hooksPath=/dev/null", *args],
                         capture_output=True, text=True, env=ENV)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr}")
    return out.stdout.strip()


def write(repo, path, text):
    full = Path(repo) / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(text)


def commit(repo, msg, files):
    for path, text in files.items():
        write(repo, path, text)
    g(repo, "add", "-A")
    g(repo, "commit", "-q", "-m", msg)
    return g(repo, "rev-parse", "HEAD")


def build_merge_repo(tmp, squash=False):
    """dev: base -> merge(feature: Boot4 upgrade) -> unrelated fix. Returns ids."""
    repo = os.path.join(tmp, "squash" if squash else "merge")
    os.makedirs(repo)
    g(repo, "init", "-q", "-b", "dev")
    commit(repo, "base", {"pom.xml": "<version>1.4.0</version>\n", "CHANGELOG.md": "## 1.4.0\n",
                          "src/App.java": "boot3\n", "src/Other.java": "other v1\n"})
    if squash:
        bad = commit(repo, "KTP-1: Boot 4 upgrade (squash)",
                     {"src/App.java": "boot4\n", "src/New.java": "new\n", "pom.xml": "<version>1.5.0</version>\n"})
    else:
        g(repo, "checkout", "-q", "-b", "feature")
        commit(repo, "KTP-1: Boot 4 upgrade", {"src/App.java": "boot4\n", "src/New.java": "new\n"})
        commit(repo, "KTP-1: bump", {"pom.xml": "<version>1.5.0</version>\n"})
        g(repo, "checkout", "-q", "dev")
        g(repo, "merge", "-q", "--no-ff", "-m", "Merge KTP-1", "feature")
        bad = g(repo, "rev-parse", "HEAD")
    unrelated = commit(repo, "KTP-2: unrelated fix", {"src/Other.java": "other v2\n"})
    return repo, bad, unrelated


def revert(repo, bad, squash):
    args = ["revert", "--no-edit"] + ([] if squash else ["-m", "1"]) + [bad]
    g(repo, *args)


def forward_bump(repo):
    commit(repo, "KTP-3: revert Boot 4, version forward",
           {"pom.xml": "<version>1.5.1</version>\n", "CHANGELOG.md": "## 1.5.1\nReverted KTP-1\n## 1.4.0\n"})


def run_check(repo, base, bad, allow=("pom.xml", "CHANGELOG.md")):
    cmd = [sys.executable, str(SCRIPT), "--repo", repo, "--base", base, "--reverted", bad]
    for path in allow:
        cmd += ["--allow", path]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.returncode, out.stdout


def case_correct_merge_revert(tmp):
    repo, bad, unrelated = build_merge_repo(tmp)
    revert(repo, bad, squash=False)
    forward_bump(repo)
    return run_check(repo, unrelated, bad), 0


def case_correct_squash_revert(tmp):
    repo, bad, unrelated = build_merge_repo(tmp, squash=True)
    revert(repo, bad, squash=True)
    forward_bump(repo)
    return run_check(repo, unrelated, bad), 0


def case_whole_tree_restore_erases_unrelated(tmp):
    """The proposal's step-4 shape: checkout the pre-merge tree. It drops KTP-2."""
    repo, bad, unrelated = build_merge_repo(tmp)
    g(repo, "checkout", f"{bad}^1", "--", ".")
    g(repo, "rm", "-q", "--cached", "src/New.java")
    os.remove(os.path.join(repo, "src/New.java"))
    g(repo, "commit", "-q", "-am", "restore pre-merge tree")
    forward_bump(repo)
    return run_check(repo, unrelated, bad), 1


def case_incomplete_revert(tmp):
    repo, bad, unrelated = build_merge_repo(tmp)
    commit(repo, "partial revert", {"src/App.java": "boot3\n"})
    forward_bump(repo)
    return run_check(repo, unrelated, bad), 1


def case_version_bump_without_allow_fails(tmp):
    """Metadata differences are legitimate only when named with --allow."""
    repo, bad, unrelated = build_merge_repo(tmp)
    revert(repo, bad, squash=False)
    forward_bump(repo)
    return run_check(repo, unrelated, bad, allow=()), 1


def case_later_edit_to_reverted_path_needs_review(tmp):
    repo, bad, _ = build_merge_repo(tmp)
    later = commit(repo, "KTP-4: touch App again", {"src/App.java": "boot4 + hotfix\n"})
    commit(repo, "manual revert of App", {"src/App.java": "boot3\n", "src/New.java": ""})
    g(repo, "rm", "-q", "src/New.java")
    g(repo, "commit", "-q", "-m", "drop New")
    forward_bump(repo)
    return run_check(repo, later, bad), 2


CASES = [
    ("01-merge-commit-revert-with-forward-bump-passes", case_correct_merge_revert),
    ("02-squash-commit-revert-passes", case_correct_squash_revert),
    ("03-whole-tree-restore-that-drops-unrelated-work-fails", case_whole_tree_restore_erases_unrelated),
    ("04-incomplete-revert-fails", case_incomplete_revert),
    ("05-unlisted-metadata-change-fails", case_version_bump_without_allow_fails),
    ("06-path-changed-again-later-is-review", case_later_edit_to_reverted_path_needs_review),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", action="store_true")
    args = parser.parse_args()
    failed = 0
    for name, fn in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                (rc, out), want = fn(tmp)
                ok = rc == want
                detail = f"rc={rc} want={want} {out.strip()[:200]}"
            except Exception as e:  # fixture build failure is a suite failure
                ok, detail = False, f"fixture error: {e}"
        failed += 0 if ok else 1
        print(f"{name:<58} {'PASS' if ok else 'FAIL'}" + (f"  {detail}" if args.v or not ok else ""))
    print("-" * 64)
    print(f"{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
