#!/usr/bin/env python3
"""
Eval suite for lookup_crosswalk.py (mapping:crosswalk skill).

Deterministic, stdlib-only. Drives the script via its CLI (subprocess) against
fixtures/fsa_to_cd_sample.csv, which matches the KTP-679 schema:
  CFSAUID,CDUID,PRUID,CDNAME,PRNAME

Known fixtures asserted: M5V->3520, H2X->2466, V6B->5915 (plus T2P->4806, K1P->3506,
and M5H->3520 so reverse CD 3520 -> {M5V,M5H} exercises distinct dedup).

Covers:
  - forward lookup (CFSAUID -> CDUID), the three known anchors
  - reverse lookup (CDUID -> CFSAUID) with multiple distinct results, deduped
  - JSON output: full matched row(s), schema fields present
  - stdin batch (multiple keys)
  - no-match: nonzero exit, empty stdout value list
  - column validation: bad --from column fails nonzero

Run:  python3 eval_lookup.py
Exit: 0 = all pass, nonzero = number of failed checks.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "lookup_crosswalk.py")
TABLE = os.path.join(HERE, "fixtures", "fsa_to_cd_sample.csv")

failures = []
checks = 0


def run(args, stdin=None):
    proc = subprocess.run(
        [sys.executable, SCRIPT, "--table", TABLE, *args],
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


def expect_true(label, cond):
    global checks
    checks += 1
    if not cond:
        failures.append(label)


# --- forward lookup: CFSAUID -> CDUID (the three known anchors) ---
for fsa, cd in [("M5V", "3520"), ("H2X", "2466"), ("V6B", "5915"),
                ("T2P", "4806"), ("K1P", "3506")]:
    rc, out, err = run(["--from", "CFSAUID", "--to", "CDUID", "--key", fsa])
    expect_rc(f"forward rc {fsa}", rc, True)
    expect(f"forward {fsa}->CDUID", out, cd)

# --- reverse lookup: CDUID -> CFSAUID, distinct + deduped ---
rc, out, err = run(["--from", "CDUID", "--to", "CFSAUID", "--key", "3520"])
expect_rc("reverse 3520 rc", rc, True)
# fixture order: M5V appears before M5H; both map to 3520, distinct preserved
expect("reverse 3520->CFSAUID", out, "M5V\nM5H")

# --- JSON output: full matched row(s) with all schema fields ---
rc, out, err = run(["--from", "CFSAUID", "--key", "M5V", "--json"])
expect_rc("json M5V rc", rc, True)
try:
    rows = json.loads(out)
    expect_true("json M5V is single-row list", isinstance(rows, list) and len(rows) == 1)
    row = rows[0]
    expect("json M5V CDUID", row.get("CDUID"), "3520")
    expect("json M5V PRUID", row.get("PRUID"), "35")
    expect("json M5V CDNAME", row.get("CDNAME"), "Toronto")
    expect("json M5V PRNAME", row.get("PRNAME"), "Ontario")
    expect_true(
        "json M5V has full schema",
        set(row.keys()) == {"CFSAUID", "CDUID", "PRUID", "CDNAME", "PRNAME"},
    )
except (ValueError, IndexError) as e:
    failures.append(f"json M5V parse failed: {e}; raw={out!r}")
    checks += 1

# --- stdin batch (multiple keys, one per line) ---
rc, out, err = run(["--from", "CFSAUID", "--to", "CDUID"], stdin="M5V\nH2X\nV6B\n")
expect_rc("stdin batch rc", rc, True)
expect("stdin batch", out, "3520\n2466\n5915")

# --- no-match: nonzero exit, empty stdout value list ---
rc, out, err = run(["--from", "CFSAUID", "--to", "CDUID", "--key", "Z9Z"])
expect_rc("no-match exits nonzero", rc, False)
expect("no-match emits nothing on stdout", out, "")
expect_true("no-match notes on stderr", "no match" in err.lower())

# --- no-match in JSON mode: nonzero exit, empty JSON array on stdout ---
rc, out, err = run(["--from", "CFSAUID", "--key", "Z9Z", "--json"])
expect_rc("no-match json exits nonzero", rc, False)
expect("no-match json emits []", out, "[]")

# --- column validation: unknown --from column fails nonzero ---
rc, _, _ = run(["--from", "NOPE", "--to", "CDUID", "--key", "M5V"])
expect_rc("bad from-column fails", rc, False)


if failures:
    print(f"FAIL: {len(failures)}/{checks} checks failed", file=sys.stderr)
    for f in failures:
        print("  - " + f, file=sys.stderr)
    sys.exit(len(failures))

print(f"PASS: {checks} lookup checks")
sys.exit(0)
