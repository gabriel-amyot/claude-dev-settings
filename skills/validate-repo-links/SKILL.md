---
name: validate-repo-links
description: Validate .repo-links.yaml integrity and manage repo graph index
---

# Validate Repo Links

Validates the integrity of `.repo-links.yaml` files across workspaces and maintains a lightweight graph index in `project-management/.repo-index.yaml`.

## Multi-Workspace Support

The script auto-detects the workspace by checking for marker directories defined in `workspaces.yaml`. Currently supported:

| Workspace | Detect dirs | Domains |
|-----------|-------------|---------|
| **supervisr-ai** | `faas`, `app/micro-services` | app, dac |
| **grp-beklever-com** | `grp-app`, `grp-dac`, `grp-iac` | 25 domains (app-backend-*, app-frontend, iac-*, dac-*, comp-*, cfg) |

Workspace config lives in `workspaces.yaml` next to this script.

## Commands

### 1. Validate (default)
```bash
/validate-repo-links
```

Discovers all `.repo-links.yaml` files and validates:
- Infrastructure links (DAC, IAC paths)
- App repo links (for DAC repos that reference an app repo)
- Interaction repo paths (sibling service links)
- Internal structure paths

### 2. Reindex
```bash
/validate-repo-links reindex
```

Rebuilds `.repo-index.yaml` from all `.repo-links.yaml` files using workspace-specific scan paths and infrastructure config.

### 3. Visualize
```bash
/validate-repo-links visualize              # Tree format
/validate-repo-links visualize --format mermaid
```

### 4. Bootstrap
```bash
/validate-repo-links bootstrap
```

Scans all workspace scan paths for git repos missing `.repo-links.yaml` and scaffolds a minimal file with name, domain, and workspace_root. Review generated files and fill in descriptions/interactions.

## Requirements

- Python 3.8+
- PyYAML: `pip install pyyaml`

## Integration

This skill is used by the **Mother Base Housekeeper** agent (`mother-base-housekeeper`).
