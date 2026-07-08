#!/usr/bin/env python3
"""run_probe_evals.py — deterministic eval suite for deploy-identity/probe.sh.

probe.sh is a probe, not a gate: it always exits 0 and emits a machine line
`DEPLOY_IDENTITY_JSON={...}`. These evals assert on that JSON (status / confidence /
on_deploy_branch / stamp), which is what the deploy-identity-guard hook and the
citation-stamp discipline consume. The hook-runner format (exit-code + needle) does
not fit a probe, so this is a small self-contained runner modelled on
post-comment/evals/run_causal_evals.py.

Hermetic and registry-safe:
  * Repo state comes from the committed code-repo bundle in the hooks-eval fixtures,
    hydrated into a per-case temp dir (gitfixtures.hydrate). {tmp} auto-removed.
  * HOME is overridden to the temp dir so the probe's registry lookup
    ($HOME/.claude/deploy-identity) resolves to an EMPTY dir and falls back to a
    repo-local .deploy-identity.yaml this runner writes. The real
    ~/.claude/deploy-identity/*.yaml files are never read or written.

Usage: python3 run_probe_evals.py [--probe <path>] [-v]
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROBE = os.path.join(os.path.dirname(HERE), "probe.sh")
GITFIXTURES_DIR = os.path.expanduser("~/.claude-shared-config/hooks/evals")
sys.path.insert(0, GITFIXTURES_DIR)
import gitfixtures  # noqa: E402


def write_registry(repo, deploy_branch, default_branch="main", deployed_sha=""):
    with open(os.path.join(repo, ".deploy-identity.yaml"), "w", encoding="utf-8") as fh:
        fh.write(f"deploy_branch: {deploy_branch}\n")
        fh.write(f"default_branch: {default_branch}\n")
        fh.write("owner: sisi\nartifact_source: cache\n")
        if deployed_sha:
            fh.write(f"deployed_sha: {deployed_sha}\n")


def run_probe(probe, target, home):
    env = dict(os.environ)
    env["HOME"] = home  # steer the probe's registry lookup into an empty dir
    proc = subprocess.run(["bash", probe, target], capture_output=True,
                          text=True, env=env, timeout=60)
    line = ""
    for l in proc.stdout.splitlines():
        if l.startswith("DEPLOY_IDENTITY_JSON="):
            line = l[len("DEPLOY_IDENTITY_JSON="):]
    return json.loads(line) if line else {}, proc.stdout


# each builder returns (target_path, expected_fields_dict, stamp_substring_or_None)
def case_verified_on_deploy(tmp):
    repo = os.path.join(tmp, "Developer", "code-fixture")
    gitfixtures.hydrate("code-repo", repo)
    sha = subprocess.run(["git", "-C", repo, "rev-parse", "dev"],
                         capture_output=True, text=True).stdout.strip()
    write_registry(repo, "dev", deployed_sha=sha)
    subprocess.run(["git", "-C", repo, "checkout", "--quiet", "dev"], check=True)
    return os.path.join(repo, "src", "app.py"), \
        {"status": "VERIFIED", "on_deploy_branch": True,
         "confidence": "HIGH-ALLOWED"}, "VERIFIED against dev"


def case_mismatch_on_default(tmp):
    repo = os.path.join(tmp, "Developer", "code-fixture")
    gitfixtures.hydrate("code-repo", repo)
    sha = subprocess.run(["git", "-C", repo, "rev-parse", "dev"],
                         capture_output=True, text=True).stdout.strip()
    write_registry(repo, "dev", deployed_sha=sha)
    # already on main (default) after hydrate
    return os.path.join(repo, "src", "app.py"), \
        {"status": "MISMATCH", "on_deploy_branch": False,
         "confidence": "HYPOTHESIS", "current_branch": "main"}, \
        "UNVERIFIED — read on main"


def case_no_registry(tmp):
    repo = os.path.join(tmp, "Developer", "unregistered-fixture")
    gitfixtures.hydrate("code-repo", repo)
    # no .deploy-identity.yaml; unique basename => no harness registry entry
    return os.path.join(repo, "src", "app.py"), {"status": "NO_REGISTRY"}, None


def case_cant_verify(tmp):
    repo = os.path.join(tmp, "Developer", "code-fixture")
    gitfixtures.hydrate("code-repo", repo)
    write_registry(repo, "dev", deployed_sha="deadbeef" * 5)  # unresolvable
    return os.path.join(repo, "src", "app.py"), \
        {"status": "CANT_VERIFY", "confidence": "CANT_VERIFY"}, None


def case_no_repo(tmp):
    plain = os.path.join(tmp, "Developer", "not-a-repo")
    os.makedirs(plain)
    with open(os.path.join(plain, "file.txt"), "w") as fh:
        fh.write("x\n")
    return os.path.join(plain, "file.txt"), {"status": "NO_REPO"}, None


def case_verified_unresolved_sha_on_deploy(tmp):
    # On the deploy branch, an unresolvable sha still yields VERIFIED (containment
    # 'unknown', not 'false'). Pins that being on the deploy branch is sufficient.
    repo = os.path.join(tmp, "Developer", "code-fixture")
    gitfixtures.hydrate("code-repo", repo)
    write_registry(repo, "dev", deployed_sha="deadbeef" * 5)
    subprocess.run(["git", "-C", repo, "checkout", "--quiet", "dev"], check=True)
    return os.path.join(repo, "src", "app.py"), \
        {"status": "VERIFIED", "on_deploy_branch": True}, None


def case_multi_deploy_branch_contained(tmp):
    # deploy_branch lists two branches; being on either counts as on-deploy AND the
    # checked-out branch must contain the deployed sha. Here sha = main's own tip.
    repo = os.path.join(tmp, "Developer", "code-fixture")
    gitfixtures.hydrate("code-repo", repo)
    sha = subprocess.run(["git", "-C", repo, "rev-parse", "main"],
                         capture_output=True, text=True).stdout.strip()
    write_registry(repo, "dev main", deployed_sha=sha)
    # on main, which is in the deploy_branch list, and main contains this sha
    return os.path.join(repo, "src", "app.py"), \
        {"status": "VERIFIED", "on_deploy_branch": True}, None


def case_listed_branch_missing_deployed_sha(tmp):
    # Behavior to pin: being NAMED in deploy_branch is necessary but NOT sufficient.
    # deploy_branch = "dev main", checked out on main, but deployed sha lives on dev
    # (main does not contain it) -> MISMATCH, not VERIFIED. The probe cross-checks
    # containment, not just the branch name.
    repo = os.path.join(tmp, "Developer", "code-fixture")
    gitfixtures.hydrate("code-repo", repo)
    sha = subprocess.run(["git", "-C", repo, "rev-parse", "dev"],
                         capture_output=True, text=True).stdout.strip()
    write_registry(repo, "dev main", deployed_sha=sha)
    return os.path.join(repo, "src", "app.py"), \
        {"status": "MISMATCH", "on_deploy_branch": True,
         "confidence": "HYPOTHESIS"}, None


CASES = {
    "01-verified-on-deploy-branch": case_verified_on_deploy,
    "02-mismatch-on-default-branch": case_mismatch_on_default,
    "03-no-registry": case_no_registry,
    "04-cant-verify-unresolvable-sha": case_cant_verify,
    "05-no-repo": case_no_repo,
    "06-verified-unresolved-sha-on-deploy": case_verified_unresolved_sha_on_deploy,
    "07-multi-deploy-branch-contained": case_multi_deploy_branch_contained,
    "08-listed-branch-missing-deployed-sha": case_listed_branch_missing_deployed_sha,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", default=DEFAULT_PROBE)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    print(f"=== deploy-identity probe evals → {os.path.basename(args.probe)} ===")
    failures = 0
    for name, builder in CASES.items():
        with tempfile.TemporaryDirectory() as tmp:
            try:
                target, expected, stamp_sub = builder(tmp)
                got, raw = run_probe(args.probe, target, home=tmp)
            except Exception as exc:
                print(f"  {name:44} FAIL runner error: {exc}")
                failures += 1
                continue
            problems = []
            for k, v in expected.items():
                if got.get(k) != v:
                    problems.append(f"{k}={got.get(k)!r} wanted {v!r}")
            if stamp_sub and stamp_sub not in got.get("stamp", ""):
                problems.append(f"stamp {got.get('stamp')!r} missing {stamp_sub!r}")
            status = "PASS" if not problems else "FAIL"
            print(f"  {name:44} {status}")
            if problems:
                failures += 1
                for p in problems:
                    print(f"      ! {p}")
            if args.verbose or problems:
                print(f"      | {json.dumps(got)}")
    total = len(CASES)
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
