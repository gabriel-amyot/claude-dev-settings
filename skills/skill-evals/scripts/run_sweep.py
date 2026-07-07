#!/usr/bin/env python3
"""run_sweep.py — run every Layer A eval suite registered in evals/manifest.yaml.

Fast path only: deterministic fixture runners (seconds each, no model calls), so it is
safe for the unattended monthly launchd job. Layer B/B' suites are on-demand via the
/skill-evals skill and the skill-creator pipeline.

Behavior:
  - runs each suite's `runner` command (bash -c, 300s timeout)
  - writes a dated sweep report to evals/reports/
  - stamps `last_green` in the manifest for suites that passed
  - on any failure, writes a decision item to the Klever Mission Control inbox
    (inbox-writer schema) so it lands in Gabriel's queue

Usage: python3 run_sweep.py [--target NAME] [--source manual|monthly]
                            [--simulate-failure TARGET]   (schedule dry-run testing)
Exit 0 if all suites green, 1 otherwise.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

import yaml

SHARED = os.path.expanduser("~/.claude-shared-config")
MANIFEST = os.path.join(SHARED, "evals", "manifest.yaml")
REPORTS_DIR = os.path.join(SHARED, "evals", "reports")
INBOX_DIR = os.path.expanduser(
    "~/Developer/grp-beklever-com/project-management/general/user/inbox/decisions")
TIMEOUT = 300


def run_suite(suite):
    cmd = suite["runner"]
    try:
        proc = subprocess.run(["bash", "-c", cmd], capture_output=True,
                              text=True, timeout=TIMEOUT)
        return proc.returncode == 0, proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        return False, "timeout", f"runner exceeded {TIMEOUT}s: {cmd}"


def stamp_last_green(manifest_path, green_targets, today):
    """Line-scoped update of last_green inside each passing suite's block."""
    with open(manifest_path, encoding="utf-8") as fh:
        lines = fh.readlines()
    current = None
    for i, line in enumerate(lines):
        m = re.match(r"\s*-\s*target:\s*(.+?)\s*$", line)
        if m:
            current = m.group(1)
        elif re.match(r"\s*last_green:", line) and current in green_targets:
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = f"{indent}last_green: {today}\n"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)


def write_inbox_item(failures, report_path, today):
    os.makedirs(INBOX_DIR, exist_ok=True)
    seq = 1
    while True:
        slug = f"{today}-skill-evals-sweep-{seq:02d}"
        path = os.path.join(INBOX_DIR, slug + ".json")
        if not os.path.exists(path):
            break
        seq += 1
    body_lines = [
        f"The skill-evals Layer A sweep found **{len(failures)} failing suite(s)**.",
        "",
        "| Suite | Exit | First error line |",
        "|---|---|---|",
    ]
    for target, code, output in failures:
        first = next((l for l in output.strip().splitlines()
                      if "FAIL" in l or "!" in l or "Error" in l),
                     output.strip().splitlines()[0] if output.strip() else "")
        body_lines.append(f"| `{target}` | {code} | {first.strip()[:120]} |")
    body_lines += [
        "",
        f"Full report: `{os.path.relpath(report_path, os.path.expanduser('~'))}` "
        "(under home).",
        "",
        "A failing suite means either a real regression in the gate/script (fix the "
        "target) or an intentionally-pinned expectation that reality has diverged from "
        "(e.g. an unwired hook whose fixture asserts `expected_wired: true` — decide "
        "wiring or re-pin the fixture).",
    ]
    msg = {
        "id": slug,
        "type": "decision",
        "priority": "high",
        "title": f"Skill-evals sweep: {len(failures)} suite(s) failing",
        "ticket": "",
        "date": today,
        "author": "skill-evals",
        "estimate": "10 min",
        "status": "open",
        "body": "\n".join(body_lines),
        "questions": [
            {
                "text": "How should the failing suites be handled?",
                "type": "choice",
                "options": [
                    "Fix the regression in the target script/gate",
                    "Re-pin the fixture (behavior change was intentional)",
                    "Wire the hook (wiring-assertion failures)",
                ],
            }
        ],
        "files": [],
        "prompt": {
            "description": "Re-run the failing suites after the fix and confirm green.",
            "target_agent": "",
            "context_path": "",
            "instruction": "Invoke /skill-evals with --target for each failing suite; "
                           "if green, no further action.",
        },
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(msg, fh, indent=2)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", help="run a single suite by target name")
    ap.add_argument("--source", default="manual", choices=["manual", "monthly"])
    ap.add_argument("--simulate-failure", metavar="TARGET",
                    help="mark TARGET failed regardless of its result (dry-run testing)")
    args = ap.parse_args()

    with open(MANIFEST, encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    suites = [s for s in manifest.get("suites", []) if s.get("layer") == "A"]
    if args.target:
        suites = [s for s in suites if s["target"] == args.target]
        if not suites:
            print(f"no Layer A suite registered for target {args.target!r}",
                  file=sys.stderr)
            return 1

    today = datetime.date.today().isoformat()
    results = []
    for suite in suites:
        ok, code, output = run_suite(suite)
        if args.simulate_failure == suite["target"]:
            ok, code = False, "simulated"
            output = "(failure simulated via --simulate-failure)\n" + output
        results.append((suite["target"], ok, code, output))
        print(f"{'PASS' if ok else 'FAIL':4}  {suite['target']}  (exit {code})")

    failures = [(t, c, o) for t, ok, c, o in results if not ok]
    green = {t for t, ok, _, _ in results if ok}

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"{today}-sweep.md")
    with open(report_path, "a", encoding="utf-8") as fh:
        now = datetime.datetime.now().strftime("%H:%M")
        fh.write(f"\n# Layer A sweep — {today} {now} ({args.source})\n\n")
        fh.write(f"{len(results) - len(failures)}/{len(results)} suites green.\n\n")
        for target, ok, code, output in results:
            fh.write(f"## {'PASS' if ok else 'FAIL'} — {target} (exit {code})\n\n")
            if not ok:
                fh.write("```\n" + output.strip()[-3000:] + "\n```\n\n")
            else:
                tail = output.strip().splitlines()[-1] if output.strip() else ""
                fh.write(f"{tail}\n\n")

    if green and not args.target:
        stamp_last_green(MANIFEST, green, today)

    if failures:
        inbox_path = write_inbox_item(failures, report_path, today)
        print(f"\n{len(failures)} suite(s) FAILED — inbox item: {inbox_path}")
        print(f"report: {report_path}")
        return 1
    print(f"\nall {len(results)} suite(s) green — report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
