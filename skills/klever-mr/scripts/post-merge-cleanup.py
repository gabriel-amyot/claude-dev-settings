#!/usr/bin/env python3
"""post-merge-cleanup.py — remove a feature worktree and branch only after the merge is proven.

Proof, in order:
  1. merge commit: the branch HEAD is an ancestor of origin/<target>.
  2. squash: some first-parent commit C on origin/<target> has the tree that
     `git merge-tree --write-tree C^1 <branch>` produces. Later, unrelated target commits do not matter.
No proof -> nothing is removed.

Preservation: the worktree must have no modified or untracked files, and no ignored file
outside the disposable build dirs (node_modules, target, .venv, dist, ...). `git worktree remove`
without --force deletes ignored files, so a `.env.local` or a `*.bak` blocks the cleanup here.

Dry run by default. --apply runs `git worktree remove` (never --force), `git branch -D`, `git worktree prune`.
The remote branch and /tmp clones are reported, never deleted.

Usage:
  post-merge-cleanup.py --repo <any checkout of the repo> --branch <name> [--target dev]
                        [--search-depth 200] [--ticket KTP-123] [--apply]
Run `git fetch origin` first so origin/<target> is current.

Exit: 0 proven (plan shown or applied), 1 merge not proven, 2 refused (preserve files or
      branch checked out in the main worktree), 3 error.
"""
import argparse
import glob
import subprocess
import sys

DISPOSABLE = {"node_modules", "target", ".venv", "venv", "dist", "build", ".next", "__pycache__",
              ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage", ".gradle", ".turbo", "out",
              ".mr-description.md", ".DS_Store"}


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def out(repo, *args):
    r = git(repo, *args)
    return r.stdout.strip() if r.returncode == 0 else None


def worktrees(repo):
    entries, cur = [], {}
    for line in (out(repo, "worktree", "list", "--porcelain") or "").splitlines():
        if not line:
            if cur:
                entries.append(cur)
            cur = {}
            continue
        key, _, val = line.partition(" ")
        cur[key] = val
    if cur:
        entries.append(cur)
    return entries


def prove_merge(repo, head, target, depth):
    if git(repo, "merge-base", "--is-ancestor", head, target).returncode == 0:
        return f"merge commit: {head[:10]} is an ancestor of {target}"
    base = out(repo, "merge-base", head, target)
    branch_files = set((out(repo, "diff", "--name-only", f"{base}..{head}") or "").split()) if base else set()
    if not branch_files:
        return None
    for commit in (out(repo, "rev-list", "--first-parent", f"-n{depth}", target) or "").split():
        parent = out(repo, "rev-parse", f"{commit}^1")
        if not parent:
            continue
        touched = set((out(repo, "diff", "--name-only", parent, commit) or "").split())
        if not touched & branch_files:
            continue
        merged = git(repo, "merge-tree", "--write-tree", parent, head)
        if merged.returncode != 0:
            continue
        if merged.stdout.split()[0] == out(repo, "rev-parse", f"{commit}^{{tree}}"):
            return f"squash: {commit[:10]} on {target} equals {head[:10]} merged onto {parent[:10]}"
    return None


def preserve_list(wt):
    status = git(wt, "status", "--porcelain", "--ignored=matching")
    if status.returncode != 0:
        return [f"cannot read status: {status.stderr.strip()}"]
    keep = []
    for line in status.stdout.splitlines():
        code, path = line[:2], line[3:]
        if code != "!!":
            keep.append(f"{code.strip() or '??'} {path}")
            continue
        top = path.rstrip("/").split("/")[0]
        leaf = path.rstrip("/").split("/")[-1]
        if top not in DISPOSABLE and leaf not in DISPOSABLE:
            keep.append(f"ignored {path}")
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--target", default="dev")
    ap.add_argument("--search-depth", type=int, default=200)
    ap.add_argument("--ticket")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    head = out(a.repo, "rev-parse", "--verify", f"refs/heads/{a.branch}")
    target = f"origin/{a.target}"
    if not head or not out(a.repo, "rev-parse", "--verify", target):
        print(f"ERROR: branch {a.branch} or {target} not found")
        return 3

    proof = prove_merge(a.repo, head, target, a.search_depth)
    if not proof:
        print(f"NOT PROVEN: no commit on {target} carries {a.branch} ({head[:10]}). Nothing removed.")
        return 1
    print(f"PROVEN: {proof}")

    trees = worktrees(a.repo)
    main_wt = trees[0]["worktree"] if trees else a.repo
    branch_ref = f"refs/heads/{a.branch}"
    wt = next((t["worktree"] for t in trees if t.get("branch") == branch_ref), None)
    if wt == main_wt:
        print(f"REFUSED: {a.branch} is checked out in the main worktree. Switch it to {a.target} first.")
        return 2
    if wt:
        keep = preserve_list(wt)
        if keep:
            print(f"REFUSED: {wt} holds files that cleanup would lose. Move or delete them, then re-run:")
            for item in keep:
                print(f"  {item}")
            return 2

    plan = ([["worktree", "remove", wt]] if wt else []) + [["branch", "-D", a.branch], ["worktree", "prune"]]
    for step in plan:
        print(("RUN: " if a.apply else "PLAN: ") + "git " + " ".join(step))
        if a.apply:
            r = git(main_wt, *step)
            if r.returncode != 0:
                print(f"STOPPED: git {' '.join(step)} failed: {r.stderr.strip()}")
                return 3

    remote = git(main_wt, "ls-remote", "--heads", "origin", a.branch)
    if remote.returncode != 0:
        print(f"REMOTE: cannot check origin/{a.branch}: {remote.stderr.strip()}")
    elif remote.stdout.strip():
        print(f"REMOTE: origin/{a.branch} still exists. GitLab usually deletes it on merge. Not deleted here.")
    else:
        print(f"REMOTE: origin/{a.branch} is gone")

    if a.ticket:
        for path in sorted(glob.glob(f"/tmp/*{a.ticket}*")):
            baks = glob.glob(f"{path}/**/*.bak", recursive=True)
            print(f"TMP: {path} (review before removal; {len(baks)} *.bak file(s))")
    print("RESULT: CLEANED" if a.apply else "RESULT: DRY RUN (re-run with --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
