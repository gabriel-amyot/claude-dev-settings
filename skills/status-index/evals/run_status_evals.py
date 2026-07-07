#!/usr/bin/env python3
"""
run_status_evals.py — deterministic eval suite for status_index.py.

status_index.py generates STATUS_SNAPSHOT.yaml from jira/ac/index.yaml (acceptance-criteria-
weighted completion). Each fixture builds a synthetic project-management/tickets/ tree in a temp
dir and runs the script with --dry-run (which prints the would-be YAML instead of writing it),
asserting the exit code and, where useful, a substring of the printed YAML. Fixtures are self-
contained; add a case here whenever the completion math or snapshot shape changes.

Usage: python3 run_status_evals.py [--script <path>]
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_SCRIPT = os.path.expanduser(
    "~/.claude-shared-config/skills/status-index/status_index.py")


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def ac_yaml(done, total, points=1, title="Sample ticket"):
    lines = [f"title: {title}", "story_points: 3", "criteria:"]
    for i in range(1, total + 1):
        status = "done" if i <= done else "not_started"
        lines.append(f"  - id: AC-{i}")
        lines.append(f"    description: criterion {i}")
        lines.append(f"    points: {points}")
        lines.append(f"    status: {status}")
    return "\n".join(lines) + "\n"


def build_pm_root(tmp: Path) -> Path:
    """Every case runs with cwd = tmp (parent of project-management), per
    get_project_management_root()'s walk-up-from-cwd logic."""
    pm = tmp / "project-management"
    pm.mkdir(parents=True, exist_ok=True)
    return pm


# --- fixtures ---

def case_2of5(pm):
    write(pm / "tickets/KTP/no-epic/KTP-9001/jira/ac/index.yaml", ac_yaml(2, 5))


def case_0of5(pm):
    write(pm / "tickets/KTP/no-epic/KTP-9001/jira/ac/index.yaml", ac_yaml(0, 5))


def case_5of5(pm):
    write(pm / "tickets/KTP/no-epic/KTP-9001/jira/ac/index.yaml", ac_yaml(5, 5))


def case_missing_ac_yaml(pm):
    (pm / "tickets/KTP/no-epic/KTP-9001").mkdir(parents=True, exist_ok=True)
    # jira/ac/index.yaml deliberately absent


def case_malformed_yaml(pm):
    write(pm / "tickets/KTP/no-epic/KTP-9001/jira/ac/index.yaml",
          "title: [unclosed\n  bad: yaml: value\n")


def case_nonexistent_ticket(pm):
    # No ticket dir created at all; we point the CLI at a path that doesn't exist.
    pass


def case_epic_weighted(pm):
    # Epic with two leaf children: one 100% (2sp), one 0% (1sp) -> weighted completion 66.7.
    write(pm / "tickets/KTP/KTP-9100/KTP-9101/jira/ac/index.yaml", ac_yaml(2, 2, title="Child A"))
    child_a = pm / "tickets/KTP/KTP-9100/KTP-9101/jira/ac/index.yaml"
    # story_points is hardcoded to 3 by ac_yaml(); override per-child for a clean weighted calc.
    child_a.write_text(child_a.read_text().replace("story_points: 3", "story_points: 2"))
    write(pm / "tickets/KTP/KTP-9100/KTP-9102/jira/ac/index.yaml", ac_yaml(0, 2, title="Child B"))
    child_b = pm / "tickets/KTP/KTP-9100/KTP-9102/jira/ac/index.yaml"
    child_b.write_text(child_b.read_text().replace("story_points: 3", "story_points: 1"))


TICKET_ARG = {
    "01-two-of-five-done": "KTP/no-epic/KTP-9001",
    "02-zero-of-five-done": "KTP/no-epic/KTP-9001",
    "03-five-of-five-done": "KTP/no-epic/KTP-9001",
    "04-missing-ac-yaml-no-crash": "KTP/no-epic/KTP-9001",
    "05-malformed-yaml-no-crash": "KTP/no-epic/KTP-9001",
    "06-nonexistent-ticket-path": "KTP/no-epic/KTP-9999",
    "07-epic-weighted-completion": "KTP/KTP-9100",
}

# name -> (builder(pm_root), expected_exit, needle_or_None)
CASES = {
    "01-two-of-five-done": (case_2of5, 0, "completion: 40.0"),
    "02-zero-of-five-done": (case_0of5, 0, "completion: 0.0"),
    "03-five-of-five-done": (case_5of5, 0, "completion: 100.0"),
    "04-missing-ac-yaml-no-crash": (case_missing_ac_yaml, 0, "completion: 0.0"),
    "05-malformed-yaml-no-crash": (case_malformed_yaml, 0, "completion: 0.0"),
    "06-nonexistent-ticket-path": (case_nonexistent_ticket, 1, "not found"),
    "07-epic-weighted-completion": (case_epic_weighted, 0, "completion: 66.7"),
}


def run_case(script, name, builder, expected, needle):
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        pm = build_pm_root(tmp)
        builder(pm)
        ticket_arg = TICKET_ARG[name]
        proc = subprocess.run(
            [sys.executable, script, ticket_arg, "--dry-run"],
            capture_output=True, text=True, cwd=str(tmp))
        output = proc.stdout + proc.stderr
        ok = proc.returncode == expected and (needle is None or needle.lower() in output.lower())
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
    print(f"{'case':32} {'want':>4} {'got':>4}  result")
    print("-" * 56)
    for name, (builder, expected, needle) in CASES.items():
        ok, code, output = run_case(args.script, name, builder, expected, needle)
        print(f"{name:32} {expected:>4} {code:>4}  {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures += 1
            if needle and needle.lower() not in output.lower():
                print(f"    (missing expected output: {needle!r})")
        if args.verbose or not ok:
            for line in output.strip().splitlines()[:20]:
                print(f"    | {line}")

    total = len(CASES)
    print("-" * 56)
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
