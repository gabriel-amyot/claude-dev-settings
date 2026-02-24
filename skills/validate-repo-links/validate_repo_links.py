#!/usr/bin/env python3
"""
Repo Links Validator - Validate .repo-links.yaml integrity

Usage:
  /validate-repo-links                      # Validate all links
  /validate-repo-links reindex              # Rebuild index
  /validate-repo-links visualize            # Show graph as tree
  /validate-repo-links visualize --format mermaid
  /validate-repo-links bootstrap            # Scaffold missing .repo-links.yaml
"""

import sys
import json
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACES_CONFIG = SCRIPT_DIR / "workspaces.yaml"


def load_yaml(file_path):
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def save_yaml(data, file_path):
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_workspaces_config():
    config = load_yaml(WORKSPACES_CONFIG)
    if not config or "workspaces" not in config:
        print(json.dumps({"error": f"Cannot load {WORKSPACES_CONFIG}"}))
        sys.exit(1)
    return config["workspaces"]


def detect_workspace_root():
    """Walk up from cwd to find a directory matching a workspace config."""
    workspaces = load_workspaces_config()

    candidates = [Path.cwd(), SCRIPT_DIR]
    for start in candidates:
        current = start
        for _ in range(10):
            if (current / "project-management").is_dir():
                for ws_name, ws_config in workspaces.items():
                    detect_dirs = ws_config.get("detect", [])
                    if any((current / d).exists() for d in detect_dirs):
                        return current, ws_name, ws_config
            current = current.parent
    return None, None, None


WORKSPACE_ROOT, WORKSPACE_NAME, WORKSPACE_CONFIG = detect_workspace_root()
if WORKSPACE_ROOT is None:
    print(json.dumps({"error": "Cannot detect workspace root. Ensure project-management/ and workspace marker dirs exist."}))
    sys.exit(1)

PROJECT_MANAGEMENT_ROOT = WORKSPACE_ROOT / "project-management"
REPO_INDEX_FILE = PROJECT_MANAGEMENT_ROOT / ".repo-index.yaml"


def get_scan_paths():
    """Build list of (domain, abs_path) from workspace config scan_paths."""
    paths = []
    for domain, rel_paths in WORKSPACE_CONFIG.get("scan_paths", {}).items():
        for rel in rel_paths:
            paths.append((domain, WORKSPACE_ROOT / rel))
    return paths


def find_all_repo_links_files():
    """Find .repo-links.yaml across all scan paths for current workspace."""
    files = []
    for domain, scan_path in get_scan_paths():
        if not scan_path.exists():
            continue
        for service_dir in sorted(scan_path.iterdir()):
            if service_dir.is_dir():
                repo_links_file = service_dir / ".repo-links.yaml"
                if repo_links_file.exists():
                    files.append(repo_links_file)
    return files


def validate_repo_links_file(repo_path, links_data):
    """Validate a single .repo-links.yaml file"""
    errors = []
    repo_dir = Path(repo_path).parent

    if "infrastructure" in links_data and links_data["infrastructure"]:
        if "dac" in links_data["infrastructure"] and links_data["infrastructure"]["dac"]:
            dac_path_str = links_data["infrastructure"]["dac"]["path"]
            if dac_path_str and dac_path_str != ".":
                dac_path = repo_dir / dac_path_str
                if not dac_path.exists():
                    errors.append({
                        "type": "broken_dac_link",
                        "path": str(dac_path),
                        "relative": dac_path_str
                    })

        if "iac" in links_data["infrastructure"] and links_data["infrastructure"]["iac"]:
            for iac in links_data["infrastructure"]["iac"]:
                iac_path = repo_dir / iac["path"]
                if not iac_path.exists():
                    errors.append({
                        "type": "broken_iac_link",
                        "path": str(iac_path),
                        "relative": iac["path"]
                    })

    if "app_repo" in links_data and links_data["app_repo"]:
        app_path = repo_dir / links_data["app_repo"]["path"]
        if not app_path.exists():
            errors.append({
                "type": "broken_app_repo_link",
                "path": str(app_path),
                "relative": links_data["app_repo"]["path"]
            })

    if "interactions" in links_data and links_data["interactions"]:
        for interaction in links_data["interactions"]:
            if "repo" in interaction:
                interaction_path = repo_dir / interaction["repo"]
                if not interaction_path.exists():
                    errors.append({
                        "type": "broken_interaction_link",
                        "path": str(interaction_path),
                        "service": interaction["name"]
                    })

    if "structure" in links_data and links_data["structure"]:
        for struct in links_data["structure"]:
            struct_path = repo_dir / struct["path"]
            if not struct_path.exists():
                errors.append({
                    "type": "broken_structure_path",
                    "path": str(struct_path),
                    "relative": struct["path"]
                })

    return errors


def validate_links():
    """Validate all .repo-links.yaml files discovered across workspace"""
    repo_links_files = find_all_repo_links_files()

    if not repo_links_files:
        return {
            "error": "No .repo-links.yaml files found",
            "suggestion": "Run '/validate-repo-links bootstrap' to scaffold them, then '/validate-repo-links reindex'"
        }

    results = {
        "workspace": WORKSPACE_NAME,
        "timestamp": datetime.now().isoformat(),
        "total_repos": 0,
        "valid_repos": 0,
        "repos_with_errors": 0,
        "total_errors": 0,
        "details": []
    }

    for repo_links_file in repo_links_files:
        results["total_repos"] += 1

        links_data = load_yaml(repo_links_file)
        if not links_data:
            results["repos_with_errors"] += 1
            results["total_errors"] += 1
            results["details"].append({
                "service": str(repo_links_file),
                "status": "error",
                "errors": [{"type": "invalid_yaml", "path": str(repo_links_file)}]
            })
            continue

        service_name = links_data.get("name", repo_links_file.parent.name)
        errors = validate_repo_links_file(repo_links_file, links_data)

        if errors:
            results["repos_with_errors"] += 1
            results["total_errors"] += len(errors)
            results["details"].append({
                "service": service_name,
                "source": str(repo_links_file.relative_to(WORKSPACE_ROOT)),
                "status": "invalid",
                "errors": errors
            })
        else:
            results["valid_repos"] += 1
            results["details"].append({
                "service": service_name,
                "source": str(repo_links_file.relative_to(WORKSPACE_ROOT)),
                "status": "valid"
            })

    results["overall_status"] = "valid" if results["repos_with_errors"] == 0 else "invalid"

    if REPO_INDEX_FILE.exists():
        index_data = load_yaml(REPO_INDEX_FILE)
        if index_data:
            index_data["validation_status"] = results["overall_status"]
            index_data["last_validated"] = results["timestamp"]
            save_yaml(index_data, REPO_INDEX_FILE)

    return results


def build_service_graph(repo_links_files):
    """Build service interaction graph from .repo-links.yaml files"""
    services = {}
    dac_mappings = {}
    iac_shared = None
    seen_names = set()

    for repo_links_file in repo_links_files:
        links_data = load_yaml(repo_links_file)
        if not links_data:
            continue

        service_name = links_data.get("name")
        if not service_name:
            continue

        is_infra_only = links_data.get("type") == "infra-only"

        try:
            relative_path = str(repo_links_file.parent.relative_to(WORKSPACE_ROOT))
        except ValueError:
            relative_path = str(repo_links_file.parent)

        interactions = {"outbound": [], "inbound": []}
        if "interactions" in links_data and links_data["interactions"]:
            for interaction in links_data["interactions"]:
                target = interaction.get("name")
                direction = interaction.get("direction", "outbound")

                if direction == "outbound":
                    interactions["outbound"].append(target)
                elif direction == "inbound":
                    interactions["inbound"].append(target)
                elif direction == "bidirectional":
                    interactions["outbound"].append(target)
                    interactions["inbound"].append(target)

        if service_name in seen_names:
            existing = services[service_name]
            for direction in ["outbound", "inbound"]:
                for target in interactions.get(direction, []):
                    if target not in existing["interactions"].get(direction, []):
                        existing["interactions"].setdefault(direction, []).append(target)
        else:
            seen_names.add(service_name)
            service_entry = {"interactions": {k: v for k, v in interactions.items() if v}}

            if is_infra_only:
                app_repo = links_data.get("app_repo")
                if app_repo and app_repo.get("path"):
                    try:
                        app_abs = (repo_links_file.parent / app_repo["path"]).resolve()
                        service_entry["path"] = str(app_abs.relative_to(WORKSPACE_ROOT))
                    except (ValueError, OSError):
                        service_entry["path"] = None
                else:
                    service_entry["path"] = None
                service_entry["description"] = links_data.get("description", "")
            else:
                service_entry["path"] = relative_path

            services[service_name] = service_entry

        if "infrastructure" in links_data and links_data["infrastructure"]:
            dac_info = (links_data["infrastructure"] or {}).get("dac")
            if dac_info:
                dac_path = dac_info.get("path", "")
                if dac_path == ".":
                    dac_mappings[service_name] = repo_links_file.parent.name
                elif dac_path:
                    dac_mappings[service_name] = Path(dac_path).name

            iac_list = (links_data["infrastructure"] or {}).get("iac")
            if iac_list and not iac_shared:
                for iac in iac_list:
                    iac_path = iac.get("path", "")
                    if iac_path:
                        iac_shared = Path(iac_path).name
                        break

    return services, dac_mappings, iac_shared


def reindex():
    """Rebuild .repo-index.yaml from all .repo-links.yaml files in workspace"""
    repo_links_files = find_all_repo_links_files()

    if not repo_links_files:
        return {
            "error": "No .repo-links.yaml files found in workspace",
            "searched": [str(p) for _, p in get_scan_paths()]
        }

    services, dac_mappings, iac_shared = build_service_graph(repo_links_files)

    infra_config = WORKSPACE_CONFIG.get("infrastructure", {})
    dac_cfg = infra_config.get("dac", {})
    iac_cfg = infra_config.get("iac", {})

    index_data = {
        "workspace_root": WORKSPACE_NAME,
        "services": services,
        "infrastructure": {
            "dac": {
                "base_path": dac_cfg.get("base_path", ""),
                "mappings": dac_mappings
            },
            "iac": {
                "base_path": iac_cfg.get("base_path", ""),
                "shared": iac_shared or iac_cfg.get("shared")
            }
        },
        "generated_at": datetime.now().isoformat(),
        "repo_count": len(services),
        "validation_status": "pending"
    }

    save_yaml(index_data, REPO_INDEX_FILE)

    return {
        "status": "success",
        "workspace": WORKSPACE_NAME,
        "index_file": str(REPO_INDEX_FILE),
        "repos_found": len(repo_links_files),
        "services_indexed": len(services),
        "timestamp": index_data["generated_at"]
    }


def visualize_tree():
    """Generate tree visualization of service graph"""
    if not REPO_INDEX_FILE.exists():
        return {
            "error": f"Index file not found: {REPO_INDEX_FILE}",
            "suggestion": "Run '/validate-repo-links reindex' to create it"
        }

    index_data = load_yaml(REPO_INDEX_FILE)
    if not index_data:
        return {"error": "Failed to parse index file"}

    services = index_data.get("services", {})
    ws_name = index_data.get("workspace_root", WORKSPACE_NAME)

    lines = []
    lines.append(f"# {ws_name} Service Graph")
    lines.append("")
    lines.append(f"Services: {len(services)}")
    lines.append(f"Last indexed: {index_data.get('generated_at')}")
    lines.append(f"Validation: {index_data.get('validation_status')}")
    lines.append("")
    lines.append("## Service Interactions")
    lines.append("")

    for service_name in sorted(services.keys()):
        service = services[service_name]
        lines.append(f"### {service_name}")
        path = service.get('path')
        if path:
            lines.append(f"  Path: {path}")
        else:
            lines.append(f"  Path: (infra-only, no app repo)")

        interactions = service.get("interactions", {})
        if "outbound" in interactions:
            lines.append(f"  Outbound → {', '.join(interactions['outbound'])}")
        if "inbound" in interactions:
            lines.append(f"  Inbound ← {', '.join(interactions['inbound'])}")
        lines.append("")

    lines.append("## Infrastructure Mappings")
    lines.append("")

    infra = index_data.get("infrastructure", {})
    if "dac" in infra:
        lines.append("### DAC (Data Access Control)")
        lines.append(f"  Base: {infra['dac'].get('base_path')}")
        for service, dac_name in infra['dac'].get('mappings', {}).items():
            lines.append(f"  {service} → {dac_name}")
        lines.append("")

    if "iac" in infra:
        lines.append("### IAC (Infrastructure as Code)")
        lines.append(f"  Base: {infra['iac'].get('base_path')}")
        lines.append(f"  Shared: {infra['iac'].get('shared')}")

    return {
        "format": "tree",
        "content": "\n".join(lines)
    }


def visualize_mermaid():
    """Generate Mermaid diagram of service graph"""
    if not REPO_INDEX_FILE.exists():
        return {
            "error": f"Index file not found: {REPO_INDEX_FILE}",
            "suggestion": "Run '/validate-repo-links reindex' to create it"
        }

    index_data = load_yaml(REPO_INDEX_FILE)
    if not index_data:
        return {"error": "Failed to parse index file"}

    services = index_data.get("services", {})

    lines = []
    lines.append("```mermaid")
    lines.append("graph TB")
    lines.append("")

    for service_name in sorted(services.keys()):
        safe_name = service_name.replace("-", "_")
        lines.append(f"  {safe_name}[{service_name}]")

    lines.append("")

    for service_name, service in services.items():
        safe_name = service_name.replace("-", "_")
        interactions = service.get("interactions", {})

        if "outbound" in interactions:
            for target in interactions["outbound"]:
                safe_target = target.replace("-", "_")
                lines.append(f"  {safe_name} --> {safe_target}")

    lines.append("```")

    return {
        "format": "mermaid",
        "content": "\n".join(lines)
    }


def visualize(format_type="tree"):
    if format_type == "mermaid":
        return visualize_mermaid()
    else:
        return visualize_tree()


def bootstrap():
    """Scaffold .repo-links.yaml for repos that don't have one yet."""
    created = []
    skipped = []

    for domain, scan_path in get_scan_paths():
        if not scan_path.exists():
            continue
        for service_dir in sorted(scan_path.iterdir()):
            if not service_dir.is_dir():
                continue
            if not (service_dir / ".git").is_dir():
                continue

            repo_links_file = service_dir / ".repo-links.yaml"
            if repo_links_file.exists():
                skipped.append(str(repo_links_file.relative_to(WORKSPACE_ROOT)))
                continue

            try:
                workspace_rel = str(service_dir.relative_to(WORKSPACE_ROOT))
                depth = len(Path(workspace_rel).parts)
                workspace_root_rel = "/".join([".."] * depth)
            except ValueError:
                workspace_root_rel = "../../.."

            scaffold = {
                "name": service_dir.name,
                "description": "",
                "workspace_root": workspace_root_rel,
                "domain": domain,
                "infrastructure": {},
                "interactions": [],
                "structure": []
            }

            save_yaml(scaffold, repo_links_file)
            created.append(str(repo_links_file.relative_to(WORKSPACE_ROOT)))

    return {
        "status": "success",
        "workspace": WORKSPACE_NAME,
        "created": len(created),
        "skipped_existing": len(skipped),
        "files_created": created,
        "files_skipped": skipped
    }


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "validate"

    try:
        if command == "validate":
            result = validate_links()
        elif command == "reindex":
            result = reindex()
        elif command == "visualize":
            format_type = "mermaid" if "--format" in sys.argv and "mermaid" in sys.argv else "tree"
            result = visualize(format_type)
        elif command == "bootstrap":
            result = bootstrap()
        else:
            result = {"error": f"Unknown command: {command}"}

        print(json.dumps(result, indent=2))
        sys.exit(0 if "error" not in result else 1)
    except Exception as e:
        error_result = {
            "error": str(e),
            "type": type(e).__name__
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)
