# Index Architecture

Recursively build and maintain index files specifically for architecture documentation (system diagrams, ADRs, design docs) to enable progressive disclosure.

## Purpose

Create `index.yml` files throughout the `agent-os/specs/architecture/` tree to enable lazy-loading of architecture specifications. This is a specialized version of `/agent-os:index-specs` focused only on architecture documentation.

## Scope

Indexes **only** the architecture section:
- `agent-os/specs/architecture/` (system diagrams, patterns)
- `agent-os/specs/architecture/decisions/` (ADRs)
- Any nested architecture subdirectories

Does **not** index:
- `agent-os/specs/api-contracts/` (use `/agent-os:index-specs` for full tree)
- `agent-os/standards/` (use `/agent-os:index-standards`)
- Other spec categories

## Process

### Step 1: Scan Architecture Tree

Starting from `agent-os/specs/architecture/`, recursively find all directories containing `.md` files:

```
agent-os/specs/architecture/
├── index.md                    # System architecture overview
├── scheduling-system.md        # Scheduling subsystem design
└── decisions/
    ├── 001-java21-spring-boot-tech-stack.md
    ├── 002-availability-in-retellai-service.md
    ├── ...
    └── 015-cloud-scheduler-ticker-pattern.md
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

Create/update `index.yml` in each architecture directory with 2+ files:

```yaml
# Architecture Index - [Subsection Name]
#
# This index enables progressive disclosure of architecture documentation.
# Load only the architectural decisions and designs relevant to your current work.

file-name-without-extension:
  description: One-line description here
  type: architecture-doc  # or: adr, diagram, pattern
  file: agent-os/specs/architecture/[subsection]/file-name.md

another-file:
  description: Another one-line description
  type: adr
  file: agent-os/specs/architecture/decisions/another-file.md
```

**Architecture-Specific Fields:**
- `type`: Document type (architecture-doc, adr, diagram, pattern, subsystem)
- `status`: For ADRs only (Accepted, Proposed, Deprecated, Superseded)
- `supersedes`: For ADRs that replace older decisions

**Rules:**
- Alphabetize entries by file name (or by ADR number for decisions/)
- File names without `.md` extension as keys
- Include `file:` path relative to repo root
- One-line `description:` focused on the architectural decision/pattern

### Step 4: Special Handling for ADRs

For files in `architecture/decisions/`:

1. **Extract ADR metadata**:
   - ADR number from filename (e.g., `001-` → ADR-001)
   - Title from `# ADR-XXX: Title` header
   - Status from `## Status` section (Accepted, Proposed, etc.)

2. **Format description**:
   ```yaml
   001-java21-spring-boot-tech-stack:
     description: "Java 21 + Spring Boot 3.4.x tech stack selection"
     type: adr
     status: Accepted
     file: agent-os/specs/architecture/decisions/001-java21-spring-boot-tech-stack.md
   ```

3. **Sort by ADR number** (not alphabetically by filename)

### Step 5: Create Architecture Root Index

Generate/update `agent-os/specs/architecture/index.yml`:

```yaml
# Architecture Root Index - Lead Lifecycle Service
#
# Progressive disclosure entry point for architecture documentation.
# Load subsections as needed during development or validation.

# System-level architecture documents
index:
  description: "System architecture overview - service boundaries, data flows, ERS/EQS pipeline"
  type: architecture-doc
  file: agent-os/specs/architecture/index.md

scheduling-system:
  description: "Cloud Scheduler + Ticker pattern - job orchestration architecture"
  type: subsystem
  file: agent-os/specs/architecture/scheduling-system.md

# Architecture Decision Records
decisions:
  description: "Architecture Decision Records (ADRs) - key architectural choices with context and rationale"
  type: directory
  file: agent-os/specs/architecture/decisions/index.yml
  count: 14
```

### Step 6: Report Results

Summarize changes:

```
Architecture indexed:

architecture/ (root)
  ✓ 2 entries indexed
  ✓ 1 subdirectory (decisions/)
  → Updated architecture/index.yml

architecture/decisions/
  ✓ 14 ADRs indexed
  ✓ 2 new entries added
  ✓ 0 stale entries removed
  → Updated architecture/decisions/index.yml

Total: 16 architecture documents across 2 directories
```

## ADR Index Example

```yaml
# Architecture Index - Decisions (ADRs)
#
# Architecture Decision Records capture key architectural choices with context.
# Load ADRs as needed during development, validation, or architectural review.

001-java21-spring-boot-tech-stack:
  description: "Java 21 + Spring Boot 3.4.x tech stack selection"
  type: adr
  status: Accepted
  file: agent-os/specs/architecture/decisions/001-java21-spring-boot-tech-stack.md

004-config-storage-ers-eqs:
  description: "Configuration storage in ERS/EQS via Apollo Gateway + Pub/Sub"
  type: adr
  status: Accepted
  file: agent-os/specs/architecture/decisions/004-config-storage-ers-eqs.md

015-cloud-scheduler-ticker-pattern:
  description: "Cloud Scheduler + Ticker pattern for job orchestration"
  type: adr
  status: Accepted
  file: agent-os/specs/architecture/decisions/015-cloud-scheduler-ticker-pattern.md
```

## When to Run

- After creating/updating ADRs
- After adding new architecture diagrams or subsystem docs
- Before architectural reviews or validation
- As part of ticket archival (via `/archive` skill)
- When reorganizing architecture documentation

## Integration with Validation

Validation scripts can:
1. Read `agent-os/specs/architecture/index.yml` to find subsections
2. Load ADRs by number/topic on demand
3. Pull only architecture docs relevant to current implementation
4. Map implementation files to relevant ADRs via metadata

## Output

Creates/updates:
- `agent-os/specs/architecture/index.yml` (architecture root)
- `agent-os/specs/architecture/decisions/index.yml` (ADRs)
- Additional indexes for any nested architecture subdirectories with 2+ files

## Relationship to Other Skills

- **Broader scope**: Use `/agent-os:index-specs` to index entire specs tree (api-contracts + architecture)
- **Narrower focus**: This skill indexes only architecture documentation
- **Standards**: Use `/agent-os:index-standards` for coding standards (separate tree)
