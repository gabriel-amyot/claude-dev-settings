---
name: doc-standards-migrate
description: Migrate a Supervisr repo to the three-layer documentation standard. Moves ADRs from agent-os/ to docs/adr/, creates required index files, adds Related Services to agent-os/index.md, and updates CLAUDE.md routing table.
trigger: When user references a doc migration ticket (SPV-156 to SPV-161), says "migrate docs for {repo}", or opens a service repo that has ADRs in agent-os/.
scope: supervisr repos
---

# doc-standards-migrate

Runs the documentation standards migration checklist for one Supervisr service repo.

**Full standard:** `project-management/documentation/process/documentation-standards.md`
**Quick ref:** `~/.claude/library/context/documentation-standards-quick-ref.md`

## Trigger

- User opens a service repo and ADRs are found in `agent-os/`
- User references a migration Jira ticket (SPV-156 LLS, SPV-157 compliance-engine, SPV-158 retell, SPV-159 EQS, SPV-160 ERS, SPV-161 origin8-web)
- User says "migrate docs for {service}"

## Pre-flight

1. Read `project-management/documentation/process/documentation-standards.md` (full standard)
2. Identify which migration ticket applies (SPV-156 to SPV-161)
3. Confirm the service repo is checked out and clean (`git status`)

## Migration Steps

### Step 1 — Audit current state
```bash
# Count ADRs in wrong place
find agent-os/ -name "*.md" | xargs grep -l "^# ADR" | wc -l

# Check if docs/adr/ exists
ls docs/adr/ 2>/dev/null || echo "MISSING"

# Check agent-os/index.md has Related Services
grep -l "Related Services" agent-os/index.md || echo "MISSING"
```

### Step 2 — Move ADRs
- Create `docs/adr/` if missing
- Move each `agent-os/specs/architecture/decisions/NNN-*.md` to `docs/adr/NNN-*.md`
- Add MADR metadata block to each ADR (Status, Date, Scope, Ticket, Supersedes)
- Remove the old `decisions/` directory

### Step 3 — Create docs/ scaffolding
- `docs/README.md` — purpose statement, link to standard, subfolder list (use template from standard)
- `docs/INDEX.md` — one-line entry per doc
- `docs/adr/INDEX.md` — registry table: ID | Title | Status | Scope | Date

### Step 4 — Update agent-os/index.md
- Remove any ADR references or links into `agent-os/specs/architecture/decisions/`
- Add `## Related Services` section with the service's known cross-service relationships
- Add single link: "Architecture Decision Records: [docs/adr/INDEX.md](../docs/adr/INDEX.md)"

### Step 5 — Update agent-os/specs/architecture/index.md
- Remove ADR content/references
- Add one line: "Decision history: [docs/adr/INDEX.md](../../../docs/adr/INDEX.md)"

### Step 6 — Update CLAUDE.md routing table
Add/update the `## Where to Look` section:
```markdown
## Where to Look

| Need | Location |
|------|----------|
| System wiring, data flows | `agent-os/specs/architecture/` |
| API contracts, integration specs | `agent-os/specs/api-contracts/` |
| Coding standards and patterns | `agent-os/standards/` |
| Architecture Decision Records | `docs/adr/INDEX.md` |
| Architecture deep-dives, design studies | `docs/architecture/` |
| Cross-service flows (big picture) | Bibliothèque `stack/` or owner service's `docs/architecture/` |
| SBE scenarios | `agent-os/sbe/` |
```

### Step 7 — Service-specific extras (check migration ticket scope)
- **LLS (SPV-156):** Move `ARCHITECTURE_ANALYSIS_HEXAGONAL.md` from `agent-os/product/` → `docs/architecture/`. Trim README.md (was 291 lines).
- **retell (SPV-158):** Move `agent-os/future-improvements.md` → `docs/architecture/future-improvements.md`.
- **EQS (SPV-159):** Reorganize 10 root-level `standards/` files into subfolders (operations/, development/, security/, patterns/).
- **ERS (SPV-160):** Create README.md (setup, run, deploy). Move `standards/local-dev.md` → `standards/operations/local-dev.md`.

## Verification Gate

Run before closing the migration ticket:
```bash
# 1. ADRs in right place
ls docs/adr/*.md | wc -l

# 2. No ADRs in agent-os
grep -r "^# ADR" agent-os/ && echo "FAIL — ADR content still in agent-os" || echo "PASS"

# 3. Related Services present
grep -l "Related Services" agent-os/index.md && echo "PASS" || echo "FAIL"

# 4. Required files exist
ls docs/README.md docs/INDEX.md docs/adr/INDEX.md

# 5. CLAUDE.md has routing table
grep -l "Where to Look" CLAUDE.md && echo "PASS" || echo "FAIL"
```

## Post-migration
- Update Bibliothèque entries that reference this service — add `## Service-Local Documentation` back-links
- Update `project-management/documentation/process/documentation-standards.md` Current State table for this repo
- Close the Jira migration ticket with verification output as evidence
