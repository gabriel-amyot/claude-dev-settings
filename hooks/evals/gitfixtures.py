#!/usr/bin/env python3
"""gitfixtures.py — persisted git fixture repos for hook evals, hermetic at runtime.

Fixture repo STATE is committed as `git bundle` files under fixtures/repos/ (bundles
are single binary files, so they survive being committed inside shared-config, unlike
working trees whose .git/ dirs can't nest). At runtime each eval case hydrates a fresh
clone into its temp dir, because guard tests MUTATE repo state (checkouts, branch
creation attempts) and each run needs a hermetic copy.

Build (or rebuild after editing a builder below):
    python3 gitfixtures.py --build            # writes fixtures/repos/*.bundle
Hydrate from another script:
    import gitfixtures; gitfixtures.hydrate("code-repo", dest_dir)

Builders are deterministic (fixed author/committer identity and dates) so a rebuild
produces reviewable, stable bundles.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLES_DIR = os.path.join(HERE, "fixtures", "repos")

FIXED_ENV = {
    "GIT_AUTHOR_NAME": "eval-fixture",
    "GIT_AUTHOR_EMAIL": "eval-fixture@localhost",
    "GIT_COMMITTER_NAME": "eval-fixture",
    "GIT_COMMITTER_EMAIL": "eval-fixture@localhost",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000",
}


def git(args, cwd, env_extra=None):
    env = dict(os.environ)
    env.update(FIXED_ENV)
    if env_extra:
        env.update(env_extra)
    subprocess.run(["git"] + args, cwd=cwd, env=env, check=True,
                   capture_output=True, text=True)


def write(repo, rel, content):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path) or repo, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def hydrate(bundle_name, dest, branch=None):
    """Clone fixtures/repos/<bundle_name>.bundle into dest. Returns dest."""
    bundle = os.path.join(BUNDLES_DIR, bundle_name + ".bundle")
    if not os.path.exists(bundle):
        raise FileNotFoundError(
            f"no fixture bundle {bundle}; run gitfixtures.py --build")
    cmd = ["git", "clone", "--quiet", bundle, dest]
    if branch:
        cmd[3:3] = ["--branch", branch]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    # materialize every bundled branch locally, then detach from the bundle so
    # `git fetch` in tests fails loudly instead of silently touching the bundle
    out = subprocess.run(
        ["git", "-C", dest, "for-each-ref", "--format=%(refname:strip=3)",
         "refs/remotes/origin"], check=True, capture_output=True, text=True)
    current = subprocess.run(["git", "-C", dest, "branch", "--show-current"],
                             check=True, capture_output=True, text=True).stdout.strip()
    for name in out.stdout.split():
        if name in ("HEAD", current):
            continue
        subprocess.run(["git", "-C", dest, "branch", name, f"origin/{name}"],
                       check=True, capture_output=True)
    subprocess.run(["git", "-C", dest, "remote", "remove", "origin"],
                   check=True, capture_output=True)
    return dest


# --- builders ---------------------------------------------------------------

def build_code_repo(repo):
    """Generic code repo: main (default) + dev branch 2 commits ahead.

    Mirrors the app-agent-hub shape from KTP-688: main is default, dev is what
    deploys and has diverged. Used by branch-guard / worktree-guard /
    deploy-identity fixtures.
    """
    git(["init", "--quiet", "-b", "main", "."], repo)
    write(repo, "src/app.py", "def handler():\n    return 'v1'\n")
    write(repo, "README.md", "# fixture code repo\n")
    git(["add", "-A"], repo)
    git(["commit", "--quiet", "-m", "initial commit on main"], repo)
    git(["checkout", "--quiet", "-b", "dev"], repo)
    write(repo, "src/app.py",
          "def handler():\n    return 'v2-dev-only'\n\n\ndef deployed_path():\n    return True\n")
    git(["add", "-A"], repo)
    git(["commit", "--quiet", "-m", "dev-only change (deploys from dev)"],
        repo, {"GIT_AUTHOR_DATE": "2026-01-02T00:00:00 +0000",
               "GIT_COMMITTER_DATE": "2026-01-02T00:00:00 +0000"})
    write(repo, "src/extra.py", "EXTRA = True\n")
    git(["add", "-A"], repo)
    git(["commit", "--quiet", "-m", "second dev commit"],
        repo, {"GIT_AUTHOR_DATE": "2026-01-03T00:00:00 +0000",
               "GIT_COMMITTER_DATE": "2026-01-03T00:00:00 +0000"})
    git(["checkout", "--quiet", "main"], repo)


def build_pm_repo(repo):
    """Single-trunk repo shaped like project-management: only main, docs tree."""
    git(["init", "--quiet", "-b", "main", "."], repo)
    write(repo, "CLAUDE.md", "# fixture pm repo — single trunk\n")
    write(repo, "tickets/KTP/no-epic/KTP-000/README.md", "# fixture ticket\n")
    git(["add", "-A"], repo)
    git(["commit", "--quiet", "-m", "initial pm fixture"], repo)


BUILDERS = {
    "code-repo": build_code_repo,
    "pm-repo": build_pm_repo,
}


def build_all():
    os.makedirs(BUNDLES_DIR, exist_ok=True)
    for name, builder in BUILDERS.items():
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, name)
            os.makedirs(repo)
            builder(repo)
            bundle = os.path.join(BUNDLES_DIR, name + ".bundle")
            if os.path.exists(bundle):
                os.remove(bundle)
            git(["bundle", "create", bundle, "--all"], repo)
            print(f"built {bundle}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true",
                    help="rebuild all fixture bundles from builders")
    ap.add_argument("--hydrate", metavar="NAME",
                    help="hydrate a bundle into --dest for manual inspection")
    ap.add_argument("--dest")
    args = ap.parse_args()
    if args.build:
        build_all()
        return 0
    if args.hydrate:
        if not args.dest:
            print("--hydrate requires --dest", file=sys.stderr)
            return 1
        hydrate(args.hydrate, args.dest)
        print(f"hydrated {args.hydrate} → {args.dest}")
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
