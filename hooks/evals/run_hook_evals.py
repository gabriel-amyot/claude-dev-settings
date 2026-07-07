#!/usr/bin/env python3
"""run_hook_evals.py — deterministic eval runner for Claude Code hooks.

Each hook gets a fixture file at fixtures/<hook-name>.yaml. The runner pipes the
fixture's stdin JSON to the hook exactly as the harness would, then asserts on exit
code and output needles. Fixtures are permanent regressions: whenever a red-team pass
or a real incident finds an evasion or false positive, encode it here.

Fixture file schema (YAML):

    hook: external-post-gate.sh        # path relative to the hooks dir, or absolute
    wired:                             # optional wiring assertion against settings.json
      event: PreToolUse                # hook event to look under
      expected: true                   # true = must be registered; false = must not be
      note: "pending PCE handoff"      # shown when the assertion fails
    cases:
      - name: 01-descriptive-name
        stdin: {tool_input: {command: "..."}}   # JSON piped to the hook
        # stdin_raw: "not-json"                 # alternative: raw stdin string
        expected_exit: 2
        needle: "must appear in stdout+stderr"  # optional, case-insensitive
        absent: "must NOT appear"               # optional, case-insensitive
        env: {KEY: "value"}                     # optional env overrides
        cwd: "{tmp}"                            # optional working dir
        files: {rel/path.md: "content"}         # materialized under the case tmp dir
        repos: {work: code-repo}                # hydrate bundle 'code-repo' at {repo:work}
        setup: "shell command"                  # runs before the hook (sh -c)
        teardown: "shell command"               # runs after, even on failure

Placeholders substituted in stdin values, env values, cwd, files content, needle,
setup and teardown: {tmp} (per-case temp dir), {hooks_dir}, {home}, {repo:<alias>}.

Usage: python3 run_hook_evals.py [--hook <name>] [--fixtures-dir <dir>] [-v]
Exit 0 if all cases (and wiring assertions) pass, 1 otherwise.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS_DIR = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")
SETTINGS = os.path.expanduser("~/.claude/settings.json")

sys.path.insert(0, HERE)
import gitfixtures  # noqa: E402


def substitute(value, subs):
    if isinstance(value, str):
        for key, repl in subs.items():
            value = value.replace(key, repl)
        return value
    if isinstance(value, dict):
        return {k: substitute(v, subs) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, subs) for v in value]
    return value


def hook_command(path):
    """Invoke the hook the way the harness would: by shebang."""
    with open(path, encoding="utf-8") as fh:
        first = fh.readline().strip()
    if first.startswith("#!"):
        interp = first[2:].split()
        if interp and interp[0].endswith("env"):
            return interp[1:] + [path]
        return interp + [path]
    return ["bash", path]


def run_case(hook_path, case, verbose):
    name = case["name"]
    with tempfile.TemporaryDirectory() as tmp:
        subs = {"{tmp}": tmp, "{hooks_dir}": HOOKS_DIR,
                "{home}": os.path.expanduser("~")}
        for alias, bundle in (case.get("repos") or {}).items():
            dest = os.path.join(tmp, alias)
            gitfixtures.hydrate(bundle, dest)
            subs["{repo:%s}" % alias] = dest

        for rel, content in (case.get("files") or {}).items():
            target = os.path.join(tmp, substitute(rel, subs))
            os.makedirs(os.path.dirname(target) or tmp, exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(substitute(content, subs))

        env = dict(os.environ)
        env.update({k: substitute(str(v), subs)
                    for k, v in (case.get("env") or {}).items()})
        cwd = substitute(case.get("cwd") or tmp, subs)

        if case.get("stdin_raw") is not None:
            stdin_data = substitute(case["stdin_raw"], subs)
        else:
            stdin_data = json.dumps(substitute(case.get("stdin") or {}, subs))

        try:
            if case.get("setup"):
                subprocess.run(["sh", "-c", substitute(case["setup"], subs)],
                               cwd=cwd, env=env, check=True, capture_output=True)
            proc = subprocess.run(hook_command(hook_path), input=stdin_data,
                                  capture_output=True, text=True, cwd=cwd,
                                  env=env, timeout=60)
        finally:
            if case.get("teardown"):
                subprocess.run(["sh", "-c", substitute(case["teardown"], subs)],
                               cwd=cwd, env=env, capture_output=True)

        output = proc.stdout + proc.stderr
        expected = case.get("expected_exit", 0)
        needle = case.get("needle")
        absent = case.get("absent")
        if needle:
            needle = substitute(needle, subs)
        problems = []
        if proc.returncode != expected:
            problems.append(f"exit {proc.returncode}, wanted {expected}")
        if needle and needle.lower() not in output.lower():
            problems.append(f"missing needle {needle!r}")
        if absent and substitute(absent, subs).lower() in output.lower():
            problems.append(f"forbidden output {absent!r} present")
        return problems, proc.returncode, output


def check_wiring(hook_path, wired):
    """Assert the hook's registration state in ~/.claude/settings.json."""
    basename = os.path.basename(hook_path)
    registered = False
    try:
        with open(SETTINGS, encoding="utf-8") as fh:
            settings = json.load(fh)
        for rule in settings.get("hooks", {}).get(wired["event"], []):
            for entry in rule.get("hooks", []):
                if basename in entry.get("command", ""):
                    registered = True
    except Exception as exc:  # settings unreadable = wiring unknown = fail
        return [f"could not read settings.json: {exc}"], registered
    expected = bool(wired.get("expected", True))
    if registered != expected:
        note = wired.get("note", "")
        want = "registered" if expected else "NOT registered"
        got = "registered" if registered else "not registered"
        msg = f"wiring: expected {want} under {wired['event']}, found {got}"
        if note:
            msg += f" ({note})"
        return [msg], registered
    return [], registered


def run_fixture_file(path, verbose):
    with open(path, encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    hook_path = spec["hook"]
    if not os.path.isabs(hook_path):
        hook_path = os.path.join(HOOKS_DIR, hook_path)
    label = os.path.basename(path).replace(".yaml", "")
    print(f"\n=== {label} → {os.path.basename(hook_path)} ===")
    if not os.path.exists(hook_path):
        print(f"  FAIL hook script not found: {hook_path}")
        return 1, 1

    failures = 0
    total = 0
    for case in spec.get("cases") or []:
        total += 1
        try:
            problems, code, output = run_case(hook_path, case, verbose)
        except Exception as exc:
            problems, code, output = [f"runner error: {exc}"], "?", ""
        status = "PASS" if not problems else "FAIL"
        print(f"  {case['name']:44} exit={code!s:>3}  {status}")
        if problems:
            failures += 1
            for p in problems:
                print(f"      ! {p}")
        if verbose or problems:
            for line in output.strip().splitlines()[:6]:
                print(f"      | {line}")

    if spec.get("wired"):
        total += 1
        problems, _ = check_wiring(hook_path, spec["wired"])
        status = "PASS" if not problems else "FAIL"
        print(f"  {'wiring-assertion':44} {'':>8}  {status}")
        if problems:
            failures += 1
            for p in problems:
                print(f"      ! {p}")
    return failures, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hook", help="run only fixtures/<hook>.yaml")
    ap.add_argument("--fixtures-dir", default=FIXTURES_DIR)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.hook:
        paths = [os.path.join(args.fixtures_dir, args.hook + ".yaml")]
        if not os.path.exists(paths[0]):
            print(f"no fixture file: {paths[0]}", file=sys.stderr)
            return 1
    else:
        paths = sorted(glob.glob(os.path.join(args.fixtures_dir, "*.yaml")))
        if not paths:
            print(f"no fixture files in {args.fixtures_dir}", file=sys.stderr)
            return 1

    failures = total = 0
    for path in paths:
        f, t = run_fixture_file(path, args.verbose)
        failures += f
        total += t
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
