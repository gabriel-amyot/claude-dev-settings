#!/usr/bin/env python3
"""revert_check.py: prove a revert undid exactly the reverted change, and nothing else.

Read-only. Runs `git` plumbing only. Stdlib only.

A whole-tree check (`git diff <pre-merge> HEAD` is empty) is wrong after a real
revert: the forward version bump and the CHANGELOG entry must differ, and any
unrelated commit merged after the bad change must survive. This check is
change-specific instead:

  1. Every path the reverted commit(s) touched is back to its content before
     that commit. Paths that a later mainline commit also touched are reported
     as REVIEW, because a mechanical revert cannot decide them.
  2. No path outside the reverted change differs from the pre-revert tip,
     except the paths in --allow (version file, CHANGELOG).

Usage:
  revert_check.py --base <pre-revert tip, e.g. origin/dev> \
                  --reverted <sha> [--reverted <sha> ...] \
                  [--allow pom.xml --allow CHANGELOG.md] [--head HEAD] [--repo DIR]

Exit: 0 = clean, 1 = FAIL found, 2 = only REVIEW items (a human must read them).
"""
import argparse
import subprocess
import sys


def git(repo, *args, check=True):
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out


def touched_paths(repo, sha):
    """Paths changed by sha relative to its first parent (the mainline for a merge)."""
    out = git(repo, "diff", "--name-only", "--no-renames", f"{sha}^1", sha)
    return {line for line in out.stdout.splitlines() if line}


def blob_id(repo, rev, path):
    out = git(repo, "rev-parse", "--verify", "--quiet", f"{rev}:{path}", check=False)
    return out.stdout.strip() or None


def mainline_after(repo, sha, base):
    """First-parent commits after sha up to base, newest first."""
    out = git(repo, "rev-list", "--first-parent", f"{sha}..{base}")
    return [line for line in out.stdout.splitlines() if line]


def full_sha(repo, rev):
    return git(repo, "rev-parse", "--verify", rev).stdout.strip()


def check(repo, base, reverted, allow, head="HEAD"):
    """Return (fails, reviews) as lists of strings."""
    reverted = [full_sha(repo, r) for r in reverted]
    allow = set(allow or [])
    fails, reviews = [], []

    owner = {}
    order = git(repo, "rev-list", "--first-parent", base).stdout.split()
    position = {sha: i for i, sha in enumerate(order)}
    for sha in reverted:
        if sha not in position:
            fails.append(f"FAIL {sha[:10]} is not on the first-parent history of {base}")
            continue
        for path in touched_paths(repo, sha):
            current = owner.get(path)
            if current is None or position[sha] > position[current]:
                owner[path] = sha

    for path, sha in sorted(owner.items()):
        if path in allow:
            continue
        later = [c for c in mainline_after(repo, sha, base)
                 if c not in reverted and path in touched_paths(repo, c)]
        if later:
            reviews.append(f"REVIEW {path}: also changed after {sha[:10]} by "
                           f"{', '.join(c[:10] for c in later)}; decide by hand")
            continue
        if blob_id(repo, f"{sha}^1", path) != blob_id(repo, head, path):
            fails.append(f"FAIL {path}: not restored to its state before {sha[:10]}")

    changed = git(repo, "diff", "--name-only", "--no-renames", base, head).stdout.split()
    for path in changed:
        if path in owner or path in allow:
            continue
        fails.append(f"FAIL {path}: changed outside the reverted change "
                     f"(unrelated work lost or extra edit)")
    return fails, reviews


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--reverted", action="append", required=True)
    parser.add_argument("--allow", action="append", default=[])
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    try:
        fails, reviews = check(args.repo, args.base, args.reverted, args.allow, args.head)
    except RuntimeError as e:
        print(f"FAIL {e}")
        return 1
    for line in fails + reviews:
        print(line)
    if fails:
        return 1
    if reviews:
        return 2
    print("OK revert is change-specific: reverted paths restored, other work kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
