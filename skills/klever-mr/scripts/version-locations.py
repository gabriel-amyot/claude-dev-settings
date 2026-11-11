#!/usr/bin/env python3
"""version-locations.py — Gate 4 helper: find every location that carries the release version.

A Klever app's release identity can live in more than one file. The version file
(pom.xml, package.json, pyproject.toml) names the Docker tag. On a FaaS zip-artifact repo,
DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION in .gitlab-ci.yml names the uploaded zip. When the
two disagree, the dev pipeline tries to overwrite a published artifact and fails with
`403 ... storage.objects.delete` (KTP-920).

Only variables proven to carry the release identity count. The rule is explicit: a
.gitlab-ci.yml variable named DATASOPHIA_INCL_*_TAG_VERSION with a semver literal value.
Other semver-valued variables (UV_VERSION, tool pins) are listed as ignored and never edited.

Usage:
  version-locations.py --repo <path> [--ref <git-ref>]     # report, exit 1 on disagreement
  version-locations.py --repo <path> --sync                # set CI release vars to the version file

Exit: 0 all locations agree (or no release location), 1 disagreement, 2 usage,
      3 CANT_VERIFY (a release CI variable exists but the version file cannot be read).
"""
import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

CI_FILE = ".gitlab-ci.yml"
SEMVER = r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?"
CI_VAR_LINE = re.compile(
    r"^(?P<indent>\s*)(?P<name>[A-Z][A-Z0-9_]*)\s*:\s*(?P<quote>[\"']?)(?P<value>" + SEMVER + r")(?P=quote)\s*(?:#.*)?$")
RELEASE_VAR = re.compile(r"^DATASOPHIA_INCL_[A-Z0-9_]*_TAG_VERSION$")


def read(repo, ref, path):
    if ref:
        r = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    p = Path(repo) / path
    return p.read_text() if p.exists() else None


def pom_version(text):
    root = ET.fromstring(text)
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    node = root.find(f"{ns}version")
    return node.text.strip() if node is not None and node.text else None


def pyproject_version(text):
    if tomllib is None:
        m = re.search(r'^\[project\][^\[]*?^version\s*=\s*"([^"]+)"', text, re.M | re.S)
        return m.group(1) if m else None
    data = tomllib.loads(text)
    return data.get("project", {}).get("version") or data.get("tool", {}).get("poetry", {}).get("version")


def version_file(repo, ref):
    for path, parse in (("pom.xml", pom_version),
                        ("package.json", lambda t: json.loads(t).get("version")),
                        ("pyproject.toml", pyproject_version)):
        text = read(repo, ref, path)
        if text is None:
            continue
        try:
            return path, parse(text)
        except Exception as exc:  # unparseable file is a CANT_VERIFY, not a pass
            return path, f"UNPARSEABLE: {exc}"
    return None, None


def ci_locations(text):
    release, ignored = [], []
    for lineno, line in enumerate((text or "").splitlines(), 1):
        m = CI_VAR_LINE.match(line)
        if not m:
            continue
        entry = (lineno, m.group("name"), m.group("value"))
        (release if RELEASE_VAR.match(m.group("name")) else ignored).append(entry)
    return release, ignored


def sync(repo, target, release):
    path = Path(repo) / CI_FILE
    lines = path.read_text().splitlines(keepends=True)
    changed = []
    for lineno, name, value in release:
        if value == target:
            continue
        line = lines[lineno - 1]
        lines[lineno - 1] = line.replace(value, target, 1)
        changed.append(f"{CI_FILE}:{name} {value} -> {target}")
    path.write_text("".join(lines))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref")
    ap.add_argument("--sync", action="store_true")
    a = ap.parse_args()
    if a.sync and a.ref:
        print("--sync edits the working tree; do not pass --ref", file=sys.stderr)
        return 2

    vpath, version = version_file(a.repo, a.ref)
    release, ignored = ci_locations(read(a.repo, a.ref, CI_FILE))

    print(f"version file: {vpath or 'none'} = {version or '-'}")
    for lineno, name, value in release:
        print(f"release var:  {CI_FILE}:{lineno} {name} = {value}")
    for lineno, name, value in ignored:
        print(f"ignored:      {CI_FILE}:{lineno} {name} = {value} (not a release identity)")

    if not release:
        print("RESULT: OK (no CI release variable; the version file is the only location)")
        return 0
    if not version or str(version).startswith("UNPARSEABLE"):
        print("RESULT: CANT_VERIFY (a CI release variable exists but the version file is unreadable)")
        return 3

    mismatched = [r for r in release if r[2] != version]
    if not mismatched:
        print(f"RESULT: OK ({1 + len(release)} locations agree on {version})")
        return 0
    if a.sync:
        changed = sync(a.repo, version, release)
        print(f"RESULT: SYNCED {len(changed)} location(s) to {version}: " + "; ".join(changed))
        return 0
    for _, name, value in mismatched:
        print(f"MISMATCH: {CI_FILE}:{name} = {value}, version file {vpath} = {version}")
    print("RESULT: MISMATCH (run with --sync after the version-file bump)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
