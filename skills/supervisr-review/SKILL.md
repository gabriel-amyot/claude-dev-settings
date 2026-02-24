# Supervisr Review Skill

Code review of staged/committed changes against repo-specific standards (`agent-os/standards/`) and global CLAUDE.md standards. Generates a structured review report.

## Usage

```bash
/supervisr-review              # Auto-detect ticket from branch name
/supervisr-review SPV-23       # Explicit ticket ID
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
3. Create `reports/review/` subdirectory if needed (standalone) or `reports/ship/` (when called by supervisr-ship agent)
4. If ticket folder not found, **ask the user** before creating one

### Step 3: Gather Diff

1. Run `git diff {base}...HEAD` to get the full diff of all changes on this branch
2. Run `git log {base}...HEAD --oneline` to get commit history
3. Run `git diff {base}...HEAD --stat` to get file change summary (+lines, -lines)
4. Run `git diff {base}...HEAD --name-only` to get changed file list (for standards matching)
5. Read each changed file in full to understand context (not just the diff hunks)

### Step 4: Load Agent OS Standards (Token-Efficient)

**Only if `{repo}/agent-os/standards/` exists.** If it doesn't exist, skip to Step 5.

1. **Front-load the standards index:**
   - Read `{repo}/agent-os/standards/index.yml` — this is the catalog of all standards with descriptions
   - **Do NOT read all standard files yet**

2. **Identify relevant standards from diff:**
   - Cross-reference changed files against the standards index:
     - Changed `*.graphqls` or GraphQL-related Java files → load `standards/graphql/*.md`
     - Changed `*Repository.java` or Datastore queries → load `standards/datastore/*.md`
     - Changed `*Test.java` → load `standards/testing/*.md`
     - Changed event handlers or webhooks → load domain-specific standards (e.g., `standards/event-receiver/*.md`, `standards/disposition/*.md`)
     - Changed code style patterns → load `standards/code-style/*.md`
   - Load only the targeted standard files

3. **Check repo standards (Part A):**
   - For each relevant standard, verify the changed code follows the documented pattern
   - Examples:
     - `dgs-codegen-types.md` says "never create manual Java classes for GraphQL types" → check if new manual types were added
     - `graphql/api-design.md` says "no REST endpoints" → check no REST controllers added
     - `webhooks/event-switch-pattern.md` says use flatMap switch → verify pattern used
     - `datastore/query-pattern.md` defines how queries should be structured → verify compliance
   - Flag violations as **Critical** (blocks merge) or **Warning** (noted but doesn't block)

4. **On-demand escalation:**
   - If a potential conflict is detected, load additional standard files for full context
   - Better to be expensive and correct than cheap and wrong

### Step 5: Analyze Against Global Standards (Part B — CLAUDE.md)

Review the diff against these criteria:

#### Code Style (from CLAUDE.md preferences)
- **Self-documenting code:** No comments that explain what code does — names should be intuitive
- **Small focused methods:** Methods should do one thing; blocks with comments should be extracted into named methods
- **Boolean helpers read like questions:** `isStaleWebhook()`, `hasPermission()`, `shouldRetry()`
- **No comment cruft in tests:** Test names + variable names should make intent obvious
- **Use `log.debug()` over comments** when explanation is truly needed

#### Test Quality
- **Test naming:** `{Given}{When}{Then}` pattern (e.g., `validJobId_whenGetJobCalled_thenReturnsJob`)
- **One behavior per test**
- **Constants extracted:** No hardcoded magic values — use `private static final` fields
- **`List.of()` over `Arrays.asList()`**
- **Compact structure:** `//given //when //then` separators, no excessive blank lines
- **Helper methods for common stubs**
- **No `@MockitoSettings(strictness = Strictness.LENIENT)` at class level**

#### Security (OWASP Top 10)
- Injection vulnerabilities (SQL, GraphQL, command)
- Broken authentication/authorization
- Sensitive data exposure (secrets in code, logs)
- Security misconfiguration

#### API/Schema Compatibility
- Breaking changes to GraphQL schema
- Removed or renamed fields without deprecation
- Changed return types
- New required arguments on existing queries/mutations

#### General Quality
- Dead code introduced or not cleaned up
- Error handling gaps
- Resource leaks (unclosed connections, streams)
- Concurrency issues
- Proper use of existing patterns in the codebase

### Step 6: Generate Report

Write to: `{resolved_ticket_path}/reports/review/review_{SHORT_HASH}_{YYYY-MM-DD}.md` (standalone)
Or: `{resolved_ticket_path}/reports/ship/review_{SHORT_HASH}_{YYYY-MM-DD}.md` (when called by supervisr-ship)

## Report Template

```markdown
# Code Review Report

**Report ID:** REV-{SHORT_HASH}-{DATE}
**Service:** {service_name}
**Branch:** {branch_name}
**Commit Range:** {base_tag_or_ref}..{short_hash}
**Files Changed:** {count} (+{added}, -{removed})
**Date:** {YYYY-MM-DD}

## Summary
{2-3 sentence overview of what changed and whether it's ready for merge}

## Repo Standards Compliance

| Standard | File(s) | Status | Details |
|----------|---------|--------|---------|
| {standard_name} | {affected_files} | PASS/VIOLATION | {details} |

*(Omit section if no agent-os/standards/ directory exists)*

## Findings

### Critical (blocks merge)
{List items that MUST be fixed before merge, or "None"}

### Warnings
{List items that should be addressed but don't block merge}

### Suggestions
{Optional improvements, style nits, refactoring opportunities}

### Positives
{Good patterns, clean code, thorough testing — acknowledge what's done well}

## Checklist
- [ ] Follows code style (CLAUDE.md)
- [ ] Follows repo standards (agent-os/standards/)
- [ ] Tests pass for changed code
- [ ] Test naming follows {Given}{When}{Then}
- [ ] No hardcoded magic values in tests
- [ ] No security issues (OWASP top 10)
- [ ] Schema backward-compatible (or breaking change is intentional)
- [ ] No dead code introduced
- [ ] Error handling adequate

## Verdict: {APPROVE|REQUEST CHANGES|APPROVE WITH COMMENTS}
{Brief justification}
```

## Important Notes

- Read the full files, not just diff hunks — context matters for understanding if patterns are followed
- Be specific in findings: reference file:line and quote the relevant code
- Distinguish between issues introduced by THIS branch vs. pre-existing problems
- If pre-existing issues are found, note them under Warnings as "pre-existing" but don't block merge
- Focus critical findings on actual bugs, security issues, and breaking changes — not style preferences
- The review should be constructive, not nitpicky
- **Token efficiency:** Always read `index.yml` first, then load only standards relevant to the diff. Never read all standard files.
- **Graceful degradation:** If `agent-os/standards/` doesn't exist, skip repo standards checks and proceed with global CLAUDE.md standards only (original behavior)
- **Two-part structure:** Part A (repo standards) uses `agent-os/standards/`, Part B (global standards) uses CLAUDE.md. Both are always checked.
