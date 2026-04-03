# ADR-001: Persona Context Loading Strategy

## Status

**Accepted** (2026-03-10)

## Context

When creating custom BMAD personas (Leo the Spec Coach, Atlas the Data Engineer), a design question arose: how should personas acquire domain-specific knowledge about the repos and orgs they operate in?

### Option A: Baked-In Knowledge ("Fat Persona")

Embed `<knowledge>` blocks directly in the persona file with org-specific facts (tech stack, entity schemas, query patterns, service topology).

**Pros:** Persona is self-contained, works immediately without loading steps.
**Cons:** Couples persona to a specific org. Stale the moment any fact changes. Maintenance nightmare across 3+ orgs.

### Option B: Per-Persona Context Folders ("Desk Idea")

Create a folder per persona in each org's project-management (e.g., `project-management/_bmad/desks/atlas/`) containing curated context files the persona loads on activation.

**Pros:** Separates persona definition from domain knowledge. Context is org-specific and co-located with the org's docs.
**Cons:** Creates a parallel context system alongside agent-os and CLAUDE.md on-demand tables. Three systems doing the same job. Desks would need maintenance, indexing, and a loading protocol that duplicates existing infrastructure.

### Option C: Dynamic Context Loading from Existing Infrastructure ("Lean Persona")

Persona files define HOW to think (principles, activation protocol, menu, prompts). On activation, an explicit step loads context from existing sources: repo agent-os/index.md, org documentation/architecture/, repo CLAUDE.md on-demand tables.

**Pros:** Zero new infrastructure. Persona works across any org that has agent-os. Context is always fresh (reads live files). Single source of truth maintained.
**Cons:** Persona needs a well-defined loading step. First activation is slightly slower (reads files before responding).

## Decision

**Option C: Dynamic Context Loading.**

Personas define thinking patterns and principles. Domain knowledge comes from the repo's agent-os, the org's documentation/, and the repo's CLAUDE.md on-demand context tables. No new infrastructure is created.

### Implementation

Each custom persona includes an activation step like:

```xml
<step n="4">CONTEXT LOADING: Before any substantive work, load local context using progressive disclosure:
    - Read the current repo's agent-os/index.md (if it exists) for specs, ADRs, standards, and contracts
    - Read the org's project-management/documentation/architecture/ for global contracts
    - Read the repo's CLAUDE.md for on-demand context tables and tech stack
    - Adapt your domain knowledge to the LOCAL stack. Do not assume any specific technology.
</step>
```

### Why Not the Desk Idea

The "desk" concept (per-persona context folders) was proposed and evaluated. It was rejected because:

1. **agent-os already serves this purpose.** Each repo's `agent-os/` contains specs, ADRs, standards, and contracts organized by topic. This IS the desk, it just doesn't live under `_bmad/`.
2. **CLAUDE.md on-demand tables already route to the right files.** The trigger-to-file mapping (e.g., "writing Java code" → `java-standards.md`) is the loading protocol. No need for a persona-specific one.
3. **Three systems doing one job is worse than one.** Adding desks alongside agent-os and CLAUDE.md creates confusion about which is authoritative.
4. **Maintenance cost is real.** Each desk would need curation, indexing, and freshness checks. agent-os already has this via `/push-adr` and spec-driven development workflow.

The desk idea is a good intuition (personas need domain context), but the solution already exists. The missing piece was an explicit activation step in the persona telling it to load from existing sources.

## Consequences

- Custom personas (Leo, Atlas) use dynamic context loading via activation step
- No `<knowledge>` blocks in persona files
- No per-persona context folders (desks)
- Personas work across any org/repo that has agent-os without modification
- If a repo lacks agent-os, the persona gracefully degrades (uses general principles only)

## Related

- Atlas v2 data-engineer.md: first persona to implement this pattern
- Leo v2 spec-coach.md: uses similar context-aware prompts
- BMAD Persona Guide: `documentation/process/bmad-persona-guide.md`
