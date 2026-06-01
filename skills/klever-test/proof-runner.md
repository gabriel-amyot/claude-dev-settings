# Sprint Proof Runner

Generate AC-level proof artifacts for Jira. Maps every acceptance criterion in the sprint to a test layer (Playwright E2E, Python API, Java unit, grep) and produces structured evidence: screenshots, response logs, test output, and code pointers.

## Quick Start

```bash
# Run all in-scope tickets
cd ~/Developer/grp-beklever-com/project-management
bash tools/proof/run-proof.sh --all

# Single ticket
bash tools/proof/run-proof.sh --ticket KTP-510

# Single AC within a ticket
bash tools/proof/run-proof.sh --ticket KTP-510 --ac 4

# Dry run (validate setup without executing)
bash tools/proof/run-proof.sh --dry-run

# Filter by test layer
bash tools/proof/run-proof.sh --layer grep         # Grep checks only (no infra needed)
bash tools/proof/run-proof.sh --layer e2e           # Playwright only
bash tools/proof/run-proof.sh --layer api           # Python API tests only
bash tools/proof/run-proof.sh --layer unit          # Java unit tests only

# Regression tickets only
bash tools/proof/run-proof.sh --regression
```

## Prerequisites

Same as all /klever-test options. Run preflight first:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000       # Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:8097/proximity-report/actuator/health  # Backend
```

If services are down, use `/klever-local-stack` first. The `--layer grep` mode needs no running services.

## Architecture

```
AC Registry (YAML)  →  run-proof.sh (orchestrator)  →  Proof Reports (Jira wiki markup)
                            │
                            ├── Layer: e2e   → Playwright specs (e2e/proof/*.spec.ts)
                            ├── Layer: api   → Python scripts (tests/api/test_*.py)
                            ├── Layer: unit  → Java tests with @Tag("proof")
                            └── Layer: grep  → Pattern-absence checks (KTP-451 style)
```

## Files

| File | Location | Purpose |
|------|----------|---------|
| AC Registry | `project-management/tools/proof/ac-registry.yaml` | Maps every AC to test layer, spec, code pointer |
| Proof Runner | `project-management/tools/proof/run-proof.sh` | Orchestrator script |
| Report Template | `project-management/tools/proof/templates/proof-report.tpl` | Jira wiki markup template |
| Playwright specs | `app-front-portal/e2e/proof/*.spec.ts` | E2E proof tests |
| Playwright config | `app-front-portal/playwright.proof.config.ts` | Config for proof mode (always screenshot) |
| Proof fixtures | `app-front-portal/e2e/proof/proof-fixtures.ts` | Shared helpers |
| Python API tests | `app-proximity-report/tests/api/test_*.py` | Backend endpoint tests |
| Java proof tests | `app-proximity-report/src/test/.../*Test.java` | Tests tagged `@Tag("proof")` |

## Output

Reports are written to: `project-management/reports/proof/{TICKET}/proof-{date}.md`

Each report contains Jira wiki markup ready for posting via `/post-comment`.

## Adding Tests for New Tickets

1. Add AC entries to `ac-registry.yaml` under the new ticket key
2. For e2e ACs: create a spec in `app-front-portal/e2e/proof/`
3. For API ACs: create a Python test in `app-proximity-report/tests/api/`
4. For unit ACs: add `@Tag("proof")` test methods in existing Java test classes
5. For grep ACs: just add the entry to the registry with `grep_pattern` and `grep_paths`
6. Run `bash tools/proof/run-proof.sh --dry-run` to verify all specs are found

## New Sprint Setup

1. Update `sprint` field in `ac-registry.yaml`
2. Add new ticket entries (keep regression tickets from prior sprints)
3. Write new spec files as needed
4. Run `--dry-run` to validate

## Posting Results

After running proof:
```
/post-comment  # for each report file in reports/proof/{TICKET}/
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tickets pass |
| 1 | Some ACs failed |
| 2 | Infrastructure down (preflight failed) |
| 3 | Registry missing or malformed |

## Test Layer Selection Guide

| AC Type | Layer | Example |
|---------|-------|---------|
| "URL shows X", "UI renders Y", "button does Z" | e2e | Screenshot proof |
| "API returns X", "endpoint exists" | api | Response log proof |
| "Service aggregates correctly", "no exception thrown" | unit | Test output proof |
| "No reference to X exists in code" | grep | Pattern absence proof |
| "Deploy shows X on demo.dev" | manual | Human verification |
