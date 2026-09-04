#!/usr/bin/env python3
"""
Eval suite for normalize_geoid.py (mapping:crosswalk skill).

Deterministic, stdlib-only. Drives the script via its CLI (subprocess) so the
argparse wiring, --level handling, and stdin batch path are all exercised
end to end, exactly as a caller would invoke them.

Covers:
  - to_db:    tileset -> db, idempotency, whitespace tolerance, leading-zero FIPS
  - to_tileset: county/state/zcta level prefixing, idempotency
  - round-trip: db -> tileset -> db == db (stability)
  - stdin batch mode
  - error: --to-tileset without --level fails nonzero
  - the script's own --self-test passes

Run:  python3 eval_normalize.py
Exit: 0 = all pass, nonzero = at least one failure (count of failures).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "normalize_geoid.py")

failures = []
checks = 0


def run(args, stdin=None):
    """Invoke the CLI. Returns (returncode, stdout_stripped, stderr)."""
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args],
        input=stdin,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr


def expect(label, got, want):
    global checks
    checks += 1
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def expect_rc(label, got_rc, want_zero):
    global checks
    checks += 1
    is_zero = got_rc == 0
    if is_zero != want_zero:
        failures.append(
            f"{label}: returncode {got_rc} (expected {'0' if want_zero else 'nonzero'})"
        )


# --- to_db: tileset form -> db form ---
for inp, want in [
    ("0500000US53033", "53033"),      # county tileset -> db
    ("53033", "53033"),               # idempotent (already db)
    ("0400000US53", "53"),            # state tileset -> db
    ("8600000US90210", "90210"),      # zcta tileset -> db
    ("  0500000US36061  ", "36061"),  # whitespace tolerated
    ("0500000US06037", "06037"),      # leading-zero FIPS preserved
]:
    rc, out, err = run(["--to-db", inp])
    expect_rc(f"to_db rc {inp!r}", rc, True)
    expect(f"to_db {inp!r}", out, want)

# --- to_tileset: db form -> tileset form, per level ---
for inp, level, want in [
    ("53033", "county", "0500000US53033"),
    ("53", "state", "0400000US53"),
    ("90210", "zcta", "8600000US90210"),
    ("0500000US53033", "county", "0500000US53033"),  # idempotent
    ("06037", "county", "0500000US06037"),           # leading zero preserved
]:
    rc, out, err = run(["--to-tileset", inp, "--level", level])
    expect_rc(f"to_tileset rc {inp!r}/{level}", rc, True)
    expect(f"to_tileset {inp!r}/{level}", out, want)

# --- round-trip stability: db -> tileset -> db == db ---
for db, level in [("53033", "county"), ("53", "state"), ("90210", "zcta"),
                  ("06037", "county")]:
    _, tileset, _ = run(["--to-tileset", db, "--level", level])
    rc, back, _ = run(["--to-db", tileset])
    expect_rc(f"round-trip rc {db}/{level}", rc, True)
    expect(f"round-trip {db}/{level}", back, db)

# --- stdin batch mode (one geoid per line) ---
rc, out, err = run(["--to-db"], stdin="0500000US53033\n0400000US53\n90210\n")
expect_rc("stdin batch rc", rc, True)
expect("stdin batch", out, "53033\n53\n90210")

# --- error path: --to-tileset without --level must fail nonzero ---
rc, _, _ = run(["--to-tileset", "53033"])
expect_rc("to_tileset missing --level", rc, False)

# --- error path: unknown level must fail nonzero (argparse choices) ---
rc, _, _ = run(["--to-tileset", "53033", "--level", "tract"])
expect_rc("to_tileset bad level", rc, False)

# --- the script's own self-test must pass ---
rc, _, _ = run(["--self-test"])
expect_rc("script --self-test", rc, True)


if failures:
    print(f"FAIL: {len(failures)}/{checks} checks failed", file=sys.stderr)
    for f in failures:
        print("  - " + f, file=sys.stderr)
    sys.exit(len(failures))

print(f"PASS: {checks} normalization checks")
sys.exit(0)
