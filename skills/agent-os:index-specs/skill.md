# Index Specs

Recursively build and maintain index files for specs documentation to enable progressive disclosure.

## Purpose

Create `index.yml` files throughout the `agent-os/specs/` tree to enable lazy-loading of specifications. Each directory with 2+ markdown files gets an index with minimal one-line descriptions for quick matching.

## Key Principles

1. **Progressive Disclosure**: Don't load everything at once — indexes enable targeted spec loading
2. **Minimal Descriptions**: One short sentence per spec for matching, not documentation
3. **Recursive**: Index every directory with 2+ `.md` files
4. **Smart Skipping**: Directories with only 1 `.md` file don't need an index
5. **Validation-Ready**: Enables validation scripts to pull only relevant specs

## Process

### Step 1: Scan Directory Tree

Starting from `agent-os/specs/`, recursively find all directories containing `.md` files:

```
agent-os/specs/
├── api-contracts/
│   └── index.md
├── architecture/
│   ├── index.md
│   ├── scheduling-system.md
│   └── decisions/
│       ├── 001-java21-spring-boot-tech-stack.md
│       ├── 002-availability-in-retellai-service.md
│       └── ...
```

For each directory:
- Count `.md` files (excluding subdirectories)
- If count >= 2, mark for indexing
- If count < 2, skip (no index needed)

### Step 2: Process Each Directory

For each directory marked for indexing:

1. **Load existing index** (if `index.yml` exists in that directory)
2. **Compare with current files**:
   - New files → need descriptions
   - Deleted files → remove from index
   - Existing files → keep as-is
3. **Handle new files**: Read file, propose description via AskUserQuestion
4. **Handle deleted files**: Remove automatically, report

### Step 3: Generate Index Files

Create/update `index.yml` in each directory with 2+ specs:

```yaml
# Specs Index - [Directory Name]
#
# This index enables progressive disclosure — load only the specs you need.
# Descriptions are minimal (one sentence) for quick matching.

file-name-without-extension:
  description: One-line description here
  file: relative/path/from/repo-root.md

another-file:
  description: Another one-line description
  file: relative/path/from/repo-root.md
```

**Rules:**
- Alphabetize entries by file name
- File names without `.md` extension as keys
- Include `file:` path relative to repo root for validation scripts
- One-line `description:` for matching/discovery
- Add comment header explaining progressive disclosure purpose

**Special Handling for ADRs** (architecture/decisions/):
- Extract ADR number and title from `# ADR-XXX: Title` header
- Description format: `"ADR-XXX: [extracted title or brief summary]"`
- Keep descriptions focused on the decision, not implementation details

### Step 4: Create Root Index

Generate/update `agent-os/specs/index.yml` (top-level) that maps categories:

```yaml
# Specs Root Index - Lead Lifecycle Service
#
# Progressive disclosure entry point — load categories as needed.

api-contracts:
  description: External service contracts and integration requirements
  file: agent-os/specs/api-contracts/index.yml

architecture:
  description: System architecture, diagrams, and design decisions
  file: agent-os/specs/architecture/index.yml
  subdirectories:
    - decisions

architecture/decisions:
  description: Architecture Decision Records (ADRs) - key architectural choices with context
  file: agent-os/specs/architecture/decisions/index.yml
```

**Root Index Rules:**
- Top-level categories map to subdirectories
- Include `subdirectories:` array if nested indexes exist
- Use `file:` to point to the category's `index.yml`

### Step 5: Report Results

Summarize changes for each directory:

```
Specs indexed:

api-contracts/
  ✓ 1 file (skipped - only 1 file, no index needed)

architecture/
  ✓ 2 new entries added
  ✓ 1 stale entry removed
  ✓ 1 entry unchanged
  → Created architecture/index.yml

architecture/decisions/
  ✓ 14 entries indexed
  ✓ 0 changes
  → Updated architecture/decisions/index.yml

Root index:
  ✓ 3 categories indexed
  → Updated agent-os/specs/index.yml

Total: 17 specs across 3 directories
```

## Example: ADR Index

```yaml
# Specs Index - Architecture Decisions

001-java21-spring-boot-tech-stack:
  description: "ADR-001: Java 21 + Spring Boot 3.4.x tech stack selection"
  file: agent-os/specs/architecture/decisions/001-java21-spring-boot-tech-stack.md

002-availability-in-retellai-service:
  description: "ADR-002: Partner availability checks delegated to RetellAI service"
  file: agent-os/specs/architecture/decisions/002-availability-in-retellai-service.md

015-cloud-scheduler-ticker-pattern:
  description: "ADR-015: Cloud Scheduler + Ticker pattern for job orchestration"
  file: agent-os/specs/architecture/decisions/015-cloud-scheduler-ticker-pattern.md
```

## When to Run

- After creating/deleting spec files (ADRs, architecture docs, contracts)
- Before running validation scripts (ensures indexes are current)
- If specs have been reorganized or renamed
- As part of ticket archival (via `/archive` skill)

## Integration with Validation

Validation scripts can:
1. Read `agent-os/specs/index.yml` to find categories
2. Load category-specific indexes on demand
3. Pull only specs matching current implementation scope
4. Avoid loading entire spec tree into context

## Output

Creates/updates:
- `agent-os/specs/index.yml` (root)
- `agent-os/specs/[category]/index.yml` (for each category with 2+ files)
- Skips directories with only 1 file
