#!/usr/bin/env python3
"""
run_trace_evals.py — deterministic eval suite for pipeline_trace_summarize.py.

pipeline_trace_summarize.py has zero existing test coverage (test_gitlab_skill.py
only covers trace_utils.py and gitlab_skill.py's safeguards/formatters/retry logic).
This suite fills that gap: it feeds synthetic GitLab CI trace logs to the actual
script via subprocess, then reads back the *_summary.yaml sidecar it writes and
pins the real emitted shape. Several fixtures pin known GAPS, not desired
behavior — see the "gap" comments and the dated eval report for detail.

Usage: python3 run_trace_evals.py [--script <path>] [-v]
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import os
import subprocess
import sys
import tempfile

import yaml

DEFAULT_SCRIPT = os.path.expanduser(
    "~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py")

SEC_START = "section_start:{ts}:{name}\r\x1b[0K\n"
SEC_END = "section_end:{ts}:{name}\r\x1b[0K\n"


def section(name, content, ts=1700000000):
    return SEC_START.format(ts=ts, name=name) + content + "\n" + SEC_END.format(ts=ts + 5, name=name)


# name -> (log text, check(dict) -> (bool, str))
FIXTURES = {}

FIXTURES["01-terraform-plan-stats"] = (
    section("env", "CI_JOB_STATUS=success\nCI_JOB_NAME=terraform-plan\nCI_PIPELINE_ID=98765\n"
                   "CI_ENVIRONMENT_NAME=dev\nCI_COMMIT_REF_NAME=dev\n"
                   "CI_PROJECT_PATH=grp/dac-gcp-back-proxrp\n")
    + section("terraform-plan", "Terraform will perform the following actions:\n\n"
              "  # module.cloud_run.google_cloud_run_service.svc will be updated in-place\n\n"
              "Plan: 3 to add, 1 to change, 2 to destroy.\n"),
    lambda s: (
        s.get("plan_add") == 3 and s.get("plan_change") == 1 and s.get("plan_destroy") == 2
        and "Destroy operations detected" in " ".join(s.get("warnings", [])),
        f"plan stats/warning mismatch: {s.get('plan_add')}/{s.get('plan_change')}/"
        f"{s.get('plan_destroy')}, warnings={s.get('warnings')}",
    ),
)

FIXTURES["02-terraform-state-lock"] = (
    section("env", "CI_JOB_NAME=terraform-apply\nCI_PIPELINE_ID=1111\n")
    + section("terraform-apply",
              "Acquiring state lock. This may take a few moments...\n"
              "Error: Error acquiring the state lock\n\n"
              "Lock Info:\n"
              "  ID:        7f3c9a21-88bb-4e11-9c0a-1a2b3c4d5e6f\n"
              "  Path:      gs://klever-tf-state/dac-gcp-back-proxrp/dev\n"),
    lambda s: (
        s.get("job_status") == "failed"
        and any(e.get("type") == "state_lock" for e in s.get("errors", []))
        and any(e.get("lock_id") == "7f3c9a21-88bb-4e11-9c0a-1a2b3c4d5e6f" for e in s.get("errors", [])),
        f"state_lock not classified correctly: {s.get('errors')}",
    ),
)

# GAP: "Error accessing remote module registry cicd.prod.datasophia.com" (the documented,
# recurring nightly outage in CLAUDE.md) matches none of the 4 ERROR_PATTERNS regexes.
# Pinning ACTUAL behavior: silently invisible — errors=[], job_status stays unknown.
# An agent piping this trace through the summarizer gets no signal to act on the
# "don't retry a known-down registry, it lasts hours" rule.
FIXTURES["03-registry-outage-gap"] = (
    section("env", "CI_JOB_NAME=terraform-init\nCI_PIPELINE_ID=2222\n")
    + section("terraform-init",
              "Initializing the backend...\nInitializing provider plugins...\n"
              "Error: Failed to install provider\n\n"
              "Error accessing remote module registry cicd.prod.datasophia.com: "
              "dial tcp: connect: connection refused\n"),
    lambda s: (
        s.get("errors") == [] and s.get("job_status") == "unknown",
        f"expected the documented gap (no classification): got errors={s.get('errors')} "
        f"job_status={s.get('job_status')} — if this now fires, update the pin AND tell "
        f"the registry-outage retry rule owner the signal exists.",
    ),
)

# GAP: no error pattern in this script targets app-repo build/test output at all —
# it is Terraform/DAC-specific. A Maven test failure produces zero signal.
FIXTURES["04-maven-test-failure-gap"] = (
    section("env", "CI_JOB_NAME=test\nCI_PIPELINE_ID=3333\nCI_PROJECT_PATH=grp/app-proximity-report\n")
    + section("test", "Running com.klever.proximity.service.ProximityServiceTest\n"
              "Tests run: 42, Failures: 1, Errors: 0, Skipped: 0\n"
              "FAILED: com.klever.proximity.service.ProximityServiceTest.testComputeRadius\n"
              "java.lang.AssertionError: expected:<12.0> but was:<0.0>\n"
              "BUILD FAILURE\n"),
    lambda s: (
        s.get("errors") == [] and s.get("job_status") == "unknown",
        f"expected the documented gap (Maven failure invisible): got errors={s.get('errors')} "
        f"job_status={s.get('job_status')}",
    ),
)

# GAP: same story for a Node/npm build failure.
FIXTURES["05-npm-build-failure-gap"] = (
    section("env", "CI_JOB_NAME=build\nCI_PIPELINE_ID=4444\nCI_PROJECT_PATH=grp/app-front-portal\n")
    + section("build", "> app-front-portal@1.4.2 build\n> next build\n\nFailed to compile.\n\n"
              "Module not found: Error: Can't resolve './FlowLines' in '/app/src/components'\n\n"
              "npm ERR! code ELIFECYCLE\nnpm ERR! errno 1\n"),
    lambda s: (
        s.get("errors") == [] and s.get("job_status") == "unknown",
        f"expected the documented gap (npm failure invisible): got errors={s.get('errors')} "
        f"job_status={s.get('job_status')}",
    ),
)

# GAP (fragility, not a live bug): pipeline_trace_summarize.py never imports trace_utils
# or strips ANSI, unlike gitlab_skill.py (which calls strip_ansi) and
# pipeline_trace_download.py (which strips ANSI with its own inline regex before writing
# the .log file). The ONLY real caller pre-strips, so production traces are safe today —
# but the script has zero defense of its own. Pinning: colorized "Plan:" line -> stats
# extraction silently fails, no error, no warning.
FIXTURES["06-ansi-color-coded-fragility"] = (
    section("env", "CI_JOB_NAME=terraform-plan\nCI_PIPELINE_ID=5555\n")
    + section("terraform-plan",
              "\x1b[1mTerraform will perform the following actions:\x1b[0m\n\n"
              "  \x1b[32m+\x1b[0m module.cloud_run.google_cloud_run_service.svc will be created\n\n"
              "\x1b[1mPlan: \x1b[32m3\x1b[0m to add, \x1b[33m1\x1b[0m to change, "
              "\x1b[31m2\x1b[0m to destroy.\x1b[0m\n"),
    lambda s: (
        "plan_add" not in s and s.get("warnings", []) == [],
        f"expected the documented ANSI fragility (no plan_add key, no destroy warning): "
        f"got plan_add={s.get('plan_add')!r} warnings={s.get('warnings')}",
    ),
)

FIXTURES["07-empty-trace"] = (
    "",
    lambda s: (
        s.get("errors") == [] and s.get("job_status") == "unknown" and s.get("auto_deploy") == "n/a",
        f"empty trace should degrade to safe defaults, no crash: {s}",
    ),
)

FIXTURES["08-truncated-trace"] = (
    "section_start:1700000000:terraform-plan\r\x1b[0K\n"
    "Terraform will perform the following actions:\n\n"
    "  # module.cloud_run.google_cloud_run_service.svc will be updated in-place\n\n"
    "Plan: 1 to add, 0 to chan",  # cut off mid-line, no section_end
    lambda s: (
        "plan_add" not in s and s.get("job_status") == "unknown",
        f"truncated trace should not crash and should not fabricate a plan count: {s}",
    ),
)

FIXTURES["09-precondition-412"] = (
    section("env", "CI_JOB_NAME=terraform-apply\nCI_PIPELINE_ID=6666\n")
    + section("terraform-apply",
              "Error: Error 412: Precondition Failed: object generation mismatch, "
              "pre-conditions not met for gs://klever-tf-state/dac-gcp-back-proexp/dev\n"),
    lambda s: (
        s.get("job_status") == "failed"
        and any(e.get("type") == "precondition_412" for e in s.get("errors", [])),
        f"precondition_412 not classified correctly: {s.get('errors')}",
    ),
)

FIXTURES["10-auto-deploy-blocked"] = (
    section("env", "CI_JOB_NAME=auto-deploy-gate\nCI_PIPELINE_ID=7777\nCI_ENVIRONMENT_NAME=dev\n")
    + section("auto-deploy-gate-check",
              "Checking plan for destructive changes before allowing auto-deploy...\n"
              "[ERROR] Destroy count > 0, manual approval required before apply\n")
    + section("terraform-plan", "Plan: 0 to add, 0 to change, 4 to destroy.\n"),
    lambda s: (
        s.get("auto_deploy") == "blocked"
        and "Destroy count > 0" in (s.get("auto_deploy_reason") or ""),
        f"auto_deploy gate not detected correctly: auto_deploy={s.get('auto_deploy')} "
        f"reason={s.get('auto_deploy_reason')!r}",
    ),
)

FIXTURES["11-manual-deploy-required"] = (
    section("terraform-apply",
            "Checking destroy count before apply...\n"
            "[ERROR] Run manual deploy via the pipeline UI: destroy count exceeds threshold\n"),
    lambda s: (
        s.get("job_status") == "failed"
        and any(e.get("type") == "manual_deploy_required" for e in s.get("errors", [])),
        f"manual_deploy_required not classified correctly: {s.get('errors')}",
    ),
)

FIXTURES["12-stuck-or-timeout"] = (
    section("terraform-apply",
            "Waiting for apply to complete...\n"
            "stuck_or_timeout_failure detected after 3600s, job will be marked failed\n"),
    lambda s: (
        s.get("job_status") == "failed"
        and any(e.get("type") == "stuck_or_timeout" for e in s.get("errors", [])),
        f"stuck_or_timeout not classified correctly: {s.get('errors')}",
    ),
)


def run_case(script, workdir, name, log_text):
    log_path = os.path.join(workdir, f"{name}.log")
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(log_text)
    proc = subprocess.run([sys.executable, script, log_path],
                          capture_output=True, text=True)
    summary_path = log_path.replace(".log", "") + "_summary.yaml"
    summary = None
    if os.path.exists(summary_path):
        with open(summary_path, encoding="utf-8") as fh:
            summary = yaml.safe_load(fh) or {}
    return proc, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=DEFAULT_SCRIPT)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.script):
        print(f"target script not found: {args.script}", file=sys.stderr)
        return 1

    failures = 0
    with tempfile.TemporaryDirectory() as workdir:
        print(f"{'case':38} {'crash?':>7}  result")
        print("-" * 62)
        for name, (log_text, check) in FIXTURES.items():
            proc, summary = run_case(args.script, workdir, name, log_text)
            crashed = proc.returncode != 0
            if crashed:
                ok, reason = False, f"script exited {proc.returncode}: {proc.stderr.strip()[:300]}"
            elif summary is None:
                ok, reason = False, "no summary yaml produced"
            else:
                ok, reason = check(summary)

            print(f"{name:38} {'yes' if crashed else 'no':>7}  {'PASS' if ok else 'FAIL'}")
            if not ok:
                failures += 1
                print(f"    (reason: {reason})")
            if args.verbose:
                print(f"    | summary: {summary}")

    total = len(FIXTURES)
    print("-" * 62)
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
