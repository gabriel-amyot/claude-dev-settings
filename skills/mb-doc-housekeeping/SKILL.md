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

Runs all checks (coverage, stale, sync, sections, project-mgmt, memory-caps, memory-dates) and returns a combined report.

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

### Memory Caps
```bash
/mb-doc-housekeeping memory-caps
```
Scans all `~/.claude/projects/*/memory/MEMORY.md` files:
- WARNING (🟡) if any MEMORY.md is 150–200 lines
- FAIL (🔴) if any MEMORY.md exceeds 200 lines
- OK (✅) if under 150 lines
- Report: file path, line count, status

### Memory Dates
```bash
/mb-doc-housekeeping memory-dates
```
Checks temporal grounding in MEMORY.md files:
- Each `## Section` heading should have `<!-- decided: YYYY-MM-DD -->` or `<!-- updated: YYYY-MM-DD -->` or `[Last Verified: YYYY-MM-DD]`
- Entries dated > 90 days ago: 🟡 STALE
- Entries with no date: 🔴 UNDATED
- Recent entries (≤ 90 days): ✅ CURRENT
- Report: file path, section heading, date found or "missing", status

## Requirements

- Python 3.8+
- PyYAML: `pip install pyyaml`

## Integration

This skill is used by the **Mother Base Housekeeper** agent (`mother-base-housekeeper`) which combines this with `/validate-repo-links` for full workspace health checks.
