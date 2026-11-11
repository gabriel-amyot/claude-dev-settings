#!/usr/bin/env python3
"""dac-env-gate.py — container env parity between the two portal DACs, and dead-var detection.

Two DACs deploy the same app-front-portal image: dac-gcp-front-klv1ai (804) and the legacy
dac-gcp-front-portal (514, prod still live). They share no git history, so an env var added to
one is easy to forget in the other. A removed app read leaves dead config behind (KTP-1333:
MEDIA_PLAN_ATTACH_EXCEL stayed "false" in klv1ai prod for 8 days after the portal stopped reading it).

Env names are read from terraform/*.tf at a git ref: `{ name = "X", value = ... }` entries.

Modes:
  parity       a DAC MR. Names the MR adds that the sibling DAC lacks -> BLOCK, unless --ack NAME.
               Names the MR removes that the sibling still sets -> advisory.
               --app <portal repo> adds the dead-var advisory (names with zero readers).
  app-removal  an app-front-portal MR. Env reads the MR removes -> every DAC that still sets
               the name gets an ACTION line (a removal MR). Advisory, exit 0.

Usage:
  dac-env-gate.py parity --dac <path> --sibling <path> [--base origin/dev] [--head HEAD]
                         [--sibling-ref origin/dev] [--ack NAME ...] [--app <path>]
  dac-env-gate.py app-removal --app <path> --dac <path> [--dac <path> ...]
                         [--base origin/dev] [--head HEAD] [--dac-ref origin/dev]

Exit: 0 pass or advisory only, 1 BLOCK, 2 usage, 3 CANT_VERIFY.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ENV_ENTRY = re.compile(r'\{\s*name\s*=\s*"([A-Z][A-Z0-9_]*)"\s*,\s*value\s*=')
APP_READ = re.compile(r'(?:process\.)?\benv(?:\.|\[\s*["\'])([A-Z][A-Z0-9_]*)')
DEFAULT_CONTROL = "KLEVER_USER_MANAGEMENT_URL"
APP_REFS = ("origin/main", "origin/dev")


class CantVerify(Exception):
    pass


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r


def dac_env_names(dac, ref):
    ls = git(dac, "ls-tree", "-r", "--name-only", ref, "--", "terraform")
    if ls.returncode != 0:
        raise CantVerify(f"{dac} @ {ref}: {ls.stderr.strip()}")
    names = set()
    for path in ls.stdout.split():
        if path.endswith(".tf"):
            names.update(ENV_ENTRY.findall(git(dac, "show", f"{ref}:{path}").stdout))
    return names


def app_reads(app, ref):
    r = git(app, "grep", "-h", "-o", "-E", r"(process\.)?env(\.|\[[\"'])[A-Z][A-Z0-9_]*", ref,
            "--", ".", ":!*.md", ":!node_modules")
    if r.returncode not in (0, 1):
        raise CantVerify(f"{app} @ {ref}: {r.stderr.strip()}")
    return set(APP_READ.findall(r.stdout))


def reader_count(app, ref, name):
    r = git(app, "grep", "-c", "-w", name, ref, "--", ".", ":!*.md")
    if r.returncode not in (0, 1):
        raise CantVerify(f"{app} @ {ref}: {r.stderr.strip()}")
    return sum(int(line.rsplit(":", 1)[1]) for line in r.stdout.splitlines() if ":" in line)


def dead_vars(app, names, control):
    for ref in APP_REFS:
        if reader_count(app, ref, control) == 0:
            raise CantVerify(f"positive control {control} has zero readers at {ref}; the reader search is broken")
    return sorted(n for n in names if all(reader_count(app, ref, n) == 0 for ref in APP_REFS))


def parity(a):
    base = dac_env_names(a.dac, a.base)
    head = dac_env_names(a.dac, a.head)
    sibling = dac_env_names(a.sibling, a.sibling_ref)
    added, removed = head - base, base - head
    acked = set(a.ack or [])
    blocking = sorted(added - sibling - acked)
    name, sib = Path(a.dac).name, Path(a.sibling).name

    print(f"DAC {name}: +{len(added)} -{len(removed)} env name(s) vs {a.base}")
    for n in sorted(added & acked - sibling):
        print(f"ACKED: {n} is only in {name} (author recorded why the sibling does not need it)")
    for n in blocking:
        print(f"BLOCK: {n} is added to {name} but {sib} does not set it. If the app treats it as "
              f"required, open the {sib} MR first. If not, re-run with --ack {n} and record why in the MR.")
    for n in sorted(removed & sibling):
        print(f"ADVISORY: {n} is removed here but {sib} still sets it. Open a removal MR there if the app no longer reads it.")
    drift = sorted((head ^ sibling) - added - removed)
    if drift:
        print(f"INFO: pre-existing asymmetry with {sib} (not this MR): {', '.join(drift)}")
    if a.app:
        for n in dead_vars(a.app, head | sibling, a.control):
            print(f"CLEANUP CANDIDATE: {n} has zero readers in {Path(a.app).name} at {' and '.join(APP_REFS)}. "
                  "Before removal, check launchers and build scripts outside the repo, and open feature "
                  "branches that may read it before they merge.")
    print("REMINDER: a prod image tag bump must be done in BOTH DAC projects' TF_VAR_build_docker_tag_version.")
    print("RESULT: BLOCK" if blocking else "RESULT: PASS")
    return 1 if blocking else 0


def app_removal(a):
    gone = app_reads(a.app, a.base) - app_reads(a.app, a.head)
    actions = 0
    for n in sorted(gone):
        if reader_count(a.app, a.head, n) > 0:
            print(f"INFO: {n} lost a direct env read but the name is still referenced at {a.head}; no action")
            continue
        for dac in a.dac:
            if n in dac_env_names(dac, a.dac_ref):
                actions += 1
                print(f"ACTION: {n} is no longer read by the app, but {Path(dac).name} still sets it. Open a removal MR there.")
    print(f"RESULT: {actions} removal MR(s) needed" if actions else "RESULT: no DAC still sets a removed env read")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("parity")
    p.add_argument("--dac", required=True)
    p.add_argument("--sibling", required=True)
    p.add_argument("--base", default="origin/dev")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--sibling-ref", default="origin/dev")
    p.add_argument("--ack", action="append")
    p.add_argument("--app")
    p.add_argument("--control", default=DEFAULT_CONTROL)
    r = sub.add_parser("app-removal")
    r.add_argument("--app", required=True)
    r.add_argument("--dac", action="append", required=True)
    r.add_argument("--base", default="origin/dev")
    r.add_argument("--head", default="HEAD")
    r.add_argument("--dac-ref", default="origin/dev")
    a = ap.parse_args()
    try:
        return parity(a) if a.mode == "parity" else app_removal(a)
    except CantVerify as exc:
        print(f"CANT_VERIFY: {exc}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
