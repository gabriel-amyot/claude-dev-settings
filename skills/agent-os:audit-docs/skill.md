# agent-os:audit-docs - Documentation Guardian Agent

## Purpose

Comprehensive documentation integrity guardian that maintains knowledge graph coherence and enforces documentation standards across the repository.

**Mission:** Ensure an agentic LLM can enter the repo and instantly understand what the service does, where to find information, how to navigate related services, current architectural decisions, and coding standards—without expensive token searches or human questions.

## Scope

Validates integrity across:
- `agent-os/specs/` - API contracts, architecture, decisions (ADRs)
- `agent-os/standards/` - Coding standards and best practices
- `agent-os/product/` - Product roadmap and overview
- `.repo-links.yaml` - Repository graph and service interactions
- `CLAUDE.md` - Engineering handbook and cross-references
- `README.md` - Quick start and setup instructions
- `reports/` - Validation, review, release, and audit reports

**Out of Scope:**
- GraphQL schema validation (delegated to `/supervisr-validate` and `/supervisr-review`)
- Code quality checks (delegated to `/supervisr-review`)
- Build/test validation (delegated to `/supervisr-validate`)

## Process

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│  /agent-os:audit-docs                                       │
│  (Documentation Guardian Agent)                             │
└─────────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌─────────┐     ┌─────────┐    ┌──────────┐
   │ Index   │     │ Validate│    │ Cross-   │
   │ Health  │     │ Repo    │    │ Reference│
   │ Check   │     │ Links   │    │ Check    │
   └─────────┘     └─────────┘    └──────────┘
         │               │               │
         └───────────────┴───────────────┘
                         │
                    Aggregate
                         │
                         ▼
              ┌──────────────────┐
              │  Health Report   │
              │  + Auto-Repair   │
              └──────────────────┘
```

### Step 1: Index Health Check

**Purpose:** Detect stale indexes when files are added/removed.

**Process:**
1. Capture current state of all indexes:
   - `agent-os/specs/index.yml`
   - `agent-os/specs/architecture/index.yml`
   - `agent-os/specs/architecture/decisions/index.yml`
   - `agent-os/standards/index.yml`
2. Run indexing skills with `--dry-run` mode (if available) or capture actual changes:
   - `/agent-os:index-specs`
   - `/agent-os:index-architecture`
   - `/agent-os:index-standards`
3. Compare before/after to detect:
   - New files not indexed (CRITICAL)
   - Stale index entries pointing to deleted files (CRITICAL)
   - Description changes needed (WARNING)

**Output:** List of index discrepancies with severity level.

**Auto-Repair:** YES - Re-run indexing skills to fix stale indexes.

### Step 2: Repo Graph Validation

**Purpose:** Ensure `.repo-links.yaml` accurately maps service interactions.

**Process:**
1. Run `/validate-repo-links` to check:
   - DAC path exists and is valid
   - IAC path exists and is valid
   - Related services listed match actual dependencies
2. Verify cross-service references:
   - Check if related services exist in expected locations
   - Validate schema compatibility (if applicable)

**Output:** Broken links, missing references, invalid paths.

**Auto-Repair:** NO - Flag for manual fix.

### Step 3: Cross-Reference Validation

**Purpose:** Detect broken references and stale documentation.

**Process:**
1. **CLAUDE.md validation:**
   - Extract all file path references
   - Verify referenced files exist
   - Check for references to deleted classes/services (grep codebase)
   - Validate package structure alignment
2. **README.md validation:**
   - Check all links (internal and external)
   - Verify setup instructions reference correct files
3. **ADR accuracy check:**
   - Compare ADR decisions to actual implementation
   - Examples:
     - ADR-001 says "Java 21 + Spring Boot 3.4.x" → verify `pom.xml` matches
     - ADR-004 says "Config in ERS/EQS" → verify no local config entities
   - Flag ADRs with status "superseded" or "deprecated" that still appear current

**Output:** Broken references, stale ADRs, mismatched decisions.

**Auto-Repair:** NO - Flag for manual fix.

### Step 4: Documentation Standards Validation

**Purpose:** Enforce CommonMark compliance and BMAD standards.

**Process:**
1. **CommonMark compliance:**
   - Validate all `.md` files with CommonMark parser
   - Check heading hierarchy (no skipped levels)
   - Validate code block language tags
2. **BMAD standards enforcement** (from `_bmad/_memory/tech-writer-sidecar/documentation-standards.md`):
   - **CRITICAL:** No time estimates ("X weeks", "Y days", "estimated Z hours")
   - **WARNING:** Prefer active voice over passive voice
   - **WARNING:** Task-oriented focus (not encyclopedic)
   - **INFO:** Check for "should", "would", "could" (prefer "must", "will", "can")
3. **Progressive disclosure validation:**
   - Index descriptions under 15 words
   - Index hierarchy max 3 levels deep
   - File paths in indexes are valid

**Output:** Standards violations categorized by severity.

**Auto-Repair:** NO - Flag for manual fix.

### Step 5: Reports Folder Validation

**Purpose:** Maintain structured report storage for traceability.

**Process:**
1. **Directory structure check:**
   - Verify `reports/validation/` exists
   - Verify `reports/review/` exists
   - Verify `reports/release/` exists
   - Verify `reports/audit/` exists (create if missing)
2. **Naming convention validation:**
   - `validation_{HASH}_{DATE}.md`
   - `review_{HASH}_{DATE}.md`
   - `release_{VERSION}_{DATE}.md`
   - `audit_{DATE}.md`
3. **Orphan detection:**
   - Check if reports reference non-existent commits
   - Flag reports older than 90 days with no corresponding git tag/branch

**Output:** Structural issues, naming violations, orphaned reports.

**Auto-Repair:** NO - Flag for manual fix (except creating `reports/audit/` if missing).

### Step 6: Generate Health Report

**Purpose:** Aggregate all findings into actionable report.

**Process:**
1. Collect all findings from Steps 1-5
2. Categorize by severity:
   - **CRITICAL:** Blocks merge (stale indexes, broken repo links, banned time estimates, stale ADRs)
   - **WARNING:** Doesn't block merge (formatting issues, passive voice, naming violations)
   - **INFO:** Informational only (suggestions, minor improvements)
3. Generate report using template (see Report Template section below)
4. Write to `.claude/audit-reports/audit_{YYYY-MM-DD-HHMMSS}.md`
5. If `--auto-repair` mode: Fix stale indexes only
6. Return summary to user with blocking status

**Output:** Structured health report with executive summary and actionable remediation steps.

## Modes

### `--check-only` (Default)

Audit without making changes. Generates report only.

**Usage:**
```bash
/agent-os:audit-docs
/agent-os:audit-docs --check-only
```

### `--auto-repair`

Conservative auto-repair: fixes stale indexes only, flags everything else for manual fix.

**What gets auto-repaired:**
- ✓ Stale spec indexes → re-run `/agent-os:index-specs`
- ✓ Stale architecture indexes → re-run `/agent-os:index-architecture`
- ✓ Stale standards indexes → re-run `/agent-os:index-standards`
- ✓ Missing `reports/audit/` directory → create with `.gitkeep`

**What gets flagged for manual fix:**
- Broken `.repo-links.yaml` paths
- Stale ADR decisions
- Time estimates in documentation
- Cross-reference issues
- CommonMark formatting violations
- Reports folder naming issues

**Usage:**
```bash
/agent-os:audit-docs --auto-repair
```

### `--verbose`

Detailed output with file-by-file analysis.

**Usage:**
```bash
/agent-os:audit-docs --verbose
/agent-os:audit-docs --auto-repair --verbose
```

## Report Template

**File:** `.claude/audit-reports/audit_{YYYY-MM-DD-HHMMSS}.md` (gitignored)

```markdown
# Documentation Health Report

**Audit ID:** AUD-YYYYMMDD-HHMMSS
**Date:** YYYY-MM-DD HH:MM:SS
**Repository:** [repo-name]
**Branch:** [current branch]
**Commit:** [short hash]

---

## Executive Summary

- **Overall Health:** [HEALTHY | DEGRADED | CRITICAL]
- **Total Issues:** X critical, Y warnings, Z info
- **Indexes Current:** [YES | NO]
- **Repo Links Valid:** [YES | NO]
- **Standards Compliant:** [YES | NO]

---

## 1. Index Health

### Specs Indexes
- ✓ agent-os/specs/index.yml - Current
- ✗ agent-os/specs/architecture/index.yml - 2 new ADRs not indexed

### Standards Indexes
- ✓ agent-os/standards/index.yml - Current

### Actions Required
- [ ] Re-run /agent-os:index-architecture to add ADR-XXX, ADR-YYY

---

## 2. Repo Graph Validation

### .repo-links.yaml
- ✓ DAC path valid: ~/path/to/dac/
- ✗ IAC path broken: ~/path/to/iac/ (path does not exist)
- ✓ compliance-ers interaction valid

### Actions Required
- [ ] Fix IAC path in .repo-links.yaml

---

## 3. Cross-Reference Validation

### CLAUDE.md
- ✓ All file references valid
- ⚠ Reference to deleted CustomerConfigService (line 42)

### README.md
- ✓ All links valid

### ADR Accuracy
- ✓ ADR-001: Java 21 + Spring Boot 3.4.x - MATCHES implementation
- ✗ ADR-004: Config storage in ERS/EQS - PARTIAL (PhonePoolClient not consumed yet)

### Actions Required
- [ ] Update CLAUDE.md line 42 to remove CustomerConfigService reference
- [ ] Update ADR-004 to reflect PhonePoolClient integration status

---

## 4. Documentation Standards

### CommonMark Compliance
- ✓ All markdown files pass CommonMark validation

### BMAD Standards
- ✗ CRITICAL: agent-os/product/roadmap.md contains time estimate ("3 weeks")
- ⚠ WARNING: agent-os/specs/api-contracts/index.md uses passive voice (line 12)

### Progressive Disclosure
- ✓ Index hierarchy navigable (3 levels deep max)
- ✓ Descriptions under 15 words

### Actions Required
- [ ] CRITICAL: Remove time estimate from product/roadmap.md (blocks merge)
- [ ] WARNING: Rewrite api-contracts/index.md line 12 in active voice

---

## 5. Reports Folder Validation

### Structure
- ✓ reports/validation/ exists
- ✓ reports/review/ exists
- ✓ reports/release/ exists
- ⚠ WARNING: reports/audit/ missing (will be created on first audit)

### Naming Conventions
- ✓ All validation reports follow: `validation_{HASH}_{DATE}.md`
- ⚠ WARNING: 1 release report missing date: `release_v1.0.0.md`

### Actions Required
- [ ] WARNING: Rename release_v1.0.0.md to include date

---

## 6. Recommendations

### High Priority (CRITICAL - blocks merge)
1. [Action 1]
2. [Action 2]

### Medium Priority (WARNING - doesn't block)
3. [Action 3]
4. [Action 4]

### Low Priority (INFO)
5. [Action 5]

---

## 7. Auto-Repair Summary

**Mode:** [CHECK-ONLY | AUTO-REPAIR]

**Auto-Fixed Issues:** (if --auto-repair mode)
- ✓ Re-indexed specs (added X new entries)
- ✓ Re-indexed architecture (added Y ADRs)
- ✓ Created reports/audit/ directory

**Manual Fix Required (CRITICAL - blocks merge):**
- [ ] [Issue 1]
- [ ] [Issue 2]

**Manual Fix Required (WARNING - doesn't block):**
- [ ] [Issue 3]

---

## 8. CI/CD Integration Status

**Blocking Status:** [CRITICAL issues found → MERGE BLOCKED ❌ | No critical issues → MERGE ALLOWED ✓]

**Summary for PR Comment:**
```
[Status Icon] Documentation Integrity Check [PASSED/FAILED]

X CRITICAL issues must be fixed before merge:
- [Issue 1]
- [Issue 2]

Y WARNING issues (merge allowed, but recommended to fix):
- [Issue 3]

Auto-repaired Z stale indexes ✓

Full report: .claude/audit-reports/audit_YYYY-MM-DD-HHMMSS.md
```

---

## Appendix: File Inventory

### agent-os/specs/ (X files)
- [List of files]

### agent-os/standards/ (Y files)
- [List of files]

### agent-os/product/ (Z files)
- [List of files]

---

**Next Steps:** Address high-priority issues, then re-run /agent-os:audit-docs to verify fixes.
```

## Integration

### Manual Invocation

```bash
# Check documentation health (read-only)
/agent-os:audit-docs

# Check with verbose output
/agent-os:audit-docs --verbose

# Check and auto-repair stale indexes
/agent-os:audit-docs --auto-repair

# Check, auto-repair, and show details
/agent-os:audit-docs --auto-repair --verbose
```

### CI/CD Integration (Future)

**Pre-Merge Hook** (`.github/workflows/doc-guardian.yml`):

```yaml
name: Documentation Guardian

on:
  pull_request:
    branches: [main, dev]
    paths:
      - 'agent-os/**'
      - '.repo-links.yaml'
      - 'CLAUDE.md'
      - 'README.md'
      - 'reports/**'

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Documentation Guardian
        run: |
          claude skill agent-os:audit-docs --check-only

      - name: Check Blocking Status
        if: failure()
        run: |
          echo "❌ Documentation integrity check failed"
          echo "CRITICAL issues must be fixed before merge"
          exit 1

      - name: Upload Audit Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: audit-report
          path: .claude/audit-reports/
```

**Trigger Conditions:**
- On PR to `main` or `dev` branch
- When files in `agent-os/` change
- When `.repo-links.yaml` changes
- When `CLAUDE.md` or `README.md` change
- When `reports/` structure changes

## Blocking Behavior

### CRITICAL (Blocks Merge)

**When CI/CD is enabled**, these issues prevent merge:
- Stale indexes (breaks progressive disclosure)
- Broken `.repo-links.yaml` paths (breaks repo navigation)
- Time estimates in documentation (banned by BMAD standards)
- Stale ADR decisions contradicting implementation

### WARNING (Visible but Doesn't Block)

**Shown in PR but merge allowed:**
- CommonMark formatting issues
- Reports folder naming violations
- Minor cross-reference issues
- Passive voice in documentation
- Missing descriptions in indexes

### INFO (Informational Only)

**No PR impact:**
- Documentation improvement suggestions
- Style recommendations
- Optional enhancements

## Implementation Notes

### Dependencies

This skill orchestrates existing skills:
- `/agent-os:index-specs` - Spec indexing
- `/agent-os:index-architecture` - Architecture indexing with ADR metadata
- `/agent-os:index-standards` - Standards indexing
- `/validate-repo-links` - Repo graph validation

### File Locations

**Skill Definition:** `~/.claude/skills/agent-os:audit-docs/skill.md`

**Reports Output:** `.claude/audit-reports/audit_{YYYY-MM-DD-HHMMSS}.md` (gitignored)

**Reports Directory Structure:**
```
.claude/
└── audit-reports/
    ├── .gitkeep
    └── audit_{YYYY-MM-DD-HHMMSS}.md  (gitignored)
```

### Validation Rules

**Index Health:**
- All files in `agent-os/specs/` must be in `index.yml`
- All ADRs in `agent-os/specs/architecture/decisions/` must be in `index.yml`
- All files in `agent-os/standards/` must be in `index.yml`
- Deleted files must be removed from indexes

**Repo Links:**
- DAC path must exist and be valid directory
- IAC path must exist and be valid directory
- Related services must be resolvable (if paths provided)

**Cross-References:**
- File paths in `CLAUDE.md` must exist
- Package structure in `CLAUDE.md` must match actual code
- ADR decisions must match `pom.xml` and code
- Class/service references must exist in codebase

**Documentation Standards:**
- No time estimates: "X weeks", "Y days", "estimated Z hours"
- Prefer active voice over passive voice
- Task-oriented focus (not encyclopedic)
- CommonMark strict compliance
- Index descriptions under 15 words
- Max 3-level index hierarchy

**Reports Folder:**
- `reports/validation/` must exist
- `reports/review/` must exist
- `reports/release/` must exist
- `reports/audit/` auto-created if missing
- Naming: `{type}_{HASH}_{DATE}.md` or `{type}_{VERSION}_{DATE}.md`

## Verification Tests

### Test 1: Index Staleness Detection
1. Add new ADR without updating index
2. Run `/agent-os:audit-docs --check-only`
3. Verify report shows "CRITICAL: 1 new ADR not indexed"
4. Run `/agent-os:audit-docs --auto-repair`
5. Verify index updated automatically
6. Re-run and verify "HEALTHY" status

### Test 2: Repo Links Validation
1. Break a path in `.repo-links.yaml`
2. Run `/agent-os:audit-docs --check-only`
3. Verify report shows "CRITICAL: IAC path broken"
4. Fix path manually
5. Re-run and verify "HEALTHY" status

### Test 3: Cross-Reference Validation
1. Reference non-existent file in `CLAUDE.md`
2. Run `/agent-os:audit-docs --check-only`
3. Verify report shows "broken reference"
4. Fix reference
5. Re-run and verify clean

### Test 4: Standards Compliance
1. Add "estimated 2 weeks" to markdown file
2. Run `/agent-os:audit-docs --check-only`
3. Verify report shows "CRITICAL: time estimate found"
4. Remove estimate manually
5. Re-run and verify compliant

### Test 5: Reports Folder Validation
1. Create report with incorrect naming: `validation_latest.md`
2. Run `/agent-os:audit-docs --check-only`
3. Verify report shows "WARNING: invalid naming convention"
4. Rename to `validation_{HASH}_{DATE}.md`
5. Re-run and verify clean

### Test 6: Full Pipeline
1. Run `/agent-os:audit-docs --check-only` on clean repo → "HEALTHY"
2. Introduce 3 CRITICAL + 1 WARNING issue
3. Re-run → "CRITICAL" status with 4 findings
4. Run `/agent-os:audit-docs --auto-repair` → 1 auto-fixed, 2 flagged
5. Fix 2 CRITICAL manually → status: 1 WARNING
6. Fix WARNING → "HEALTHY"

## Success Criteria

**An agentic LLM can enter the repository and instantly understand:**
- ✓ What the service does (mission, boundaries) → `CLAUDE.md`, `README.md`
- ✓ Where to find information (optimized indexes) → `agent-os/*/index.yml`
- ✓ How to navigate related services (repo links) → `.repo-links.yaml`
- ✓ Current architectural decisions (ADRs) → `agent-os/specs/architecture/decisions/`
- ✓ Coding standards (progressive disclosure) → `agent-os/standards/`

**All without:**
- ✗ Expensive token searches (thanks to accurate indexes)
- ✗ Human questions (thanks to clear documentation)
- ✗ Stale information (thanks to automated integrity checks)

## References

### Existing Skills
- `/agent-os:index-specs` - Spec indexing
- `/agent-os:index-architecture` - Architecture indexing
- `/agent-os:index-standards` - Standards indexing
- `/validate-repo-links` - Repo graph validation
- `/supervisr-validate` - Build + tests + smoke tests
- `/supervisr-review` - Code review against standards

### Documentation Standards
- BMAD Standards: `~/Developer/gabriel-amyot/tools/adhd-developers-best-friend/_bmad/_memory/tech-writer-sidecar/documentation-standards.md`
- CommonMark Spec: https://commonmark.org/

### Related Tools
- `markdownlint` - CommonMark linting (if available)
- `grep` - Pattern detection for banned phrases
- Git - For commit/branch metadata
