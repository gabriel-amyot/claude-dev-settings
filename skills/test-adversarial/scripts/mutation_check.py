#!/usr/bin/env python3
"""Mutation-check a fix: re-apply the shipped defect, prove the tests go red, restore byte-identical.

    mutation_check.py run --file <src> --find '<fixed expr>' --replace '<defect expr>' --test '<cmd>'
                          [--baseline '<cmd>'] [--count 1] [--cwd <dir>] [--out <result.json>] [--allow-dirty]
    mutation_check.py recover --file <src>

Procedure and triage: ../references/mutation-mode.md. One mutant per run. Several defect sites means
several runs.

Exit codes: 0 KILLED (and restored, and green again) | 1 SURVIVED | 2 refused (no change made) |
3 RESTORE FAILED (stop everything and run `recover`).

Guardrails, each one from a real incident (Klever SOP guard-test-validity-and-falsification.md):
- the substitution must change the text, exactly --count times (a silent no-op mutant reads as a pass);
- the suite must be green BEFORE the mutant, so a broken runner cannot pose as a kill;
- runner errors under the mutant (exit 126/127) are not kills;
- backup by shutil.copyfile, never `cp` (interactive cp strands the mutant);
- restore in `finally` and on SIGINT/SIGTERM, then verify sha256; a journal survives a hard kill;
- a file with uncommitted changes is refused unless --allow-dirty: run in a worktree, not on shared work.
"""
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys

RUNNER_ERRORS = {126, 127}


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def bump_mtime(path, seconds):
    # Bytecode and build caches key on (mtime, size). A same-size mutant written in the same second as
    # the cached original is silently ignored: the suite runs the ORIGINAL and the mutant "survives".
    # Found by this suite's first run (Python __pycache__). Force a distinct mtime on every write.
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + int(seconds * 1e9)))


def paths(src):
    return src + ".mutation-backup", src + ".mutation-journal.json"


def run_cmd(cmd, cwd):
    proc = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-15:]
    return proc.returncode, tail


def has_uncommitted(src):
    d = os.path.dirname(os.path.abspath(src))
    inside = subprocess.run(["git", "-C", d, "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    if inside.returncode != 0:
        return False
    st = subprocess.run(["git", "-C", d, "status", "--porcelain", "--", os.path.abspath(src)], capture_output=True, text=True)
    return st.stdout.strip() != ""


def restore(src):
    backup, journal = paths(src)
    if not os.path.exists(journal):
        return {"restored": False, "detail": "no journal: nothing to restore"}
    with open(journal) as handle:
        expected = json.load(handle)["original_sha256"]
    if not os.path.exists(backup):
        return {"restored": False, "detail": f"journal exists but backup {backup} is missing: restore by hand from git"}
    if sha(backup) != expected:
        return {"restored": False, "detail": "backup sha256 does not match the journal: restore by hand from git"}
    shutil.copyfile(backup, src)
    bump_mtime(src, 4)
    if sha(src) != expected:
        return {"restored": False, "detail": "file still differs after restore"}
    os.remove(backup)
    os.remove(journal)
    return {"restored": True, "detail": "restored byte-identical"}


def refuse(msg):
    print(json.dumps({"verdict": "REFUSED", "detail": msg}, indent=2))
    return 2


def run(a):
    src = os.path.abspath(a.file)
    cwd = a.cwd or os.getcwd()
    backup, journal = paths(src)
    if not os.path.isfile(src):
        return refuse(f"no such file: {src}")
    if os.path.exists(journal) or os.path.exists(backup):
        return refuse("a previous run was interrupted (journal or backup exists). Run: mutation_check.py recover --file " + src)
    if not a.allow_dirty and has_uncommitted(src):
        return refuse("the file has uncommitted changes. Commit, or run in a worktree, or pass --allow-dirty")
    with open(src, "rb") as handle:
        orig = handle.read()
    find, replace = a.find.encode(), a.replace.encode()
    occurrences = orig.count(find) if find else 0
    if occurrences != a.count:
        return refuse(f"--find occurs {occurrences} time(s), expected {a.count}: the mutant would be a no-op or ambiguous")
    mutant = orig.replace(find, replace, a.count)
    if mutant == orig:
        return refuse("the substitution does not change the file: a no-op mutant proves nothing")

    pre_rc, pre_tail = run_cmd(a.test, cwd)
    if pre_rc != 0:
        return refuse(f"the suite is not green before mutation (exit {pre_rc}); a red-before run cannot show a kill. Tail: {pre_tail[-3:]}")

    original_sha = sha(src)
    shutil.copyfile(src, backup)
    with open(journal, "w") as handle:
        json.dump({"file": src, "original_sha256": original_sha, "find": a.find, "replace": a.replace}, handle)

    def on_signal(signum, _frame):
        r = restore(src)
        print(json.dumps({"verdict": "INTERRUPTED", "signal": signum, "restore": r}), file=sys.stderr)
        sys.exit(3 if not r["restored"] else 130)

    old_int = signal.signal(signal.SIGINT, on_signal)
    old_term = signal.signal(signal.SIGTERM, on_signal)
    result = {"file": src, "find": a.find, "replace": a.replace}
    try:
        orig_mtime_ns = os.stat(backup).st_mtime_ns
        with open(src, "wb") as handle:
            handle.write(mutant)
        os.utime(src, ns=(os.stat(src).st_atime_ns, max(os.stat(src).st_mtime_ns, orig_mtime_ns) + 2_000_000_000))
        if sha(src) == original_sha:
            raise RuntimeError("mutant write did not change the file")
        rc, tail = run_cmd(a.test, cwd)
        result["mutant_exit"] = rc
        result["mutant_tail"] = tail
        if a.baseline:
            b_rc, b_tail = run_cmd(a.baseline, cwd)
            result["baseline_exit_under_mutant"] = b_rc
            result["baseline_tail"] = b_tail
    finally:
        r = restore(src)
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
        result["restore"] = r
    if not r["restored"]:
        result["verdict"] = "RESTORE_FAILED"
        print(json.dumps(result, indent=2))
        return 3

    post_rc, post_tail = run_cmd(a.test, cwd)
    result["post_restore_exit"] = post_rc
    notes = []
    if result["mutant_exit"] in RUNNER_ERRORS:
        verdict = "RUNNER_ERROR"
        notes.append("the test runner failed to start under the mutant; this is not a kill")
    elif result["mutant_exit"] != 0:
        verdict = "KILLED"
    else:
        verdict = "SURVIVED"
        notes.append("the suite does not detect this mutant. Read it before adding a test: either a test is "
                     "missing, or the production code is redundant/equivalent and the test is right to ignore it")
    if a.baseline and result.get("baseline_exit_under_mutant", 0) != 0:
        notes.append("the untouched-side baseline went RED under the mutant: the mutant is too broad or the test too coupled")
    if post_rc != 0:
        notes.append("the suite is not green after restore: investigate before trusting anything")
    result["verdict"] = verdict
    result["notes"] = notes
    if a.out:
        with open(a.out, "w") as handle:
            json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))
    if verdict == "KILLED" and post_rc == 0:
        return 0
    return 1


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--file", required=True)
    r.add_argument("--find", required=True)
    r.add_argument("--replace", required=True)
    r.add_argument("--test", required=True)
    r.add_argument("--baseline")
    r.add_argument("--count", type=int, default=1)
    r.add_argument("--cwd")
    r.add_argument("--out")
    r.add_argument("--allow-dirty", action="store_true")
    c = sub.add_parser("recover")
    c.add_argument("--file", required=True)
    a = p.parse_args(argv)
    if a.cmd == "recover":
        out = restore(os.path.abspath(a.file))
        print(json.dumps(out, indent=2))
        return 0 if out["restored"] else 3
    return run(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
