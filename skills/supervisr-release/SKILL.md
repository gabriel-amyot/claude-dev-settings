# Supervisr Release Skill

Full release pipeline for Supervisr.AI microservices: test, tag, build, and publish GraphQL schema.

## Usage

```bash
/supervisr-release              # Full pipeline: test -> tag -> build -> schema
/supervisr-release --skip-tests  # Skip tests (tag -> build -> schema)
/supervisr-release --no-build    # Test -> tag only (no image, no schema)
/supervisr-release --schema-only # Only publish schema (prompt for env)
/supervisr-release --check-sync  # Check all schemas against Apollo Gateway (dev)
```

## Pipeline

### Phase 1: Test
Runs `mvn clean compile test`. If tests fail, the release is aborted.

### Phase 2: Changelog
- If `CHANGELOG.md` doesn't exist, create it by reconstructing history from git tags and commits
- Add a new entry at the top: `## [X.Y.Z-dev] - YYYY-MM-DD : TICKET-ID Summary`
- Categorize changes under **Features**, **Fixes**, **Refactors**, **Other**
- Stage and include in the release commit

### Phase 3: Tag & Build
- Finds latest `X.Y.Z-dev` tag and increments patch version
- Creates tag, pushes branch and tag to origin
- Builds and pushes Docker image via `mvn compile jib:build`

### Phase 4: Schema Publish
- Detects GraphQL schema changes since last tag
- Prompts for target environment (dev/sandbox/uat/prod)
- Publishes via `rover subgraph publish SupervisrAI@{env}`
- Skipped automatically for services without GraphQL (e.g., compliance-ers)

## Schema Sync Check

Use `--check-sync` to verify all local schemas against Apollo Gateway (dev environment):

```bash
/supervisr-release --check-sync
```

**What it does:**
- Runs `rover subgraph check SupervisrAI@dev` for all services with GraphQL schemas
- Reports which schemas are in sync ✅ vs. need publishing ⚠️
- Shows breaking changes, additions, and removals
- Can be run from any directory (checks all services)

**Output example:**
```
Checking schemas against Apollo Gateway (dev)...

✅ lead-lifecycle-service: No changes
⚠️  retell-service: Schema changes detected
    - Added field: CallEvent.duration
    - Changed type: CallEvent.timestamp (String! -> DateTime!)
✅ supervisor-query-service: No changes

Summary: 1 service needs schema publish
```

## Supported Services

| Service | Schema | Subgraph Name |
|---------|--------|---------------|
| lead-lifecycle-service | lead.graphqls | lead-lifecycle-service |
| retell-service | schema.graphqls | retell-service |
| supervisor-query-service | schema.graphqls | query-service |
| compliance-ers | none | n/a |

Service is auto-detected from `$PWD`.

## Configuration

Edit `supervisr_release_config.json` to add services or update routing URLs.

### Phase 5: Release Report

After the pipeline completes, generate a structured report.

**Report path resolution:**
1. Parse ticket ID from branch name (`fix/SPV-23-*` → `SPV-23`)
2. Search for existing ticket folder:
   - `~/Developer/supervisr-ai/project-management/tickets/{TICKET-ID}/`
   - `~/Developer/supervisr-ai/project-management/tickets/SPV-3/{TICKET-ID}/` (nested under epic)
   - Search other epic folders under `tickets/` if not found above
3. Create `reports/release/` subdirectory if needed
4. If ticket folder not found, **ask the user** before creating one

**Write to:** `{resolved_ticket_path}/reports/release/release_{TAG}_{YYYY-MM-DD}.md`

**Report template:**

```markdown
# Release Report

**Report ID:** REL-{TAG}-{DATE}
**Service:** {service_name}
**Tag:** {new_tag}
**Branch:** {branch_name}
**Commit:** {short_hash}
**Date:** {YYYY-MM-DD}
**Validation Report:** {VAL-ID if found, or "NOT FOUND — run /supervisr-validate first"}

## Pipeline Results
| Phase | Status | Details |
|-------|--------|---------|
| Tests | {PASS|FAIL|SKIPPED} | {pass/fail counts or skip reason} |
| Changelog | {UPDATED|SKIPPED} | {CHANGELOG.md entry added or reason skipped} |
| Tag | {new_tag} | {Pushed to origin} |
| Docker Image | {PUSHED|SKIPPED} | {image:tag or skip reason} |
| Schema Publish | {PUBLISHED|SKIPPED} | {environment or reason skipped} |

## Pending Actions
{List any manual steps remaining, e.g.:}
- [ ] Update DAC CI/CD variable to {new_tag}
- [ ] Publish schema via rover (if deferred)
- [ ] Verify deployment in target environment
```

## SOP: Pre-Release Validation

Before running `/supervisr-release`, it is **strongly recommended** to run `/supervisr-validate` first.

During report generation, the release skill will:
1. Look for a validation report in `{ticket_path}/reports/validation/`
2. If found, reference it in the release report (by Report ID)
3. If NOT found, print a warning: `⚠️ No validation report found. Consider running /supervisr-validate first.`

The release will NOT be blocked — this is advisory only.

## Requirements

- Git repo with committed changes
- Maven with Jib plugin configured
- Rover CLI + `APOLLO_KEY` (for schema publishing)
- GCP credentials (for image push)
