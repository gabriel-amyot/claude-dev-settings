---
name: bmad-repo-onboarding
description: Onboard any repo with a full agent-os scaffold: CLAUDE.md, agent-os/index.md, standards, docs/adr/. Dispatches Winston (architecture), Amelia (code standards), and Leo (spec gaps) in parallel. Trigger: "onboard this repo", "set up agent-os", "bootstrap repo", "new repo setup", "add CLAUDE.md".
nav:
  bay: ops
  when: "Bootstrap agent-os scaffold for a repo: CLAUDE.md, specs, ADRs, standards."
  when_not: "Repo already onboarded. Auditing existing docs (use /agent-os:audit-docs)."
  personas: [winston, amelia, leo]
---

# bmad-repo-onboarding

Bootstraps a repo from zero to fully onboarded: CLAUDE.md, agent-os scaffold, docs/adr/, .gitignore hygiene, and Bibliotheque link. All output is committed immediately because untracked files die in context resets.

## When to Use

- A repo has no CLAUDE.md or agent-os/
- User says "onboard this repo", "set up agent-os", "bootstrap repo", "new repo setup", "add CLAUDE.md"
- A night crawl or sprint-crawl discovers an unregistered repo
- After cloning a new service into the org

## Input

- **Repo path** (required): absolute path to the repo root. If not provided, use `pwd`.
- **Ticket ID** (optional): Jira ticket for traceability in commit messages. Default: "ONBOARD".
- **Org** (optional): `supervisrai` or `klever`. Detected from repo path if omitted.

---

## Phase 0 — Pre-flight

Before writing anything:

1. Confirm repo path exists and is a git repo:
   ```bash
   git -C <repo_path> status --porcelain
   ```
   If not a git repo, STOP and tell the user.

2. Check clean working tree. If dirty, STOP and ask the user whether to stash, commit, or discard before proceeding.

3. Detect default branch:
   ```bash
   git -C <repo_path> branch -r | grep HEAD
   ```
   Record it. If DAC repo (path contains `grp-dac`), default branch is `dev`.

4. Check .gitignore for credential patterns. Open or create `.gitignore` and verify these patterns are present. Add any that are missing:
   ```
   .env
   *.env.*
   *.secret
   *.token
   .env.local
   .env.*.local
   ```
   If any were added, commit the .gitignore fix first before any other changes.

---

## Phase 1 — Language and Framework Detection

Read the repo root to identify the stack. Look for these files in order:

| File | Stack |
|------|-------|
| `pom.xml` | Java / Maven (Spring Boot likely) |
| `build.gradle` or `build.gradle.kts` | Java / Gradle |
| `package.json` | Node.js (check `frameworks` field for Next.js, Express, etc.) |
| `go.mod` | Go |
| `requirements.txt` or `pyproject.toml` | Python |
| `Cargo.toml` | Rust |
| `*.tf` files | Terraform infrastructure |
| `Dockerfile` only | Container-only repo |

Read whichever manifest exists. Extract:
- Language and version
- Main framework (Spring Boot, Next.js, Express, etc.)
- Build command (from scripts section, Makefile, or Maven lifecycle)
- Test command
- Any linting/formatting commands

Also read `README.md` if it exists for repo purpose, team owner, and deployment notes.

---

## Phase 2 — Dispatch Parallel Agents

Dispatch all three BMAD agents simultaneously. Each reads their persona file first. Each writes their output to a temp location (`/tmp/onboard-{repo-name}/`). The orchestrator assembles the final scaffold after all three complete.

Use `model: "sonnet"` for all three agents.

### Agent A: Winston (Architecture Scan)

Persona file: `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/architect.md`

Winston's job:
1. Read the source tree structure (top 2 levels only, not all source files)
2. Identify the service's architectural pattern (layered, hexagonal, event-driven, etc.)
3. Identify entry points (controllers, handlers, main functions, API routes)
4. Identify external dependencies (databases, message queues, external APIs)
5. Identify cross-service relationships (what does this service call, what calls it)
6. Flag any architectural debt worth capturing

Winston writes to `/tmp/onboard-{repo-name}/winston-architecture.md` in this format:
```markdown
## Service Purpose
One sentence.

## Architectural Pattern
Layered / Hexagonal / Event-Driven / etc. with brief rationale.

## Entry Points
- `path/to/Controller.java` — HTTP REST, port 8080
- `path/to/Consumer.java` — PubSub subscription: topic-name

## External Dependencies
- PostgreSQL (main datastore)
- PubSub (lead-events topic)
- Auth0 (M2M token validation)

## Cross-Service Relationships
| Service | Relationship | Direction |
|---------|-------------|-----------|
| lead-lifecycle-service | Consumes lead events | Inbound |
| eqs | Publishes materialized views | Outbound |

## Architectural Debt (flagged)
- Bullet list of issues worth capturing as ADR candidates
```

### Agent B: Amelia (Code Standards Scan)

Persona file: `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/dev.md`

Amelia's job:
1. Sample 3-5 source files representative of the codebase (controllers, services, models/entities)
2. Identify coding conventions (naming, package structure, error handling patterns)
3. Identify anti-patterns present (things agents should avoid when working in this repo)
4. Identify testing patterns (unit vs integration, mocking framework, test naming)
5. Note any linting or formatting tooling present

Amelia writes to `/tmp/onboard-{repo-name}/amelia-standards.md` in this format:
```markdown
## Language & Framework
Java 17 / Spring Boot 3.x

## Build & Run
- Build: `mvn clean install -DskipTests`
- Test: `mvn test`
- Run locally: `mvn spring-boot:run`
- Lint/format: (if applicable)

## Code Conventions
- Naming: camelCase methods, PascalCase classes, SCREAMING_SNAKE_CASE constants
- Package structure: `com.example.{feature}.{layer}` (controller / service / repository)
- Error handling: GlobalExceptionHandler, specific exception types per domain

## Testing Patterns
- Framework: JUnit 5 + Mockito (strict mode)
- Naming: `should{Behavior}When{Condition}()`
- Mocking: `@ExtendWith(MockitoExtension.class)` — no SpringBootTest in unit tests

## Anti-Patterns (do not introduce)
- Bullet list of patterns seen in the code that agents should NOT copy or extend

## Key Directories
| Directory | Purpose |
|-----------|---------|
| `src/main/java/...` | Application source |
| `src/test/java/...` | Tests |
| `src/main/resources/` | Config files |
```

### Agent C: Leo (Spec Gap Analysis)

Persona file: `~/Developer/supervisr-ai/project-management/_bmad/bmm/agents/spec-coach.md`

Leo's job:
1. Read any existing specs, README, or docs in the repo
2. Identify what behavioral guarantees the service provides (Given/When/Then language)
3. Flag capabilities that exist in code but have no documented spec
4. Flag any spec documents that describe behavior not present in the code
5. List the top 3 spec gaps that should become AC in the next ticket

Leo writes to `/tmp/onboard-{repo-name}/leo-spec-gaps.md` in this format:
```markdown
## Documented Capabilities
- Given {trigger}, When {condition}, Then {outcome}
- (one per known behavior)

## Spec Gaps (behavior exists, no spec)
1. {capability description} — found in `path/to/file.java:lineN`
2. ...

## Ghost Specs (spec exists, no code)
1. {spec claim} — source: `docs/README.md:lineN`

## Top 3 ADR Candidates
1. {decision that should be recorded} — rationale: ...
```

---

## Phase 3 — Assemble Scaffold

After all three agents complete, the orchestrator assembles the scaffold by writing each file in sequence.

### 3.1 — CLAUDE.md (repo root)

Write `{repo_path}/CLAUDE.md`. Use Amelia's build/test commands and key directories. Use Winston's service purpose and cross-service relationships. If a CLAUDE.md already exists, read it first and merge/enhance rather than overwrite.

Include this structure:

```markdown
# CLAUDE Context: {Repo Name}

## Service Purpose
{Winston's one-sentence description}

## Build & Run
{Amelia's build, test, run commands — verbatim}

## Key Directories
{Amelia's directory table}

## Coding Standards
{Amelia's conventions, anti-patterns, testing patterns — condensed}

## Architecture
{Winston's architectural pattern and entry points — condensed}

## Cross-Service Relationships
{Winston's relationship table}

## Where to Look

| Need | Location |
|------|----------|
| System wiring, data flows | `agent-os/specs/architecture/` |
| Coding standards and patterns | `agent-os/standards/` |
| Architecture Decision Records | `docs/adr/INDEX.md` |
| Architecture deep-dives | `docs/architecture/` |
| Cross-service flows (big picture) | Bibliotheque `stack/` |
```

### 3.2 — agent-os/index.md

Write `{repo_path}/agent-os/index.md`. This is the agent-facing service overview. Present-tense, operational. No past-tense "we decided X" language.

```markdown
# {Service Name} — agent-os Index

## Purpose
{one paragraph from Winston}

## Capabilities
{bullet list of what the service does}

## API Surface
{entry points from Winston — HTTP routes, PubSub topics, GraphQL queries}

## Configuration
{key environment variables or config files agents need to know about}

## Related Services
| Service | Relationship | Big Picture |
|---------|-------------|-------------|
{Winston's relationship table}

## Documentation Index
| Document | Purpose |
|----------|---------|
| [Architecture](specs/architecture/index.md) | System wiring and patterns |
| [Standards](standards/index.md) | Coding conventions for this repo |
| [ADRs](../docs/adr/INDEX.md) | Architecture decisions |
```

### 3.3 — agent-os/specs/architecture/index.md

Write `{repo_path}/agent-os/specs/architecture/index.md`. Synthesized from Winston's output.

Content: architectural pattern, entry points, external dependencies, data flow overview. End with one line: "Architecture Decision Records: [docs/adr/INDEX.md](../../../docs/adr/INDEX.md)"

### 3.4 — agent-os/standards/index.md

Write `{repo_path}/agent-os/standards/index.md`. Verbatim from Amelia's output, reformatted as a standards reference doc. Include a "Do Not" section derived from Amelia's anti-patterns.

### 3.5 — agent-os/product/index.md

Write `{repo_path}/agent-os/product/index.md`. From Leo's output: documented capabilities as Given/When/Then statements. Include spec gaps as a "Gaps Requiring AC" section.

### 3.6 — docs/README.md

```markdown
# {Service Name} — Documentation

This folder contains long-lived reference documentation for {service name}.
Standard: [Three-Layer Documentation Standard](link-to-standard)

## Subfolders
- `adr/` — Architecture Decision Records (past decisions, immutable history)
- `architecture/` — Design studies, deep-dives, research spikes
```

### 3.7 — docs/INDEX.md

One-line entry per doc currently in docs/. If docs/ is empty, create the index with a placeholder:
```markdown
# {Service Name} docs/ Index

| File | Purpose | Date |
|------|---------|------|
| (empty — add entries here as docs are created) | | |
```

### 3.8 — docs/adr/INDEX.md

ADR registry. If no ADRs exist yet:
```markdown
# Architecture Decision Records — {Service Name}

| ID | Title | Status | Scope | Date |
|----|-------|--------|-------|------|
| (empty — ADRs will be added here as decisions are made) | | | | |
```

If Winston flagged ADR candidates, add a comment section listing them as "Candidate ADRs (not yet formal)".

---

## Phase 4 — .repo-index.yaml Registration

Determine if this repo belongs to a known org:
- Path contains `supervisr-ai` -> Supervisr org
- Path contains `grp-beklever-com` -> Klever org

If yes, update `/Users/gabrielamyot/Developer/supervisr-ai/project-management/.repo-index.yaml`:

1. Read the current file
2. Add an entry for the new repo under the correct service group. Pattern:
   ```yaml
   services:
     {service-slug}:
       path: {absolute_repo_path}
       language: {detected language}
       framework: {detected framework}
       default_branch: {detected branch}
       onboarded: {YYYY-MM-DD}
   ```
3. Write the updated file

If the repo does not belong to a known org, skip this step and note it in the summary.

---

## Phase 5 — Commit

Commit all created files immediately. Untracked files are lost on `git clean`, checkout, or repo switches.

Stage only the files this skill created:
```bash
git -C <repo_path> add CLAUDE.md agent-os/ docs/ .gitignore
```

Commit with HEREDOC body:
```bash
git -C <repo_path> commit -m "$(cat <<'EOF'
{TICKET-ID}: onboard repo — agent-os scaffold, CLAUDE.md, docs/adr/

Bootstraps {service-name} with the full three-layer documentation standard.

- CLAUDE.md: repo purpose, build commands, coding standards, routing table
- agent-os/index.md: present-tense operational overview, Related Services
- agent-os/specs/architecture/: architectural pattern, entry points, dependencies
- agent-os/standards/: coding conventions and anti-patterns (Amelia scan)
- agent-os/product/: capability specs and gap analysis (Leo scan)
- docs/adr/INDEX.md: ADR registry (empty, ready for first decisions)
- .gitignore: credential patterns verified/added
EOF
)"
```

After committing, verify with `git -C <repo_path> status` that the working tree is clean.

---

## Phase 6 — Bibliotheque Inbox

Write a brief knowledge note to the Bibliotheque inbox for the Librarian to process:

File: `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/inbox/{YYYY-MM-DD}-{service-name}-onboarding.md`

```markdown
# {Service Name} — Onboarded {YYYY-MM-DD}

## Service Summary
{Winston's one-sentence purpose}

## Stack
{Language, framework, key dependencies}

## Cross-Service Relationships
{Winston's relationship table}

## Service-Local Documentation
| Document | Location |
|----------|---------|
| agent-os index | `{repo_path}/agent-os/index.md` |
| Architecture | `{repo_path}/agent-os/specs/architecture/index.md` |
| Standards | `{repo_path}/agent-os/standards/index.md` |
| ADRs | `{repo_path}/docs/adr/INDEX.md` |

## Spec Gaps (for backlog)
{Leo's top 3 gaps}
```

This note will be picked up by `/bibliotheque-librarian` during the next catalog run.

---

## Phase 7 — Summary Report

Print to the user:

```
## Onboarding Complete: {service-name}

### Files Created
- {repo_path}/CLAUDE.md
- {repo_path}/agent-os/index.md
- {repo_path}/agent-os/specs/architecture/index.md
- {repo_path}/agent-os/standards/index.md
- {repo_path}/agent-os/product/index.md
- {repo_path}/docs/README.md
- {repo_path}/docs/INDEX.md
- {repo_path}/docs/adr/INDEX.md

### Commit
{git commit hash}

### .gitignore
{CLEAN (all patterns present) | UPDATED (N patterns added)}

### .repo-index.yaml
{REGISTERED | SKIPPED (unknown org)}

### Spec Gaps Flagged (Leo)
1. {gap 1}
2. {gap 2}
3. {gap 3}

### ADR Candidates (Winston)
{list or "none flagged"}

### Next Steps
- Run /doc-standards-migrate if existing ADRs were found in wrong locations
- Review Leo's spec gaps and create tickets for the top priority
- Update Bibliotheque if this service has cross-org impact
```

---

## Key Rules

- **Commit before claiming done.** Untracked files are wiped by git clean, checkout, or repo switches.
- **ADRs always go in docs/adr/.** Never in agent-os/. If any are found in agent-os/ during the scan, surface them and recommend running /doc-standards-migrate.
- **agent-os/ is present-tense only.** No historical decisions. No "we decided X" language. Only "the system does X."
- **Never guess build commands.** Read the manifest. If no build command is detectable, write "UNKNOWN — check README" in CLAUDE.md.
- **Never modify existing CLAUDE.md blindly.** If a CLAUDE.md exists, read it first, then merge/enhance rather than overwrite.
- **DAC repos: default branch is dev.** Any repo path containing `grp-dac` uses dev, not main.
- **.gitignore check is non-negotiable.** Do this in Phase 0, before any other write. Secrets never committed.
- **Never pipe git commands.** Run each sequentially.
- **Subagent outputs go to /tmp/ first.** The orchestrator assembles the final scaffold. Agents do not write directly to the repo.
