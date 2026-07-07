#!/usr/bin/env python3
"""
run_link_evals.py — deterministic eval suite for validate_repo_links.py.

The script auto-detects a "workspace" by walking up from cwd looking for a project-management/
dir plus a workspace-specific marker dir (see workspaces.yaml). Each fixture builds a synthetic
workspace root in a temp dir matching the "supervisr-ai" workspace shape (detect: app/micro-
services) and runs the CLI with that dir as cwd, asserting the exit code and a substring of the
JSON output. Fixtures are self-contained; add a case here whenever a new subcommand or validation
rule is added.

PINNED BEHAVIOR (found while writing this suite, reported not fixed — see eval report):
`validate` returns exit 0 even when repo_links files ARE broken (missing path / bad key). The
top-level result dict only gets an "error" key when the workspace has ZERO .repo-links.yaml files
at all; a per-repo error just raises `repos_with_errors` / sets `overall_status: "invalid"` inside
an exit-0 payload. This suite pins that real behavior rather than asserting the "should fail"
version, since asserting the wrong thing would make the regression harness silently useless.

Usage: python3 run_link_evals.py [--script <path>]
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_SCRIPT = os.path.expanduser(
    "~/.claude-shared-config/skills/validate-repo-links/validate_repo_links.py")

GOOD_LINKS = """\
name: good-service
description: test fixture
infrastructure:
  dac:
    path: dac-dir
interactions: []
structure: []
"""

BROKEN_LINKS = """\
name: bad-service
description: test fixture
infrastructure:
  dac:
    path: nonexistent-dir
interactions: []
structure: []
"""

BAD_KEY_LINKS = """\
name: bad-key-service
description: test fixture
app_repo:
  path: nonexistent-app-repo
"""


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def build_workspace(tmp: Path) -> Path:
    """Minimal supervisr-ai-shaped workspace: project-management/ + app/micro-services/ (the
    workspace's 'detect' marker, also its scan_path for services)."""
    (tmp / "project-management").mkdir(parents=True, exist_ok=True)
    (tmp / "app" / "micro-services").mkdir(parents=True, exist_ok=True)
    return tmp


def case_valid_links(tmp):
    write(tmp / "app/micro-services/good-service/.repo-links.yaml", GOOD_LINKS)
    (tmp / "app/micro-services/good-service/dac-dir").mkdir(parents=True, exist_ok=True)


def case_broken_path(tmp):
    write(tmp / "app/micro-services/bad-service/.repo-links.yaml", BROKEN_LINKS)
    # dac-dir deliberately NOT created -> broken_dac_link


def case_bad_key(tmp):
    write(tmp / "app/micro-services/bad-key-service/.repo-links.yaml", BAD_KEY_LINKS)
    # app_repo.path deliberately not created -> broken_app_repo_link


def case_no_files(tmp):
    pass  # workspace exists but zero .repo-links.yaml anywhere


def case_malformed_yaml(tmp):
    write(tmp / "app/micro-services/broken-yaml-service/.repo-links.yaml",
          "name: [unclosed\n  bad: yaml: value\n")


def case_unknown_command(tmp):
    write(tmp / "app/micro-services/good-service/.repo-links.yaml", GOOD_LINKS)
    (tmp / "app/micro-services/good-service/dac-dir").mkdir(parents=True, exist_ok=True)


def case_reindex_no_files(tmp):
    pass


def case_reindex_then_visualize(tmp):
    write(tmp / "app/micro-services/good-service/.repo-links.yaml", GOOD_LINKS)
    (tmp / "app/micro-services/good-service/dac-dir").mkdir(parents=True, exist_ok=True)


def case_visualize_no_index(tmp):
    write(tmp / "app/micro-services/good-service/.repo-links.yaml", GOOD_LINKS)
    (tmp / "app/micro-services/good-service/dac-dir").mkdir(parents=True, exist_ok=True)
    # deliberately never run reindex first -> no .repo-index.yaml


def case_bootstrap_no_git_repos(tmp):
    pass  # bootstrap only scaffolds dirs that contain a .git/, none exist here


# name -> (builder(tmp), argv (list of extra args after script), expected_exit, needle, extra_check)
CASES = {
    "01-valid-links-exit-0": (case_valid_links, ["validate"], 0, '"overall_status": "valid"', None),
    "02-broken-path-still-exit-0-BUG": (
        case_broken_path, ["validate"], 0, '"overall_status": "invalid"', "broken_dac_link"),
    "03-bad-key-still-exit-0-BUG": (
        case_bad_key, ["validate"], 0, '"overall_status": "invalid"', "broken_app_repo_link"),
    "04-no-repo-links-files-exit-1": (
        case_no_files, ["validate"], 1, '"error"', "No .repo-links.yaml files found"),
    "05-malformed-yaml-no-crash-exit-0": (
        case_malformed_yaml, ["validate"], 0, "invalid_yaml", None),
    "06-unknown-command-exit-1": (
        case_unknown_command, ["frobnicate"], 1, "Unknown command", None),
    "07-reindex-no-files-exit-1": (
        case_reindex_no_files, ["reindex"], 1, '"error"', None),
    "08-reindex-then-list-services": (
        case_reindex_then_visualize, ["reindex"], 0, '"services_indexed": 1', None),
    "09-visualize-without-reindex-exit-1": (
        case_visualize_no_index, ["visualize"], 1, "Index file not found", None),
    "10-bootstrap-no-git-repos-exit-0": (
        case_bootstrap_no_git_repos, ["bootstrap"], 0, '"created": 0', None),
}


def run_case(script, name, builder, argv, expected, needle, extra_check):
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        build_workspace(tmp)
        builder(tmp)
        proc = subprocess.run(
            [sys.executable, script] + argv,
            capture_output=True, text=True, cwd=str(tmp))
        output = proc.stdout + proc.stderr
        ok = proc.returncode == expected
        if ok and needle is not None:
            ok = needle.lower() in output.lower()
        if ok and extra_check is not None:
            ok = extra_check.lower() in output.lower()
        return ok, proc.returncode, output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=DEFAULT_SCRIPT)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.script):
        print(f"script not found: {args.script}", file=sys.stderr)
        return 1

    failures = 0
    print(f"{'case':38} {'want':>4} {'got':>4}  result")
    print("-" * 62)
    for name, (builder, argv, expected, needle, extra_check) in CASES.items():
        ok, code, output = run_case(args.script, name, builder, argv, expected, needle, extra_check)
        print(f"{name:38} {expected:>4} {code:>4}  {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures += 1
        if args.verbose or not ok:
            for line in output.strip().splitlines()[:25]:
                print(f"    | {line}")

    total = len(CASES)
    print("-" * 62)
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
