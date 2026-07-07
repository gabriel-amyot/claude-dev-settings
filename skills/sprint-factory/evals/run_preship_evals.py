#!/usr/bin/env python3
"""
run_preship_evals.py — deterministic eval suite for pre-ship-gate.sh.

pre-ship-gate.sh is the Dark Factory Phase 7 artifact gate: it HALTS shipping if the QA report,
review artifacts, execution_verified marker, or (for frontend tickets) screenshots are missing.
Each fixture builds a synthetic ticket directory in a temp dir and asserts the gate's exit code
(0 = PASS, 1 = HALT, 2 = usage/env error). Fixtures are self-contained; add a case here whenever
the gate's checks change or a new evasion is found.

Usage: python3 run_preship_evals.py [--script <path>]
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_SCRIPT = os.path.expanduser(
    "~/.claude-shared-config/skills/sprint-factory/resources/pre-ship-gate.sh")

LONG_QA_REPORT = "\n".join(f"QA finding line {i}" for i in range(1, 20)) + "\n"
SHORT_QA_REPORT = "QA report\nstub\n"
FRONTEND_AFFECTED_REPOS = '{"repos": [{"name": "app-front-portal", "type": "node/package.json"}]}'
BACKEND_AFFECTED_REPOS = '{"repos": [{"name": "app-proximity-report", "type": "java/maven"}]}'


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def base_ticket(root: Path, qa_report=LONG_QA_REPORT, review_files=("finding.md",),
                 exec_verified="true", affected_repos=None, screenshots=(), qa_review_note=None):
    """Build a baseline valid ticket dir, then let callers omit/break specific pieces."""
    if qa_report is not None:
        report_text = qa_report if qa_review_note is None else qa_report + f"\n{qa_review_note}\n"
        write(root / "qa" / "qa-report.v1.md", report_text)
    if review_files is not None:
        (root / "review").mkdir(parents=True, exist_ok=True)
        for f in review_files:
            write(root / "review" / f, "finding\n")
    else:
        (root / "review").mkdir(parents=True, exist_ok=True)
    if exec_verified == "OMIT":
        write(root / "pipeline-state.yaml", "phase: ship\n")
    elif exec_verified is not None:
        write(root / "pipeline-state.yaml", f"phase: ship\nexecution_verified: {exec_verified}\n")
    if affected_repos is not None:
        write(root / "analyst" / "affected_repos.v1.json", affected_repos)
    for s in screenshots:
        write(root / "design" / "screenshots" / s, "not-really-a-png")


# name -> (builder(root), expected_exit, needle_or_None, args_override_or_None)
def case_01(root):
    base_ticket(root)


def case_02(root):
    base_ticket(root, qa_report=None)


def case_03(root):
    base_ticket(root, qa_report=SHORT_QA_REPORT)


def case_04(root):
    base_ticket(root, review_files=None)
    import shutil
    shutil.rmtree(root / "review", ignore_errors=True)  # no review/ dir at all


def case_05(root):
    base_ticket(root, review_files=())  # review/ exists, empty


def case_06(root):
    base_ticket(root)
    (root / "pipeline-state.yaml").unlink(missing_ok=True)


def case_07(root):
    base_ticket(root, exec_verified="OMIT")


def case_08(root):
    base_ticket(root, affected_repos=FRONTEND_AFFECTED_REPOS)  # no screenshots, no note


def case_09(root):
    base_ticket(root, affected_repos=FRONTEND_AFFECTED_REPOS, screenshots=("ac1.png",))


def case_10(root):
    base_ticket(root, affected_repos=FRONTEND_AFFECTED_REPOS,
                qa_review_note="No UI change in this ticket — backend-only endpoint fix.")


def case_13(root):
    # Two QA report versions: v1 is a short stub, v2 is the real report. Gate must pick v2
    # (sort -V | tail -1), so this must PASS even though v1 alone would fail the length check.
    write(root / "qa" / "qa-report.v1.md", SHORT_QA_REPORT)
    write(root / "qa" / "qa-report.v2.md", LONG_QA_REPORT)
    base_ticket(root, qa_report=None)  # keep the rest of the baseline valid


CASES = {
    "01-happy-path-backend-only": (case_01, 0, "RESULT: PASS", None),
    "02-missing-qa-report": (case_02, 1, "no qa/qa-report.v*.md found", None),
    "03-empty-qa-report-stub": (case_03, 1, "looks empty/stub", None),
    "04-missing-review-dir": (case_04, 1, "no review/ directory", None),
    "05-empty-review-dir": (case_05, 1, "review/ exists but is empty", None),
    "06-missing-pipeline-state": (case_06, 1, "no pipeline-state.yaml", None),
    "07-pipeline-state-no-exec-verified": (case_07, 1, "no execution_verified", None),
    "08-frontend-no-screenshots-undocumented": (case_08, 1, "design/screenshots/ empty", None),
    "09-frontend-with-screenshots": (case_09, 0, "RESULT: PASS", None),
    "10-frontend-documented-no-ui-change": (case_10, 0, "RESULT: PASS", None),
    "11-usage-error-no-arg": (lambda root: None, 2, "no TICKET_DIR argument", []),
    "12-usage-error-dir-not-found": (lambda root: None, 2, "ticket directory not found", "__MISSING__"),
    "13-multiple-qa-reports-picks-latest": (case_13, 0, "qa-report.v2.md", None),
}


def run_case(script, name, builder, expected, needle, args_override):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / name
        root.mkdir(parents=True, exist_ok=True)
        builder(root)

        if args_override == []:
            argv = [script]
        elif args_override == "__MISSING__":
            argv = [script, str(root / "does-not-exist")]
        else:
            argv = [script, str(root)]

        proc = subprocess.run(argv, capture_output=True, text=True)
        output = proc.stdout + proc.stderr
        ok = proc.returncode == expected and (needle is None or needle.lower() in output.lower())
        return ok, proc.returncode, output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=DEFAULT_SCRIPT)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.script):
        print(f"gate script not found: {args.script}", file=sys.stderr)
        return 1

    failures = 0
    print(f"{'case':42} {'want':>4} {'got':>4}  result")
    print("-" * 66)
    for name, (builder, expected, needle, args_override) in CASES.items():
        ok, code, output = run_case(args.script, name, builder, expected, needle, args_override)
        print(f"{name:42} {expected:>4} {code:>4}  {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures += 1
            if needle and needle.lower() not in output.lower():
                print(f"    (missing expected output: {needle!r})")
        if args.verbose or not ok:
            for line in output.strip().splitlines()[:10]:
                print(f"    | {line}")

    total = len(CASES)
    print("-" * 66)
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
