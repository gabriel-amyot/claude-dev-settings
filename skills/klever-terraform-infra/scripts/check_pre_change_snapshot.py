#!/usr/bin/env python3
"""Static check: does every stateful MIG wait for a pre-change snapshot?

Terraform does not run locally in Klever repos (the pipeline injects the provider, the
backend and the utility modules). So this reads the HCL text. It checks the shape of the
pattern in references/stateful-mig-pre-change-snapshot.md:

  1. google_compute_snapshot.pre_change exists, with a source_disk and storage_locations.
  2. Its name is derived from an instance template, so a template change replaces it and
     an unchanged template leaves it alone.
  3. It has lifecycle { create_before_destroy = true }.
  4. Every MIG with a stateful_disk block has depends_on = [google_compute_snapshot.pre_change].

Usage: check_pre_change_snapshot.py <terraform-dir>
Exit: 0 pattern holds, 1 a check failed, 2 bad input, 3 no stateful MIG (not applicable).
It proves shape only. The pipeline plan proves the replacement order.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RESOURCE_HEADER = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"([A-Za-z0-9_-]+)"\s*\{')
MIG_TYPES = {"google_compute_instance_group_manager", "google_compute_region_instance_group_manager"}
SNAPSHOT_REF = "google_compute_snapshot.pre_change"
TEMPLATE_REF = re.compile(r"google_compute_(region_)?instance_template\.")


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"(?m)(^|\s)(#|//).*$", r"\1", text)


def blocks(text: str) -> list[tuple[str, str, str]]:
    found = []
    for match in RESOURCE_HEADER.finditer(text):
        depth, index = 1, match.end()
        while index < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[index], 0)
            index += 1
        found.append((match.group(1), match.group(2), text[match.end():index - 1]))
    return found


def attribute(body: str, name: str) -> str | None:
    match = re.search(rf"(?m)^\s*{name}\s*=\s*(.+)$", body)
    return match.group(1).strip() if match else None


def check(directory: Path) -> tuple[int, list[str]]:
    text = "\n".join(strip_comments(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.tf")))
    resources = blocks(text)
    migs = [(t, n, b) for t, n, b in resources if t in MIG_TYPES and re.search(r"\bstateful_disk\s*\{", b)]
    if not migs:
        return 3, ["no MIG with a stateful_disk block; the pattern does not apply"]

    problems = []
    snapshots = [b for t, n, b in resources if t == "google_compute_snapshot" and n == "pre_change"]
    if not snapshots:
        problems.append(f"missing resource {SNAPSHOT_REF}")
    else:
        body = snapshots[0]
        name = attribute(body, "name") or ""
        if not TEMPLATE_REF.search(name):
            problems.append("pre_change name does not derive from the instance template; "
                            "a template change would not replace the snapshot")
        if not re.search(r"\blifecycle\s*\{[^}]*create_before_destroy\s*=\s*true", body, re.DOTALL):
            problems.append("pre_change lacks lifecycle { create_before_destroy = true }")
        if attribute(body, "source_disk") is None:
            problems.append("pre_change has no source_disk")
        if attribute(body, "storage_locations") is None:
            problems.append("pre_change has no storage_locations")

    for mig_type, mig_name, body in migs:
        depends = re.search(r"\bdepends_on\s*=\s*\[([^\]]*)\]", body, re.DOTALL)
        if not depends or SNAPSHOT_REF not in depends.group(1):
            problems.append(f"{mig_type}.{mig_name} does not depend_on {SNAPSHOT_REF}")
    return (1 if problems else 0), problems


def main() -> int:
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_dir():
        print("usage: check_pre_change_snapshot.py <terraform-dir>")
        return 2
    code, messages = check(Path(sys.argv[1]))
    label = {0: "PASS", 1: "FAIL", 3: "NOT APPLICABLE"}[code]
    print(f"{label}: pre-change snapshot pattern")
    for message in messages:
        print(f"  - {message}")
    return code


if __name__ == "__main__":
    sys.exit(main())
