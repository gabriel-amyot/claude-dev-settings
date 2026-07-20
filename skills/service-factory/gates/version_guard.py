#!/usr/bin/env python3
"""Version guard — the version↔improvement + no-drift gate (Law 5).

The self-improvement loop had no mechanical link to a version, and the spec
lived outside the skill (two copies drift). This gate closes both, mirroring
dark-factory's carried-spec + CHANGELOG discipline — but as an un-skippable
check, true to this line's "narrated ≠ done" ethos.

Two laws, one gate (see docs/spec/laws-of-execution.md §Law 5):

  1. VERSION COUPLING — SKILL.md `version:` frontmatter MUST match the top
     version entry in CHANGELOG.md. Every change to the line bumps both, so the
     link between a self-improvement and the version it landed in cannot be
     skipped: you cannot change the skill without a changelog entry, nor add a
     changelog version without bumping the skill.
  2. NO DRIFT — the authoritative spec MUST be carried inside the skill
     (docs/spec/service-factory-spec-*.md exists; SKILL.md `spec_source` points
     at a real local file), AND the authoritative spec surface (SKILL.md +
     docs/spec/) MUST NOT reference an external copy (session-retros /
     project-management). A second live copy of a spec drifts; this forbids the
     tether that would create one.

  python3 version_guard.py <skill-dir>
  exit 0 = pass (version disciplined, spec self-contained); 1 = reject
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_SEMVER = re.compile(r"^\d+\.\d+\.\d+")
_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_CHANGELOG_VER = re.compile(r"^##\s+(\d+\.\d+\.\d+)", re.MULTILINE)

# "session-retros" never legitimately appears in the spec surface. In docs/spec
# we also forbid a bare "project-management" (SKILL.md's `when_not` legitimately
# says "project-management repo (never)" as a scope rule, so it is scanned only
# for the retro-folder tether).
_FORBIDDEN_SKILL_MD = ("session-retros", "reports/session-retros")
_FORBIDDEN_SPEC = ("session-retros", "project-management")


def _read(p: Path) -> str:
    return p.read_text() if p.exists() else ""


def _frontmatter(skill_md_text: str) -> dict:
    m = _FRONTMATTER.match(skill_md_text)
    if not m or yaml is None:
        return {}
    data = yaml.safe_load(m.group(1))
    return data if isinstance(data, dict) else {}


def _changelog_top_version(text: str):
    m = _CHANGELOG_VER.search(text)
    return m.group(1) if m else None


def check(skill_dir) -> dict:
    d = Path(skill_dir)
    reasons = []

    skill_md = _read(d / "SKILL.md")
    if not skill_md:
        return {"pass": False, "reasons": ["SKILL.md missing"]}

    fm = _frontmatter(skill_md)
    version = str(fm.get("version") or "").strip()
    spec_source = str(fm.get("spec_source") or "").strip()

    # 1 — version is semver
    if not version:
        reasons.append("SKILL.md frontmatter has no `version:`")
    elif not _SEMVER.match(version):
        reasons.append(f"SKILL.md version '{version}' is not semver")

    # 2 — CHANGELOG top matches version (the coupling law)
    changelog = _read(d / "CHANGELOG.md")
    if not changelog:
        reasons.append("CHANGELOG.md missing — the version↔improvement law has no ledger")
    else:
        top = _changelog_top_version(changelog)
        if top is None:
            reasons.append("CHANGELOG.md has no `## X.Y.Z` version entry")
        elif version and top != version:
            reasons.append(
                f"version drift: SKILL.md version={version} but CHANGELOG top={top} "
                f"— a change bumped one and not the other"
            )

    # 3 — spec carried in docs/spec/ (no-drift: the spec lives here)
    spec_dir = d / "docs" / "spec"
    carried = sorted(spec_dir.glob("service-factory-spec-*.md")) if spec_dir.exists() else []
    if not carried:
        reasons.append("no carried spec in docs/spec/ (service-factory-spec-*.md) "
                       "— the spec is not self-contained")
    if not spec_source:
        reasons.append("SKILL.md frontmatter has no `spec_source:` pointer")
    elif not (d / spec_source).exists():
        reasons.append(f"spec_source '{spec_source}' does not resolve to a file in the skill")
    elif "docs/spec/" not in spec_source:
        reasons.append(f"spec_source '{spec_source}' is not under docs/spec/ "
                       f"(the carried-spec home)")

    # 4 — no external tether (no-drift: no reference to a second copy)
    hits = [tok for tok in _FORBIDDEN_SKILL_MD if tok in skill_md]
    if hits:
        reasons.append(f"SKILL.md references the external spec copy {hits} "
                       f"— removes single-source-of-truth")
    for spec in carried:
        stext = _read(spec)
        shits = [tok for tok in _FORBIDDEN_SPEC if tok in stext]
        if shits:
            reasons.append(f"{spec.name} contains external reference(s) {shits} "
                           f"— carried spec must be self-contained")

    return {
        "pass": not reasons,
        "reasons": reasons,
        "version": version,
        "changelog_top": _changelog_top_version(changelog) if changelog else None,
        "carried_specs": [p.name for p in carried],
        "spec_source": spec_source,
    }


def main(argv):
    if len(argv) < 2:
        print("usage: version_guard.py <skill-dir>", file=sys.stderr)
        return 2
    res = check(argv[1])
    print(json.dumps(res, indent=2))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
