#!/usr/bin/env python3
"""run_interpreter_evals.py: the gitlab scripts must run when python3 has no `requests`.

Regression for 2026-10/11: Homebrew moved python3 to a version without site
packages, and every `python3 gitlab_skill.py ...` call failed with
`ModuleNotFoundError: No module named 'requests'`.

`python3 -S` turns off site-packages, so `requests` is absent on any host. That
makes the cases deterministic. Stdlib only. Needs `uv` on PATH.

Usage: python3 run_interpreter_evals.py [--skill-dir DIR] [-v]
Exit 0 when all cases pass, 1 otherwise.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

DEFAULT_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEP_SCRIPTS = ("gitlab_skill.py", "pipeline_trace_download.py", "pipeline_trace_summarize.py")
DOCS = ("SKILL.md", "QUICK_REFERENCE.md", "README.md")
PLAIN_PYTHON_CALL = re.compile(r"python3\s+\S*(gitlab_skill|pipeline_trace_download|pipeline_trace_summarize)\.py")


def run(cmd, env_extra=None):
    env = dict(os.environ)
    env.pop("GITLAB_SKILL_UV_REEXEC", None)
    env.update(env_extra or {})
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env, cwd="/tmp")


def case_plain_python_reexecs(skill_dir):
    out = run([sys.executable, "-S", os.path.join(skill_dir, "gitlab_skill.py"), "--help"])
    ok = out.returncode == 0 and "recent" in out.stdout and "api" in out.stdout
    return ok, f"rc={out.returncode} stderr={out.stderr.strip()[-160:]}"


def case_loop_guard_holds(skill_dir):
    out = run([sys.executable, "-S", os.path.join(skill_dir, "gitlab_skill.py"), "--help"],
              env_extra={"GITLAB_SKILL_UV_REEXEC": "1"})
    ok = out.returncode != 0 and "No module named 'requests'" in out.stderr
    return ok, f"rc={out.returncode}"


def case_trace_download_reexecs(skill_dir):
    out = run([sys.executable, "-S", os.path.join(skill_dir, "pipeline_trace_download.py"), "--help"])
    return out.returncode == 0 and "usage" in out.stdout.lower(), f"rc={out.returncode} stderr={out.stderr.strip()[-160:]}"


def case_inline_metadata_present(skill_dir):
    missing = []
    for name in DEP_SCRIPTS:
        with open(os.path.join(skill_dir, name), encoding="utf-8") as fh:
            head = fh.read(400)
        if "# /// script" not in head or "dependencies" not in head:
            missing.append(name)
    return not missing, f"missing PEP 723 header: {missing}" if missing else "ok"


def case_docs_use_uv(skill_dir):
    offenders = []
    for name in DOCS:
        path = os.path.join(skill_dir, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if PLAIN_PYTHON_CALL.search(line):
                    offenders.append(f"{name}:{lineno}")
    return not offenders, f"plain python3 calls: {offenders[:5]}" if offenders else "ok"


CASES = [
    ("01-plain-python3-without-requests-reexecs-under-uv", case_plain_python_reexecs),
    ("02-reexec-loop-guard", case_loop_guard_holds),
    ("03-trace-download-reexecs-under-uv", case_trace_download_reexecs),
    ("04-pep723-header-on-dependency-scripts", case_inline_metadata_present),
    ("05-docs-invoke-with-uv-run", case_docs_use_uv),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", default=DEFAULT_SKILL_DIR)
    parser.add_argument("-v", action="store_true")
    args = parser.parse_args()
    if not shutil.which("uv"):
        print("FAIL: uv is not on PATH")
        return 1
    failed = 0
    for name, fn in CASES:
        ok, detail = fn(args.skill_dir)
        failed += 0 if ok else 1
        print(f"{name:<55} {'PASS' if ok else 'FAIL'}" + (f"  {detail}" if args.v or not ok else ""))
    print("-" * 62)
    print(f"{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
