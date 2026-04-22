---
name: supervisr-validate
description: "Pre-release validation for Supervisr.AI services. Runs spec compliance, AC verification, compile, tests, and smoke tests. Auto-detects ticket from branch name. Use before /supervisr-release to catch issues. Does NOT work with Klever repos. Input: none (auto-detects from branch). Returns: structured pass/fail report with AC coverage. Usually orchestrated by supervisr-ship agent. Use standalone only when you need validation in isolation (e.g., mid-development check)."
user_invocable: true
---

# Supervisr Validate Skill

Local validation of a fix/feature before release. Runs spec compliance checks, acceptance criteria verification, compile, tests, and smoke tests, then generates a structured report.

## Usage

```bash
/supervisr-validate              # Auto-detect ticket from branch name
/supervisr-validate SPV-23       # Explicit ticket ID
```

## Workflow

### Step 1: Detect Context

1. **Service:** Identify from `$PWD` (e.g., `supervisor-query-service`, `lead-lifecycle-service`)
2. **Branch:** `git branch --show-current`
3. **Ticket:** Parse from branch name (`fix/SPV-23-*` → `SPV-23`) or use the argument passed by the user
4. **Commit:** `git rev-parse --short HEAD`
5. **Base branch:** Determine merge base — try `dev`, `main`, `master` in order

### Step 2: Resolve Report Path

1. Parse ticket ID (e.g., `SPV-23`)
2. Search for existing ticket folder:
   - `~/Developer/supervisr-ai/project-management/tickets/{TICKET-ID}/`
   - `~/Developer/supervisr-ai/project-management/tickets/SPV-3/{TICKET-ID}/` (nested under epic)
   - Search other epic folders under `tickets/` if not found above
3. Create `reports/validation/` subdirectory if needed (standalone) or `reports/ship/` (when called by supervisr-ship agent)
4. If ticket folder not found, **ask the user** before creating one

### Step 3: Load Agent OS Specs (Token-Efficient)

**Only if `{repo}/agent-os/specs/` exists.** If it doesn't exist, skip to Step 4.

1. **Front-load indices (lightweight — ~500 tokens each):**
   - Read `{repo}/agent-os/specs/api-contracts/index.md` — API contract catalog
   - Read `{repo}/agent-os/specs/architecture/index.md` — Architecture overview
   - List filenames in `{repo}/agent-os/specs/architecture/decisions/` — ADR titles only (don't read contents)
   - **Do NOT read all spec files yet**

2. **Identify relevant specs from git diff:**
   - Run `git diff {base_branch}...HEAD --name-only` to get changed files
   - Cross-reference changed files against the spec indices:
     - Changed `*Datafetcher.java` or `*Resolver.java` → load ADRs about data fetching/resolver patterns
     - Changed `schema.graphqls` or `*.graphqls` → load GraphQL API contracts + schema ADRs
     - Changed `*Repository.java` or `*Entity.java` → load datastore/entity ADRs
     - Changed config files (`application*.properties`, `*.yml`) → load config-related ADRs
     - Changed event/message handlers → load event architecture ADRs
   - Load only the targeted spec files

3. **Check API contracts:**
   - For each contract in `api-contracts/index.md` that's relevant to the diff:
     - Verify implementation satisfies the contract (payload schemas, endpoint paths, message formats)
     - Flag violations: missing fields, changed types, removed endpoints

4. **Check architecture alignment:**
   - For each relevant ADR:
     - Verify implementation follows the decided approach
     - Flag contradictions between code and ADR decisions
   - Example: ADR says "config goes to ERS/EQS, not local Datastore" → verify no local Datastore config queries added

5. **On-demand escalation:**
   - If a potential conflict is detected, load additional context (the full ADR, the full contract)
   - Better to be expensive and correct than cheap and wrong

### Step 4: Check Acceptance Criteria (When Available)

If acceptance criteria are provided (by the calling agent or via Jira):
1. For each criterion, review the diff + read relevant code to assess if met
2. Mark each: MET / NOT MET / CANNOT DETERMINE
3. For CANNOT DETERMINE, explain what's unclear

When running standalone (not from supervisr-ship), try to extract acceptance criteria:
- If the ticket ID is known, use the jira skill: `python3 ~/.claude-shared-config/skills/jira/jira.py get {TICKET-ID} --full`
- Parse acceptance criteria from the description

### Step 5: Compile

Run `mvn clean compile` and capture result (PASS/FAIL). If FAIL, stop and generate a failure report.

### Step 6: Run Tests

Run `mvn test` and capture:
- Total tests, passed, failed, skipped counts
- Note any pre-existing failures vs. new failures
- Distinguish between failures caused by current changes vs. known issues

### Step 7: Local Smoke Test

1. Start the app in background: `mvn spring-boot:run -Dspring-boot.run.profiles=local &`
2. Wait for startup (poll health endpoint or watch logs for "Started" message, ~30s timeout)
3. Run smoke queries against GraphQL endpoint (`http://localhost:8080/graphql` or service-specific port):
   - For `supervisor-query-service`: Query each root query type with minimal filters
   - For other services: Hit primary endpoints with basic requests
4. Capture response status and brief response summary for each query
5. Stop the app (kill the background process)

If the service cannot start locally (missing env vars, DB deps), note it as SKIPPED with reason.

### Step 8: Generate Report

Write to: `{resolved_ticket_path}/reports/validation/validation_{SHORT_HASH}_{YYYY-MM-DD}.md` (standalone)
Or: `{resolved_ticket_path}/reports/ship/validation_{SHORT_HASH}_{YYYY-MM-DD}.md` (when called by supervisr-ship)

## Report Template

```markdown
# Validation Report

**Report ID:** VAL-{SHORT_HASH}-{DATE}
**Service:** {service_name}
**Branch:** {branch_name}
**Commit:** {short_hash}
**Date:** {YYYY-MM-DD}

## Spec Compliance

### API Contracts
| Contract | Status | Details |
|----------|--------|---------|
| {contract_name} | PASS/FAIL/N/A | {details} |

*(Omit section if no agent-os/specs/ directory exists)*

### Architecture (ADR Alignment)
| ADR | Status | Details |
|-----|--------|---------|
| {adr_number} - {title} | ALIGNED/VIOLATION/N/A | {details} |

*(Omit section if no ADRs are relevant to the diff)*

## Acceptance Criteria
- [x] {criterion} — {evidence}
- [ ] {criterion} — {reason not met}

*(Omit section if no acceptance criteria available)*

## Compile: {PASS|FAIL}
{If FAIL, include error summary}

## Tests: {PASS (X/Y)} | {FAIL (N failures)}
{List any failures with brief description}
{Distinguish new failures vs. pre-existing known issues}

## Local Smoke Test: {PASS|FAIL|SKIPPED}
| Query | Status | Response |
|-------|--------|----------|
| {QueryName} | {PASS|FAIL|KNOWN ISSUE} | {brief response or error} |

## Known Issues
{List any pre-existing failures or known issues that are NOT caused by current changes}

## Verdict: {READY FOR RELEASE|NOT READY|READY WITH KNOWN ISSUES}
{Brief justification}
```

## Important Notes

- If compile fails, skip tests and smoke tests — generate partial report
- Always distinguish between NEW failures (caused by this branch) and PRE-EXISTING failures
- The smoke test phase is best-effort — if the app can't start locally, skip and note why
- Kill any background processes before finishing (cleanup)
- Report file naming: `validation_{SHORT_HASH}_{YYYY-MM-DD}.md` (e.g., `validation_60d42cb_2026-02-14.md`)
- **Token efficiency:** Always read index files first, then load only specs relevant to the diff. Never read all spec files.
- **Graceful degradation:** If `agent-os/specs/` doesn't exist, skip spec compliance checks and proceed with compile/test/smoke only (original behavior)
