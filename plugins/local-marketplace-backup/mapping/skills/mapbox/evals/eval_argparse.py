#!/usr/bin/env python3
"""Offline argparse eval for manage_tilesets.py.

Exercises the list/status/replace CLI surface WITHOUT any real Mapbox calls
(no token, no network). We only verify the argument parser behaves:

  - `--help` for the top-level command and each subcommand exits 0.
  - Missing required args / unknown subcommands exit non-zero, and argparse
    emits a clean usage error (no Python traceback dumped to the user).

The script's module-level `from upload_tilesets import ...` only pulls stdlib
at import time (the `mapbox` SDK import is lazy, inside cmd_replace), so `--help`
parses fine with no extra dependencies. Any invocation that would reach a real
API call (e.g. a fully-formed `list`) is deliberately NOT run here, because that
needs a 1Password token and network — see EVAL.md for the live smoke checklist.

stdlib only. Run: python3 eval_argparse.py
"""

import os
import subprocess
import sys

SCRIPT = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "scripts",
        "manage_tilesets.py",
    )
)

PASS = "PASS"
FAIL = "FAIL"


def run(args):
    """Invoke the CLI as a subprocess; return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def has_traceback(text):
    return "Traceback (most recent call last)" in text


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    line = f"  [{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    return condition


def main():
    print(f"eval_argparse: manage_tilesets.py CLI surface")
    print(f"  script: {SCRIPT}\n")

    if not os.path.isfile(SCRIPT):
        print(f"  [{FAIL}] script not found at {SCRIPT}")
        sys.exit(1)

    results = []

    # --- help exits 0, no traceback -------------------------------------
    help_invocations = [
        ("top-level --help", ["--help"]),
        ("list --help", ["list", "--help"]),
        ("status --help", ["status", "--help"]),
        ("replace --help", ["replace", "--help"]),
    ]
    for name, args in help_invocations:
        rc, out, err = run(args)
        ok = check(
            f"{name} exits 0",
            rc == 0,
            f"returncode={rc}",
        )
        results.append(ok)
        clean = check(
            f"{name} no traceback",
            not has_traceback(out) and not has_traceback(err),
        )
        results.append(clean)

    # help text should actually mention the subcommand it documents
    rc, out, _ = run(["list", "--help"])
    results.append(
        check("list --help mentions --prefix", "--prefix" in out)
    )
    rc, out, _ = run(["status", "--help"])
    results.append(
        check("status --help mentions upload_id", "upload_id" in out)
    )
    rc, out, _ = run(["replace", "--help"])
    results.append(
        check("replace --help mentions --tileset-id", "--tileset-id" in out)
    )

    # --- bad args: non-zero, clean error, no traceback ------------------
    bad_invocations = [
        # No subcommand at all (subparser required=True -> error).
        ("no subcommand errors", []),
        # Unknown subcommand.
        ("unknown subcommand errors", ["frobnicate"]),
        # status requires a positional upload_id.
        ("status missing upload_id errors", ["status"]),
        # replace requires both the file positional and --tileset-id.
        ("replace missing file errors", ["replace"]),
        # replace given a file but no required --tileset-id.
        ("replace missing --tileset-id errors", ["replace", "some.mbtiles"]),
        # unknown flag on a valid subcommand.
        ("list unknown flag errors", ["list", "--bogus"]),
    ]
    for name, args in bad_invocations:
        rc, out, err = run(args)
        results.append(
            check(
                f"{name} (nonzero)",
                rc != 0,
                f"returncode={rc}",
            )
        )
        results.append(
            check(
                f"{name} (no traceback)",
                not has_traceback(out) and not has_traceback(err),
            )
        )

    print()
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"eval_argparse: {passed}/{total} checks passed")
    if passed != total:
        sys.exit(1)
    print("RESULT: PASS (offline argparse only; live API untested — see EVAL.md)")


if __name__ == "__main__":
    main()
