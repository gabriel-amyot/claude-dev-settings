#!/usr/bin/env python3
"""Launch-time preflight and a temporary pre-push guard for headless dark-factory builds.

Procedure and rationale: ../references/headless-launch.md. This script owns only the deterministic
parts. It never launches a build, never opens an MR, and never deletes a worktree or a branch.

    headless_launch_guard.py preflight     --repo <code repo> [--min-free-gb 15] [--auth-smoke] [--no-fetch]
    headless_launch_guard.py install-guard --repo <code repo> [--protect dev,uat,main,master] [--protect-prefix P ...]
    headless_launch_guard.py remove-guard  --repo <code repo>
    headless_launch_guard.py status        --repo <code repo>
    headless_launch_guard.py hook          --config <json>        (called by the installed hook only)

Exit codes: 0 ok, 1 refused / check failed, 2 usage or environment error.
Source: KTP-1216 overnight builds (2026-11-02/03). Two of four build attempts were lost to launcher faults.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

MARKER = "# dark-factory-headless-guard v1"
BACKUP_NAME = "pre-push.dark-factory-backup"
CONFIG_NAME = "dark-factory-guard.json"
ZERO_SHA = "0" * 40
DEFAULT_PROTECTED = ["dev", "uat", "main", "master"]
PM_SEGMENT = "project-management"


def git(repo, *args, check=False):
    proc = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def hooks_dir(repo):
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir", check=True).stdout.strip()
    return os.path.join(common, "hooks"), common


def sha256_of(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def is_project_management(path):
    parts = os.path.abspath(path).split(os.sep)
    return PM_SEGMENT in parts


# ---------------------------------------------------------------- preflight
def preflight(repo, min_free_gb, auth_smoke, do_fetch):
    checks = []

    def record(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    repo = os.path.abspath(repo)
    record("claude_cli", shutil.which("claude") is not None, "claude CLI on PATH" if shutil.which("claude") else "claude CLI missing")
    is_repo = git(repo, "rev-parse", "--git-dir").returncode == 0 if os.path.isdir(repo) else False
    record("git_repo", is_repo, repo)
    record("not_project_management", not is_project_management(repo),
           "launch the child INSIDE the code repo; project-management must never get a worktree")
    if is_repo:
        hooks_path = git(repo, "config", "--get", "core.hooksPath").stdout.strip()
        record("no_hooks_path", hooks_path == "", f"core.hooksPath={hooks_path!r}" if hooks_path else "unset")
        record("no_husky", not os.path.isdir(os.path.join(repo, ".husky")), ".husky/ present" if os.path.isdir(os.path.join(repo, ".husky")) else "absent")
        dirty = git(repo, "status", "--porcelain").stdout.strip()
        record("clean_main_checkout", dirty == "", "clean" if not dirty else f"{len(dirty.splitlines())} changed path(s)")
        if do_fetch:
            fetch = git(repo, "fetch", "origin")
            record("fetch_origin", fetch.returncode == 0, fetch.stderr.strip()[-200:] or "ok")
    free_gb = None
    if os.path.isdir(repo):
        free_gb = round(shutil.disk_usage(repo).free / (1024 ** 3), 1)
        record("free_disk", free_gb >= min_free_gb, f"{free_gb} GB free on the repo volume (floor {min_free_gb} GB)")
    if auth_smoke and shutil.which("claude"):
        try:
            smoke = subprocess.run(["claude", "-p", "Reply with exactly: OK"], capture_output=True, text=True,
                                   stdin=subprocess.DEVNULL, timeout=180)
            record("claude_auth_smoke", smoke.returncode == 0 and "OK" in smoke.stdout, (smoke.stdout or smoke.stderr).strip()[:200])
        except subprocess.TimeoutExpired:
            record("claude_auth_smoke", False, "claude -p timed out after 180 s")
    ok = all(c["ok"] for c in checks)
    return {
        "ok": ok,
        "checks": checks,
        # Pass these straight into the dark-factory Workflow args (substrate preflight, 0.10.6).
        "workflow_args": {"cwd": repo, "free_disk_gb": free_gb, "min_free_gb": min_free_gb},
    }


# ---------------------------------------------------------------- guard install / remove
def hook_body(config_path):
    script = os.path.abspath(__file__)
    return (
        "#!/bin/sh\n"
        f"{MARKER}\n"
        "# TEMPORARY. Installed for an unattended dark-factory run. Remove with:\n"
        f"#   python3 {script} remove-guard --repo <repo>\n"
        f"exec python3 '{script}' hook --config '{config_path}' \"$@\"\n"
    )


def is_ours(path):
    if not os.path.isfile(path):
        return False
    with open(path, "r", errors="replace") as handle:
        return MARKER in handle.read()


def install_guard(repo, protected, prefixes):
    hdir, common = hooks_dir(repo)
    os.makedirs(hdir, exist_ok=True)
    hook = os.path.join(hdir, "pre-push")
    backup = os.path.join(hdir, BACKUP_NAME)
    config_path = os.path.join(common, CONFIG_NAME)
    previous = None
    if os.path.exists(config_path):
        with open(config_path) as handle:
            previous = json.load(handle)
    if os.path.exists(hook) and not is_ours(hook):
        if os.path.exists(backup):
            return {"ok": False, "detail": f"refused: a foreign pre-push hook AND an old backup both exist ({backup}). Resolve by hand."}
        backup_sha = sha256_of(hook)
        os.rename(hook, backup)
    else:
        # Re-install over our own hook (an interrupted earlier run): keep the ORIGINAL backup record.
        backup_sha = previous.get("backup_sha256") if previous else None
    config = {"protected": protected, "protected_prefixes": prefixes, "backup_sha256": backup_sha}
    with open(config_path, "w") as handle:
        json.dump(config, handle, indent=2)
    with open(hook, "w") as handle:
        handle.write(hook_body(config_path))
    os.chmod(hook, 0o755)
    return {"ok": True, "detail": f"guard installed at {hook}", "backed_up": backup_sha is not None}


def remove_guard(repo):
    hdir, common = hooks_dir(repo)
    hook = os.path.join(hdir, "pre-push")
    backup = os.path.join(hdir, BACKUP_NAME)
    config_path = os.path.join(common, CONFIG_NAME)
    if os.path.exists(hook) and not is_ours(hook):
        return {"ok": False, "detail": "refused: the current pre-push hook is not the dark-factory guard. Not touching it."}
    expected = None
    if os.path.exists(config_path):
        with open(config_path) as handle:
            expected = json.load(handle).get("backup_sha256")
    if os.path.exists(hook):
        os.remove(hook)
    restored = False
    if os.path.exists(backup):
        if expected and sha256_of(backup) != expected:
            return {"ok": False, "detail": f"refused: backup {backup} does not match the recorded sha256. Left in place."}
        os.rename(backup, hook)
        restored = True
    if os.path.exists(config_path):
        os.remove(config_path)
    if restored and expected and sha256_of(hook) != expected:
        return {"ok": False, "detail": "restored hook does not match the recorded sha256"}
    return {"ok": True, "detail": "guard removed" + (", original hook restored byte-identical" if restored else ""), "restored": restored}


def status(repo):
    hdir, common = hooks_dir(repo)
    return {"ok": True, "guard_installed": is_ours(os.path.join(hdir, "pre-push")),
            "backup_present": os.path.exists(os.path.join(hdir, BACKUP_NAME)),
            "config_present": os.path.exists(os.path.join(common, CONFIG_NAME))}


# ---------------------------------------------------------------- the hook itself
def refusal(config, local_ref, local_sha, remote_ref, remote_sha):
    if local_sha == ZERO_SHA:
        return f"deleting {remote_ref} is not allowed during an unattended run"
    if remote_ref.startswith("refs/tags/"):
        return f"pushing tag {remote_ref} is not allowed during an unattended run"
    branch = remote_ref[len("refs/heads/"):] if remote_ref.startswith("refs/heads/") else remote_ref
    if branch in config.get("protected", []):
        return f"push to protected branch '{branch}' refused"
    for prefix in config.get("protected_prefixes", []):
        if prefix and branch.startswith(prefix):
            return f"push to '{branch}' refused (protected prefix '{prefix}')"
    if remote_sha != ZERO_SHA:
        known = subprocess.run(["git", "cat-file", "-e", remote_sha], capture_output=True, stdin=subprocess.DEVNULL).returncode == 0
        if not known:
            return f"remote tip {remote_sha[:12]} of '{branch}' is unknown locally; fetch first (cannot prove fast-forward)"
        ff = subprocess.run(["git", "merge-base", "--is-ancestor", remote_sha, local_sha], capture_output=True, stdin=subprocess.DEVNULL).returncode == 0
        if not ff:
            return f"non-fast-forward push to '{branch}' refused (history rewrite)"
    return None


def run_hook(config_path, stdin):
    with open(config_path) as handle:
        config = json.load(handle)
    problems = []
    for line in stdin.read().splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        reason = refusal(config, *parts)
        if reason:
            problems.append(reason)
    for p in problems:
        print(f"dark-factory guard: {p}", file=sys.stderr)
    return 1 if problems else 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--repo", required=True)
    p.add_argument("--min-free-gb", type=float, default=15.0)
    p.add_argument("--auth-smoke", action="store_true")
    p.add_argument("--no-fetch", action="store_true")
    i = sub.add_parser("install-guard")
    i.add_argument("--repo", required=True)
    i.add_argument("--protect", default=",".join(DEFAULT_PROTECTED))
    i.add_argument("--protect-prefix", action="append", default=[])
    r = sub.add_parser("remove-guard")
    r.add_argument("--repo", required=True)
    s = sub.add_parser("status")
    s.add_argument("--repo", required=True)
    h = sub.add_parser("hook")
    h.add_argument("--config", required=True)
    h.add_argument("rest", nargs="*")
    args = parser.parse_args(argv)

    if args.cmd == "hook":
        return run_hook(args.config, sys.stdin)
    try:
        if args.cmd == "preflight":
            out = preflight(args.repo, args.min_free_gb, args.auth_smoke, not args.no_fetch)
        elif args.cmd == "install-guard":
            protected = [b.strip() for b in args.protect.split(",") if b.strip()]
            out = install_guard(args.repo, protected, args.protect_prefix)
        elif args.cmd == "remove-guard":
            out = remove_guard(args.repo)
        else:
            out = status(args.repo)
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "detail": str(exc)}))
        return 2
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
