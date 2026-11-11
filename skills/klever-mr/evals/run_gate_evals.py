#!/usr/bin/env python3
"""run_gate_evals.py — Layer A suite for the klever-mr gate scripts.

Self-contained: every case builds throwaway git repos in a temp dir. `gcloud` is replaced by a
fake on PATH, so no network and no auth. Covers:
  preflight   promotion-image-preflight.sh: zip vs image detection, RED vs CANT_VERIFY
  versions    version-locations.py: CI release vars, UV_VERSION is never touched
  claudemd    claude-md-gate.py: only MR-introduced violations, skip when untouched
  dacenv      dac-env-gate.py: parity BLOCK/--ack, removal ACTION, dead-var control
  cleanup     post-merge-cleanup.py: merge/squash proof, preservation refusals, --apply
  skillmd     SKILL.md: no plain-python3 gitlab call; gitlab_skill.py runs under uv without ambient requests

Usage: python3 run_gate_evals.py [--scripts <dir>] [--preflight <path>] [--only <group>] [-v]
  --preflight lets you run the preflight cases against an older copy to prove they fail there.
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
RESULTS = []
VERBOSE = False

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "eval", "GIT_AUTHOR_EMAIL": "eval@example.com",
    "GIT_COMMITTER_NAME": "eval", "GIT_COMMITTER_EMAIL": "eval@example.com",
}


def env(extra=None):
    e = dict(os.environ)
    e.update(GIT_ENV)
    e.update(extra or {})
    return e


def sh(cwd, *args, check=True):
    r = subprocess.run(["git", "-c", "init.defaultBranch=dev", "-c", "commit.gpgsign=false", *args],
                       cwd=cwd, capture_output=True, text=True, env=env())
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}: {r.stderr}")
    return r.stdout.strip()


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def commit_all(repo, msg):
    sh(repo, "add", "-A")
    sh(repo, "commit", "-q", "-m", msg)
    return sh(repo, "rev-parse", "HEAD")


def new_repo(root, name):
    repo = Path(root) / name
    repo.mkdir(parents=True)
    sh(repo, "init", "-q")
    return repo


def run(cmd, extra_env=None, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, env=env(extra_env), cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    mark = "PASS" if cond else "FAIL"
    print(f"{mark}  {name}" + (f"\n      {detail[:600]}" if (not cond or VERBOSE) and detail else ""))


# ---------------------------------------------------------------- preflight
FAKE_GCLOUD = """#!/bin/sh
case "$1 $2" in
  "storage ls")
    [ "$FAKE_GCS_MODE" = "fail" ] && { echo "ERROR: (gcloud.auth) Reauthentication failed." >&2; exit 1; }
    printf '%s\\n' $FAKE_GCS_OBJECTS; exit 0;;
  "artifacts docker")
    [ "$FAKE_AR_MODE" = "fail" ] && { echo "ERROR: (gcloud.auth) Reauthentication failed." >&2; exit 1; }
    for t in $FAKE_AR_TAGS; do printf '%s\\tsha256:abc%s\\n' "$t" "$t"; done; exit 0;;
esac
echo "fake gcloud: unexpected $*" >&2; exit 9
"""

ZIP_CI = """include:
  - project: "grp-comp/grp-includes/datasophia-glb-incl-zip-artifact"
variables:
  DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION: "0.5.1"
  DATASOPHIA_INCL_ZIP_ARTIFACT_NAME: "$CI_PROJECT_NAME"
  DATASOPHIA_INCL_ZIP_ARTIFACT_DESTINATION_BUCKET: "bkt-test"
  UV_VERSION: "0.10.9"
"""
IMAGE_CI = """include:
  - project: "grp-comp/grp-includes/datasophia-glb-incl-build-docker"
variables:
  DATASOPHIA_INCL_BUILD_DOCKER_ENV: "dev"
"""


def preflight_cases(tmp, script):
    bindir = Path(tmp) / "bin"
    bindir.mkdir()
    fake = bindir / "gcloud"
    fake.write_text(FAKE_GCLOUD)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    path_env = f"{bindir}:{os.environ['PATH']}"

    zip_repo = new_repo(tmp, "app-dooh-client-report")
    write(zip_repo / ".gitlab-ci.yml", ZIP_CI)
    write(zip_repo / "pyproject.toml", '[project]\nname = "x"\nversion = "0.5.1"\n')
    sh(zip_repo, "remote", "add", "origin", "git@example.com:grp/app-dooh-client-report.git")
    commit_all(zip_repo, "zip repo")

    img_repo = new_repo(tmp, "app-front-portal")
    write(img_repo / ".gitlab-ci.yml", IMAGE_CI)
    write(img_repo / "package.json", '{"name": "x", "version": "2.0.10"}\n')
    commit_all(img_repo, "image repo")

    plain_repo = new_repo(tmp, "app-nothing")
    write(plain_repo / ".gitlab-ci.yml", "stages: [test]\n")
    write(plain_repo / "package.json", '{"version": "1.0.0"}\n')
    commit_all(plain_repo, "plain")

    obj = "gs://bkt-test/app-dooh-client-report/zip/app-dooh-client-report_0.5.1.zip"
    other = "gs://bkt-test/app-dooh-client-report/zip/app-dooh-client-report_0.5.0.zip"

    def pf(repo, extra, *args):
        e = {"PATH": path_env, "FAKE_GCS_OBJECTS": "", "FAKE_AR_TAGS": ""}
        e.update(extra)
        return run(["bash", script, "--repo", str(repo), *args], e)

    rc, o = pf(zip_repo, {"FAKE_GCS_OBJECTS": f"{other} {obj}"})
    check("preflight/zip-present-green", rc == 0 and "GREEN" in o, o)
    rc, o = pf(zip_repo, {"FAKE_GCS_OBJECTS": other})
    check("preflight/zip-absent-red-not-image-verdict", rc == 1 and "image tag" not in o and "zip" in o, o)
    rc, o = pf(zip_repo, {"FAKE_GCS_MODE": "fail"})
    check("preflight/zip-auth-failure-cant-verify", rc == 3 and "CANT_VERIFY" in o, o)
    rc, o = pf(img_repo, {"FAKE_AR_TAGS": "2.0.9 2.0.10"})
    check("preflight/image-present-green", rc == 0 and "GREEN" in o, o)
    rc, o = pf(img_repo, {"FAKE_AR_TAGS": "2.0.8 2.0.9"})
    check("preflight/image-absent-red", rc == 1 and "RED" in o, o)
    rc, o = pf(img_repo, {"FAKE_AR_MODE": "fail"})
    check("preflight/image-auth-failure-cant-verify", rc == 3 and "CANT_VERIFY" in o, o)
    rc, o = pf(img_repo, {"FAKE_AR_TAGS": ""})
    check("preflight/image-empty-registry-cant-verify", rc == 3, o)
    rc, o = pf(plain_repo, {"FAKE_AR_TAGS": "1.0.0"})
    check("preflight/ambiguous-type-cant-verify", rc == 3 and "ambiguous" in o, o)

    # detection must read the promoted revision, not the working tree
    write(zip_repo / ".gitlab-ci.yml", IMAGE_CI)
    rc, o = pf(zip_repo, {"FAKE_GCS_OBJECTS": obj}, "--ref", "HEAD")
    check("preflight/detects-type-at-ref", rc == 0 and "zip artifact" in o, o)
    sh(zip_repo, "checkout", "-q", "--", ".gitlab-ci.yml")


# ---------------------------------------------------------------- versions
def version_cases(tmp, scripts):
    script = str(scripts / "version-locations.py")
    repo = new_repo(tmp, "faas-app")
    write(repo / "pyproject.toml", '[project]\nname = "x"\nversion = "0.7.0"\n')
    write(repo / ".gitlab-ci.yml", ZIP_CI.replace("0.5.1", "0.7.0"))
    commit_all(repo, "base")
    write(repo / "pyproject.toml", '[project]\nname = "x"\nversion = "0.9.0"\n')

    rc, o = run([sys.executable, script, "--repo", str(repo)])
    check("versions/mismatch-detected", rc == 1 and "MISMATCH" in o and "DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION" in o, o)
    check("versions/uv-version-ignored", "UV_VERSION = 0.10.9 (not a release identity)" in o, o)
    rc, o = run([sys.executable, script, "--repo", str(repo), "--sync"])
    ci = (repo / ".gitlab-ci.yml").read_text()
    check("versions/sync-bumps-release-var", rc == 0 and 'DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION: "0.9.0"' in ci, o)
    check("versions/sync-never-touches-uv-version", 'UV_VERSION: "0.10.9"' in ci, ci)
    rc, o = run([sys.executable, script, "--repo", str(repo)])
    check("versions/agree-after-sync", rc == 0 and "agree on 0.9.0" in o, o)
    rc, o = run([sys.executable, script, "--repo", str(repo), "--ref", "HEAD"])
    check("versions/reads-ref", rc == 0 and "= 0.7.0" in o, o)

    uv_only = new_repo(tmp, "mcp-app")
    write(uv_only / "pyproject.toml", '[project]\nname = "x"\nversion = "1.2.3"\n')
    write(uv_only / ".gitlab-ci.yml", 'variables:\n  UV_VERSION: "0.10.9"\n')
    rc, o = run([sys.executable, script, "--repo", str(uv_only)])
    check("versions/uv-only-is-ok", rc == 0 and "no CI release variable" in o, o)

    pom = new_repo(tmp, "java-app")
    write(pom / "pom.xml", '<project xmlns="http://maven.apache.org/POM/4.0.0"><parent><version>3.2.0</version></parent>'
                           '<version>1.4.2</version></project>')
    write(pom / ".gitlab-ci.yml", 'variables:\n  DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION: "1.4.2"\n')
    rc, o = run([sys.executable, script, "--repo", str(pom)])
    check("versions/pom-project-version-not-parent", rc == 0 and "pom.xml = 1.4.2" in o, o)


# ---------------------------------------------------------------- claude-md
FAKE_LINTER = """import argparse, subprocess, sys
ap = argparse.ArgumentParser(); ap.add_argument('--repo'); ap.add_argument('--ref'); a = ap.parse_args()
r = subprocess.run(['git', '-C', a.repo, 'show', f'{a.ref}:CLAUDE.md'], capture_output=True, text=True)
if r.returncode != 0:
    print('no CLAUDE.md'); sys.exit(1)
v = [l.split(':', 2)[1:] for l in r.stdout.splitlines() if l.startswith('VIOLATION:')]
for i, (rule, msg) in enumerate(v):
    print(f'{rule}\\tL{i + 1}\\t{msg}')
print(f'{len(v)} violation(s)'); sys.exit(1 if v else 0)
"""


def claudemd_cases(tmp, scripts):
    script = str(scripts / "claude-md-gate.py")
    linter = Path(tmp) / "fake_lint.py"
    linter.write_text(FAKE_LINTER)
    repo = new_repo(tmp, "portal")
    write(repo / "CLAUDE.md", "# portal\nVIOLATION:C1:ticket key KTP-1\n")
    write(repo / "src/a.ts", "x\n")
    commit_all(repo, "base")
    sh(repo, "branch", "base")

    write(repo / "src/a.ts", "y\n")
    commit_all(repo, "code only")
    rc, o = run([sys.executable, script, "--repo", str(repo), "--base", "base", "--linter", str(linter)])
    check("claudemd/skip-when-untouched", rc == 0 and "SKIP" in o, o)

    write(repo / "CLAUDE.md", "# portal\nVIOLATION:C1:ticket key KTP-1\nmore text\n")
    commit_all(repo, "touch, no new violation")
    rc, o = run([sys.executable, script, "--repo", str(repo), "--base", "base", "--linter", str(linter)])
    check("claudemd/pre-existing-does-not-block", rc == 0 and "Pre-existing violations (not this MR's job): 1" in o, o)

    write(repo / "CLAUDE.md", "# portal\nnew first line\nVIOLATION:C1:ticket key KTP-1\nVIOLATION:B1:120 lines > 100\n")
    commit_all(repo, "new violation")
    rc, o = run([sys.executable, script, "--repo", str(repo), "--base", "base", "--linter", str(linter)])
    check("claudemd/new-violation-flags", rc == 1 and "NEW\tB1" in o and "NEW\tC1" not in o, o)

    sh(repo, "branch", "-f", "base", "HEAD")
    write(repo / "CLAUDE.md", "# portal\nVIOLATION:C1:ticket key KTP-1\nVIOLATION:B1:130 lines > 100\n")
    commit_all(repo, "file grew, same size violation")
    rc, o = run([sys.executable, script, "--repo", str(repo), "--base", "base", "--linter", str(linter)])
    check("claudemd/size-count-change-not-new", rc == 0, o)
    write(repo / "CLAUDE.md", "# portal\nVIOLATION:C1:ticket key KTP-1\nVIOLATION:C1:ticket key KTP-2\nVIOLATION:B1:130 lines > 100\n")
    commit_all(repo, "second ticket key")
    rc, o = run([sys.executable, script, "--repo", str(repo), "--base", "base", "--linter", str(linter)])
    check("claudemd/second-ticket-key-is-new", rc == 1 and "KTP-2" in o, o)

    write(repo / "docs/guide.md", "doc\n")
    rc, o = run([sys.executable, script, "--repo", str(repo), "--base", "base", "--linter", str(Path(tmp) / "missing.py")])
    check("claudemd/missing-linter-cant-verify", rc == 3 and "CANT_VERIFY" in o, o)


# ---------------------------------------------------------------- dac-env
def tf(names):
    rows = "\n".join(f'          {{ name = "{n}", value = "v" }},' for n in names)
    return f"container = {{\n  env = [\n{rows}\n  ]\n  volumes = [{{ name = \"data-disk\" }}]\n}}\n"


def dacenv_cases(tmp, scripts):
    script = str(scripts / "dac-env-gate.py")
    sib = new_repo(tmp, "dac-gcp-front-portal")
    write(sib / "terraform/res.tf", tf(["KLEVER_USER_MANAGEMENT_URL", "OLD_FLAG", "SHARED"]))
    commit_all(sib, "sibling")
    sh(sib, "branch", "base")

    dac = new_repo(tmp, "dac-gcp-front-klv1ai")
    write(dac / "terraform/res.tf", tf(["KLEVER_USER_MANAGEMENT_URL", "OLD_FLAG", "SHARED", "DEAD_ONE"]))
    commit_all(dac, "base")
    sh(dac, "branch", "base")
    write(dac / "terraform/res.tf", tf(["KLEVER_USER_MANAGEMENT_URL", "SHARED", "DEAD_ONE", "NEW_REQUIRED"]))
    commit_all(dac, "add NEW_REQUIRED, drop OLD_FLAG")

    app = new_repo(tmp, "app-front-portal")
    write(app / "lib/a.ts", "const u = process.env.KLEVER_USER_MANAGEMENT_URL;\nconst f = process.env.OLD_FLAG;\n"
                            "const s = env.SHARED;\nconst n = process.env['NEW_REQUIRED'];\n")
    commit_all(app, "base")
    sh(app, "branch", "base")
    write(app / "lib/a.ts", "const u = process.env.KLEVER_USER_MANAGEMENT_URL;\n"
                            "const s = env.SHARED;\nconst n = process.env['NEW_REQUIRED'];\n")
    head = commit_all(app, "stop reading OLD_FLAG")
    sh(app, "update-ref", "refs/remotes/origin/main", head)
    sh(app, "update-ref", "refs/remotes/origin/dev", head)

    common = [sys.executable, script, "parity", "--dac", str(dac), "--sibling", str(sib), "--base", "base", "--sibling-ref", "HEAD"]
    rc, o = run(common)
    check("dacenv/added-only-here-blocks", rc == 1 and "BLOCK: NEW_REQUIRED" in o, o)
    check("dacenv/removed-still-in-sibling-advisory", "ADVISORY: OLD_FLAG" in o, o)
    check("dacenv/preexisting-asymmetry-info-only", "INFO: pre-existing asymmetry" in o and "DEAD_ONE" in o and "BLOCK: DEAD_ONE" not in o, o)
    rc, o = run(common + ["--ack", "NEW_REQUIRED"])
    check("dacenv/ack-unblocks", rc == 0 and "ACKED: NEW_REQUIRED" in o, o)
    rc, o = run(common + ["--ack", "NEW_REQUIRED", "--app", str(app)])
    check("dacenv/dead-var-candidate", rc == 0 and "CLEANUP CANDIDATE: DEAD_ONE" in o and "CLEANUP CANDIDATE: SHARED" not in o, o)
    rc, o = run(common + ["--ack", "NEW_REQUIRED", "--app", str(app), "--control", "NOT_READ_ANYWHERE"])
    check("dacenv/broken-control-cant-verify", rc == 3 and "positive control" in o, o)

    rc, o = run([sys.executable, script, "app-removal", "--app", str(app), "--base", "base", "--head", "HEAD",
                 "--dac", str(dac), "--dac", str(sib), "--dac-ref", "base"])
    check("dacenv/app-removal-lists-each-dac", rc == 0 and o.count("ACTION: OLD_FLAG") == 2, o)


# ---------------------------------------------------------------- cleanup
def cleanup_cases(tmp, scripts):
    script = str(scripts / "post-merge-cleanup.py")
    bare = Path(tmp) / "remote.git"
    sh(tmp, "init", "-q", "--bare", str(bare))
    repo = new_repo(tmp, "app")
    write(repo / ".gitignore", "node_modules/\n.env.local\n")
    write(repo / "a.txt", "a\n")
    write(repo / "b.txt", "b\n")
    commit_all(repo, "init")
    sh(repo, "remote", "add", "origin", str(bare))
    sh(repo, "push", "-q", "origin", "dev")

    def branch(name, path, text):
        sh(repo, "switch", "-q", "-c", name, "dev")
        write(repo / path, text)
        commit_all(repo, name)
        sh(repo, "switch", "-q", "dev")

    def cmd(name, *extra):
        return run([sys.executable, script, "--repo", str(repo), "--branch", name, *extra])

    # merge commit
    branch("KTP-1-merge", "a.txt", "a merged\n")
    sh(repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'KTP-1-merge' into 'dev'", "KTP-1-merge")
    # squash, followed by an unrelated target commit
    branch("KTP-2-squash", "b.txt", "b squashed\n")
    sh(repo, "merge", "-q", "--squash", "KTP-2-squash")
    sh(repo, "commit", "-q", "-m", "KTP-2 squash")
    write(repo / "c.txt", "later unrelated\n")
    commit_all(repo, "later")
    # never merged
    branch("KTP-3-open", "a.txt", "never merged\n")
    sh(repo, "push", "-q", "origin", "dev")
    sh(repo, "fetch", "-q", "origin")

    rc, o = cmd("KTP-1-merge")
    check("cleanup/merge-commit-proven-dry-run", rc == 0 and "PROVEN: merge commit" in o and "DRY RUN" in o, o)
    check("cleanup/dry-run-keeps-branch", sh(repo, "branch", "--list", "KTP-1-merge") != "", "")
    rc, o = cmd("KTP-2-squash")
    check("cleanup/squash-proven-despite-later-commit", rc == 0 and "PROVEN: squash" in o, o)
    rc, o = cmd("KTP-3-open")
    check("cleanup/unmerged-not-proven", rc == 1 and "NOT PROVEN" in o, o)

    wt_root = Path(tmp) / "wts"
    wt_env = wt_root / "KTP-2-squash"
    sh(repo, "worktree", "add", "-q", str(wt_env), "KTP-2-squash")
    write(wt_env / ".env.local", "SECRET=x\n")
    rc, o = cmd("KTP-2-squash", "--apply")
    check("cleanup/ignored-env-file-refused", rc == 2 and ".env.local" in o and wt_env.exists(), o)
    (wt_env / ".env.local").unlink()
    write(wt_env / "notes.txt", "untracked\n")
    rc, o = cmd("KTP-2-squash", "--apply")
    check("cleanup/untracked-file-refused", rc == 2 and "notes.txt" in o, o)
    (wt_env / "notes.txt").unlink()
    write(wt_env / "node_modules/pkg/index.js", "x\n")
    rc, o = cmd("KTP-2-squash", "--apply")
    gone = not wt_env.exists() and sh(repo, "branch", "--list", "KTP-2-squash") == ""
    check("cleanup/disposable-only-applies", rc == 0 and "CLEANED" in o and gone, o)

    sh(repo, "switch", "-q", "KTP-1-merge")
    rc, o = cmd("KTP-1-merge", "--apply")
    check("cleanup/main-worktree-branch-refused", rc == 2 and "main worktree" in o, o)
    sh(repo, "switch", "-q", "dev")


# ---------------------------------------------------------------- SKILL.md
def skillmd_cases():
    text = (SKILL / "SKILL.md").read_text()
    check("skillmd/no-plain-python3-gitlab-call", "python3 ~/.claude-shared-config/skills/gitlab/" not in text)
    check("skillmd/gitlab-calls-use-uv", "uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py" in text)
    for ref in ("references/external-merge-gate.md", "references/conditional-gates.md"):
        check(f"skillmd/pointer-target-exists:{ref}", ref in text and (SKILL / ref).is_file())
    for s in ("version-locations.py", "claude-md-gate.py", "dac-env-gate.py", "post-merge-cleanup.py"):
        check(f"skillmd/script-wired:{s}", s in text and (SKILL / "scripts" / s).is_file())
    check("skillmd/portal-routes-to-klv1ai", "| `app-front-portal` | `dac-gcp-front-klv1ai`" in text)
    gitlab = SKILL.parent / "gitlab" / "gitlab_skill.py"
    if shutil.which("uv") and gitlab.is_file():
        rc, o = run(["uv", "run", "--quiet", str(gitlab), "--help"], {"PYTHONPATH": ""})
        check("skillmd/gitlab-skill-runs-under-uv", rc == 0 and "ModuleNotFoundError" not in o, o)
    else:
        print("SKIP  skillmd/gitlab-skill-runs-under-uv (uv or gitlab_skill.py missing)")


def main():
    global VERBOSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", default=str(SKILL / "scripts"))
    ap.add_argument("--preflight")
    ap.add_argument("--only")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    VERBOSE = a.v
    scripts = Path(a.scripts)
    groups = {
        "preflight": lambda t: preflight_cases(t, a.preflight or str(scripts / "promotion-image-preflight.sh")),
        "versions": lambda t: version_cases(t, scripts),
        "claudemd": lambda t: claudemd_cases(t, scripts),
        "dacenv": lambda t: dacenv_cases(t, scripts),
        "cleanup": lambda t: cleanup_cases(t, scripts),
        "skillmd": lambda t: skillmd_cases(),
    }
    for name, fn in groups.items():
        if a.only and name != a.only:
            continue
        with tempfile.TemporaryDirectory(prefix=f"klever-mr-{name}-") as tmp:
            try:
                fn(tmp)
            except Exception as exc:  # a crashed group is a failed group
                check(f"{name}/group-crashed", False, repr(exc))
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
