#!/usr/bin/env python3
"""Layer A suite for scripts/headless_launch_guard.py. Real git repos in a temp dir, real `git push`
through the installed hook. Run: `python3 tests/headless_launch_guard_test.py`. Exit 1 on any failure.

Pins: launch-time preflight fails closed (hook manager, dirty checkout, project-management cwd, low disk),
the guard blocks protected refs / tags / deletes / non-fast-forward / protected prefixes, and the guard
lifecycle restores a pre-existing hook byte-identical, including after an interrupted double install.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "headless_launch_guard.py")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")

passed = 0
failed = 0


def ok(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {name} {detail}", file=sys.stderr)


def sh(cwd, *args):
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL)


def guard(*args):
    proc = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL)
    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        out = {"raw": proc.stdout}
    return proc.returncode, out


def make_repo(root, name="app"):
    remote = os.path.join(root, name + ".git")
    work = os.path.join(root, name)
    sh(root, "git", "init", "--bare", "-b", "main", remote)
    sh(root, "git", "clone", remote, work)
    sh(work, "git", "checkout", "-b", "main")
    with open(os.path.join(work, "a.txt"), "w") as f:
        f.write("one\n")
    sh(work, "git", "add", "a.txt")
    sh(work, "git", "commit", "-m", "init")
    sh(work, "git", "push", "origin", "main")
    sh(work, "git", "push", "origin", "main:dev")
    return work


def commit(work, text):
    with open(os.path.join(work, "a.txt"), "a") as f:
        f.write(text + "\n")
    sh(work, "git", "commit", "-am", text)


with tempfile.TemporaryDirectory() as root:
    work = make_repo(root)

    # ---- preflight ----
    code, out = guard("preflight", "--repo", work, "--min-free-gb", "0.001")
    ok("P1 clean repo passes preflight", code == 0 and out.get("ok") is True, json.dumps(out)[:400])
    ok("P2 preflight emits workflow args for the substrate gate",
       out.get("workflow_args", {}).get("cwd") == os.path.abspath(work) and isinstance(out.get("workflow_args", {}).get("free_disk_gb"), float))
    code, out = guard("preflight", "--repo", work, "--min-free-gb", "999999", "--no-fetch")
    ok("P3 disk floor above free space fails closed", code == 1 and any(c["check"] == "free_disk" and not c["ok"] for c in out["checks"]))
    sh(work, "git", "config", "core.hooksPath", ".githooks")
    code, out = guard("preflight", "--repo", work, "--min-free-gb", "0.001", "--no-fetch")
    ok("P4 a hook manager (core.hooksPath) fails closed", code == 1 and any(c["check"] == "no_hooks_path" and not c["ok"] for c in out["checks"]))
    sh(work, "git", "config", "--unset", "core.hooksPath")
    with open(os.path.join(work, "a.txt"), "a") as f:
        f.write("dirty\n")
    code, out = guard("preflight", "--repo", work, "--min-free-gb", "0.001", "--no-fetch")
    ok("P5 a dirty main checkout fails closed", code == 1 and any(c["check"] == "clean_main_checkout" and not c["ok"] for c in out["checks"]))
    sh(work, "git", "checkout", "--", "a.txt")
    pm = os.path.join(root, "project-management")
    os.makedirs(pm)
    sh(pm, "git", "init", "-b", "main")
    code, out = guard("preflight", "--repo", pm, "--min-free-gb", "0.001", "--no-fetch")
    ok("P6 a project-management cwd fails closed", code == 1 and any(c["check"] == "not_project_management" and not c["ok"] for c in out["checks"]))
    code, out = guard("preflight", "--repo", os.path.join(root, "nope"), "--no-fetch")
    ok("P7 a missing repo path fails closed, no crash", code == 1 and out.get("ok") is False)

    # ---- guard lifecycle with a pre-existing foreign hook ----
    hook = os.path.join(work, ".git", "hooks", "pre-push")
    original = "#!/bin/sh\n# someone else's hook\nexit 0\n"
    with open(hook, "w") as f:
        f.write(original)
    os.chmod(hook, 0o755)
    code, out = guard("install-guard", "--repo", work, "--protect-prefix", "KTP-1216-spike-")
    ok("G1 install backs up a foreign hook", code == 0 and out.get("backed_up") is True)
    code, out = guard("install-guard", "--repo", work, "--protect-prefix", "KTP-1216-spike-")
    ok("G2 a second install (interrupted re-run) is idempotent", code == 0)
    code, st = guard("status", "--repo", work)
    ok("G3 status sees the guard and the backup", st.get("guard_installed") is True and st.get("backup_present") is True)

    # ---- the hook, through real git push ----
    sh(work, "git", "checkout", "-b", "KTP-1-feature")
    commit(work, "feature")
    r = sh(work, "git", "push", "origin", "KTP-1-feature")
    ok("H1 feature branch push is allowed", r.returncode == 0, r.stderr)
    r = sh(work, "git", "push", "origin", "KTP-1-feature:dev")
    ok("H2 push to dev is refused", r.returncode != 0 and "protected branch 'dev'" in r.stderr, r.stderr)
    r = sh(work, "git", "push", "origin", "KTP-1-feature:main")
    ok("H3 push to main is refused", r.returncode != 0 and "protected branch 'main'" in r.stderr, r.stderr)
    sh(work, "git", "tag", "v9.9.9")
    r = sh(work, "git", "push", "origin", "v9.9.9")
    ok("H4 tag push is refused", r.returncode != 0 and "tag" in r.stderr, r.stderr)
    r = sh(work, "git", "push", "origin", "KTP-1-feature:KTP-1216-spike-client-view")
    ok("H5 protected prefix is refused", r.returncode != 0 and "protected prefix" in r.stderr, r.stderr)
    sh(work, "git", "reset", "--hard", "HEAD~1")
    commit(work, "rewritten")
    r = sh(work, "git", "push", "--force", "origin", "KTP-1-feature")
    ok("H6 non-fast-forward force push is refused", r.returncode != 0 and "non-fast-forward" in r.stderr, r.stderr)
    r = sh(work, "git", "push", "origin", "--delete", "KTP-1-feature")
    ok("H7 branch delete is refused", r.returncode != 0 and "deleting" in r.stderr, r.stderr)

    # ---- removal restores the original byte-identical ----
    code, out = guard("remove-guard", "--repo", work)
    ok("G4 remove restores the original hook", code == 0 and out.get("restored") is True, json.dumps(out))
    with open(hook) as f:
        ok("G5 restored hook is byte-identical", f.read() == original)
    code, st = guard("status", "--repo", work)
    ok("G6 nothing of the guard is left", st.get("guard_installed") is False and st.get("backup_present") is False and st.get("config_present") is False)
    code, out = guard("remove-guard", "--repo", work)
    ok("G7 remove on a foreign hook refuses and leaves it", code == 1 and open(hook).read() == original)
    os.remove(hook)
    code, out = guard("remove-guard", "--repo", work)
    ok("G8 remove when nothing is installed is a clean no-op", code == 0 and out.get("restored") is False)

    # ---- tampered backup is never restored silently ----
    with open(hook, "w") as f:
        f.write(original)
    guard("install-guard", "--repo", work)
    with open(os.path.join(work, ".git", "hooks", "pre-push.dark-factory-backup"), "a") as f:
        f.write("# tampered\n")
    code, out = guard("remove-guard", "--repo", work)
    ok("G9 a backup whose sha256 changed is refused, not restored", code == 1 and "does not match" in out.get("detail", ""))

print(f"headless-launch-guard: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
