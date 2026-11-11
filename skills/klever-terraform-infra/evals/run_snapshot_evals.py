#!/usr/bin/env python3
"""Layer A suite for scripts/check_pre_change_snapshot.py.

Origin: Proxi DAC MR !48 (KTP-853). A stateful COS MIG recreate needed a manual snapshot
(Rule 0). The Terraform-native fix only works if three details are all right: the name
follows the template, create_before_destroy is set, and the MIG waits for the snapshot.
Each case removes one of them.

Run:  python3 run_snapshot_evals.py [-v]
Exit: 0 all green, 1 any failure
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_pre_change_snapshot.py"
VERBOSE = "-v" in sys.argv
RESULTS: list[tuple[str, bool, str]] = []

TEMPLATE = '''
resource "google_compute_region_instance_template" "cos" {
  for_each    = local.templates
  name_prefix = "proxi-"
}
'''

SNAPSHOT = '''
resource "google_compute_snapshot" "pre_change" {
  name              = "proxi-pre-change-${substr(sha1(join(",", sort([for t in google_compute_region_instance_template.cos : t.id]))), 0, 12)}"
  source_disk       = "cos-proxi-16n4-1"
  zone              = "us-east1-b"
  storage_locations = ["us-east1"]

  lifecycle {
    create_before_destroy = true
  }
}
'''

MIG = '''
resource "google_compute_region_instance_group_manager" "cos" {
  name = "proxi"
  stateful_disk {
    device_name = "hermes-data"
    delete_rule = "NEVER"
  }
  depends_on = [google_compute_snapshot.pre_change]
}
'''


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))
    if VERBOSE or not condition:
        print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not condition else ""))


def run_case(name: str, files: dict[str, str], expected_code: int, needle: str = "") -> None:
    root = Path(tempfile.mkdtemp(prefix="snapshot-eval-"))
    try:
        for filename, text in files.items():
            (root / filename).write_text(text, encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)
        check(f"{name}:exit {expected_code}", result.returncode == expected_code, result.stdout + result.stderr)
        if needle:
            check(f"{name}:names the defect", needle in result.stdout, result.stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    if not SCRIPT.exists():
        print(f"FATAL: {SCRIPT} missing. NOT-RUN, not a pass.")
        return 1
    run_case("complete pattern", {"template.tf": TEMPLATE, "snapshot.tf": SNAPSHOT, "mig.tf": MIG}, 0)
    run_case("no stateful MIG", {"template.tf": TEMPLATE,
                                  "mig.tf": MIG.replace('stateful_disk {\n    device_name = "hermes-data"\n    delete_rule = "NEVER"\n  }\n', "")}, 3)
    run_case("snapshot missing", {"template.tf": TEMPLATE, "mig.tf": MIG}, 1, "missing resource")
    run_case("static name never replaces", {"template.tf": TEMPLATE, "mig.tf": MIG,
             "snapshot.tf": SNAPSHOT.replace(SNAPSHOT.split('name              = ')[1].split("\n")[0], '"proxi-pre-change"')},
             1, "does not derive from the instance template")
    run_case("no create_before_destroy", {"template.tf": TEMPLATE, "mig.tf": MIG,
             "snapshot.tf": SNAPSHOT.replace("create_before_destroy = true", "prevent_destroy = false")},
             1, "create_before_destroy")
    run_case("commented-out lifecycle does not count", {"template.tf": TEMPLATE, "mig.tf": MIG,
             "snapshot.tf": SNAPSHOT.replace("    create_before_destroy = true", "    # create_before_destroy = true")},
             1, "create_before_destroy")
    run_case("MIG does not wait", {"template.tf": TEMPLATE, "snapshot.tf": SNAPSHOT,
             "mig.tf": MIG.replace("  depends_on = [google_compute_snapshot.pre_change]\n", "")},
             1, "does not depend_on")
    run_case("no storage location", {"template.tf": TEMPLATE, "mig.tf": MIG,
             "snapshot.tf": SNAPSHOT.replace('  storage_locations = ["us-east1"]\n', "")},
             1, "storage_locations")

    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    print(f"pre-change snapshot evals: {len(RESULTS) - len(failed)}/{len(RESULTS)} assertions passed")
    for name, detail in failed:
        print(f"  - {name}\n      {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
