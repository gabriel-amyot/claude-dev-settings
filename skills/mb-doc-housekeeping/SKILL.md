---
name: mb-doc-housekeeping
description: Mother Base Documentation Housekeeping — checks CLAUDE.md coverage, staleness, infrastructure sync, and required sections across DAC repos
---

# Mother Base Documentation Housekeeping

Checks documentation health across the Supervisr.ai workspace. Designed to be run by the Mother Base Housekeeper agent or standalone.

## Commands

### Full Check (default)
```bash
/mb-doc-housekeeping
```

Runs all checks and returns a combined report.

### Coverage Only
```bash
/mb-doc-housekeeping coverage
```
Which DAC repos have `CLAUDE.md` and `.repo-links.yaml`.

### Staleness Check
```bash
/mb-doc-housekeeping stale
```
Finds `CLAUDE.md` files where `README.md` was modified more recently (content may be out of sync).

### Infrastructure Sync
```bash
/mb-doc-housekeeping sync
```
Verifies `INFRASTRUCTURE_OVERVIEW.md` service catalog matches `.repo-index.yaml`.

### Section Validation
```bash
/mb-doc-housekeeping sections
```
Checks each `CLAUDE.md` has required sections: Project Overview, Related Repositories, Deployment Workflow.

### Project Management Check
```bash
/mb-doc-housekeeping project-mgmt
```
Checks `project-management/CLAUDE.md` exists and references `.repo-index.yaml`.

## Requirements

- Python 3.8+
- PyYAML: `pip install pyyaml`

## Integration

This skill is used by the **Mother Base Housekeeper** agent (`mother-base-housekeeper`) which combines this with `/validate-repo-links` for full workspace health checks.
