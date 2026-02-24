#!/usr/bin/env python3
"""
Mother Base Documentation Housekeeping

Checks documentation health across the Supervisr workspace:
- Missing CLAUDE.md in DAC repos
- Stale CLAUDE.md (README.md newer than CLAUDE.md)
- INFRASTRUCTURE_OVERVIEW.md sync with .repo-index.yaml
- project-management CLAUDE.md existence and structure
- CLAUDE.md required sections validation

Usage:
  /mb-doc-housekeeping              # Full documentation health check
  /mb-doc-housekeeping coverage     # Just CLAUDE.md coverage
  /mb-doc-housekeeping stale        # Just staleness check
  /mb-doc-housekeeping sync         # Just infrastructure overview sync
"""

import sys
import json
import yaml
import os
from pathlib import Path
from datetime import datetime


def detect_workspace_root():
    """Walk up from CWD to find workspace root"""
    candidates = [Path.cwd(), Path(__file__).resolve().parent]
    for start in candidates:
        current = start
        for _ in range(10):
            if (current / "project-management").is_dir() and (current / "faas").is_dir():
                return current
            current = current.parent
    return None


WORKSPACE_ROOT = detect_workspace_root()
if WORKSPACE_ROOT is None:
    print(json.dumps({"error": "Cannot detect workspace root"}))
    sys.exit(1)

DAC_BASE = WORKSPACE_ROOT / "faas" / "grp-dac" / "grp-dac-sprvsr" / "grp-dac-sprvsr-core"
PROJECT_MGMT = WORKSPACE_ROOT / "project-management"
REPO_INDEX = PROJECT_MGMT / ".repo-index.yaml"
INFRA_OVERVIEW = PROJECT_MGMT / "documentation" / "architecture" / "INFRASTRUCTURE_OVERVIEW.md"

REQUIRED_CLAUDE_SECTIONS = [
    "Project Overview",
    "Related Repositories",
    "Deployment Workflow",
]


def load_yaml(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def mtime(path):
    """Get file modification time, or 0 if missing"""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def check_coverage():
    """Check which DAC repos have CLAUDE.md"""
    results = {"total": 0, "with_claude": 0, "missing": [], "with_repo_links": 0, "missing_repo_links": []}

    if not DAC_BASE.exists():
        return {"error": f"DAC base not found: {DAC_BASE}"}

    for repo_dir in sorted(DAC_BASE.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        results["total"] += 1

        if (repo_dir / "CLAUDE.md").exists():
            results["with_claude"] += 1
        else:
            results["missing"].append(repo_dir.name)

        if (repo_dir / ".repo-links.yaml").exists():
            results["with_repo_links"] += 1
        else:
            results["missing_repo_links"].append(repo_dir.name)

    return results


def check_staleness():
    """Check CLAUDE.md freshness vs README.md"""
    results = {"checked": 0, "stale": []}

    if not DAC_BASE.exists():
        return {"error": "DAC base not found"}

    for repo_dir in sorted(DAC_BASE.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue

        claude_md = repo_dir / "CLAUDE.md"
        readme_md = repo_dir / "README.md"

        if not claude_md.exists():
            continue

        results["checked"] += 1
        claude_time = mtime(claude_md)
        readme_time = mtime(readme_md)

        if readme_time > claude_time and readme_md.exists():
            results["stale"].append({
                "repo": repo_dir.name,
                "readme_modified": datetime.fromtimestamp(readme_time).isoformat(),
                "claude_modified": datetime.fromtimestamp(claude_time).isoformat(),
            })

    return results


def check_sections():
    """Validate CLAUDE.md files have required sections"""
    results = {"checked": 0, "issues": []}

    if not DAC_BASE.exists():
        return {"error": "DAC base not found"}

    for repo_dir in sorted(DAC_BASE.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue

        claude_md = repo_dir / "CLAUDE.md"
        if not claude_md.exists():
            continue

        results["checked"] += 1
        try:
            content = claude_md.read_text()
        except OSError:
            continue

        missing = [s for s in REQUIRED_CLAUDE_SECTIONS if f"## {s}" not in content]
        if missing:
            results["issues"].append({
                "repo": repo_dir.name,
                "missing_sections": missing
            })

    return results


def check_infra_sync():
    """Check INFRASTRUCTURE_OVERVIEW.md service catalog vs .repo-index.yaml"""
    results = {"in_sync": True, "issues": []}

    if not INFRA_OVERVIEW.exists():
        return {"error": "INFRASTRUCTURE_OVERVIEW.md not found", "in_sync": False}

    if not REPO_INDEX.exists():
        return {"error": ".repo-index.yaml not found", "in_sync": False}

    index_data = load_yaml(REPO_INDEX)
    if not index_data:
        return {"error": "Failed to parse .repo-index.yaml", "in_sync": False}

    try:
        overview_content = INFRA_OVERVIEW.read_text()
    except OSError:
        return {"error": "Failed to read INFRASTRUCTURE_OVERVIEW.md", "in_sync": False}

    index_services = set(index_data.get("services", {}).keys())
    dac_mappings = index_data.get("infrastructure", {}).get("dac", {}).get("mappings", {})

    # Check each indexed service appears in overview
    for service in index_services:
        dac_name = dac_mappings.get(service, "")
        if dac_name and dac_name not in overview_content:
            results["in_sync"] = False
            results["issues"].append(f"Service '{service}' (DAC: {dac_name}) not found in INFRASTRUCTURE_OVERVIEW.md")

    # Check DAC mapping count matches
    dac_repos_on_disk = [d.name for d in DAC_BASE.iterdir() if d.is_dir() and not d.name.startswith(".")]
    unmapped = [r for r in dac_repos_on_disk if r not in dac_mappings.values()]
    if unmapped:
        results["in_sync"] = False
        results["issues"].append(f"DAC repos not in .repo-index.yaml mappings: {unmapped}")

    return results


def check_project_mgmt():
    """Check project-management has appropriate CLAUDE.md"""
    results = {"has_claude": False, "issues": []}

    claude_md = PROJECT_MGMT / "CLAUDE.md"
    if claude_md.exists():
        results["has_claude"] = True
        content = claude_md.read_text()
        if "repo-index" not in content.lower() and ".repo-index" not in content:
            results["issues"].append("project-management/CLAUDE.md doesn't reference .repo-index.yaml")
    else:
        results["issues"].append("project-management/CLAUDE.md does not exist")

    return results


def full_check():
    """Run all checks"""
    return {
        "timestamp": datetime.now().isoformat(),
        "coverage": check_coverage(),
        "staleness": check_staleness(),
        "sections": check_sections(),
        "infra_sync": check_infra_sync(),
        "project_management": check_project_mgmt(),
    }


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "full"

    try:
        if command == "full":
            result = full_check()
        elif command == "coverage":
            result = check_coverage()
        elif command == "stale":
            result = check_staleness()
        elif command == "sync":
            result = check_infra_sync()
        elif command == "sections":
            result = check_sections()
        elif command == "project-mgmt":
            result = check_project_mgmt()
        else:
            result = {"error": f"Unknown command: {command}"}

        print(json.dumps(result, indent=2))
        sys.exit(0 if "error" not in result else 1)
    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}))
        sys.exit(1)
