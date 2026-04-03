# SBE: Persona Context Loading

## SBE-CE-01: Custom persona loads repo context on activation

**Given** Atlas (data-engineer) is activated in the lead-lifecycle-service repo
**And** the repo has `agent-os/index.md` with specs, ADRs, and standards
**When** Atlas reaches activation step 4 (CONTEXT LOADING)
**Then** Atlas reads `agent-os/index.md` to discover available context
**And** Atlas reads relevant standards (e.g., `standards/datastore/query-pattern.md`) before answering Datastore questions
**And** Atlas does NOT reference technologies or patterns not present in the repo's agent-os

## SBE-CE-02: Custom persona loads org-level contracts

**Given** Atlas is activated in any Supervisr AI repo
**When** Atlas needs to understand data models or service contracts
**Then** Atlas reads `project-management/documentation/architecture/contracts/` for global contracts
**And** Atlas adapts recommendations to the actual data model (not a generic one)

## SBE-CE-03: Persona works without agent-os (graceful degradation)

**Given** Atlas is activated in a repo with no `agent-os/` directory
**When** Atlas reaches activation step 4
**Then** Atlas skips agent-os loading without error
**And** Atlas falls back to general data engineering principles from its persona definition
**And** Atlas informs the user that no local specs were found

## SBE-CE-04: No baked-in knowledge survives persona creation

**Given** a new custom persona is being created via the agent-builder
**When** the creator includes org-specific facts (entity names, query patterns, service URLs)
**Then** adversarial review flags these as violations of ADR-001
**And** the facts are removed in favor of a context-loading activation step

## SBE-CE-05: Persona context loading does not duplicate desk infrastructure

**Given** someone proposes creating a `_bmad/desks/{persona}/` folder
**When** the proposal is evaluated
**Then** it is rejected per ADR-001
**And** the proposer is directed to use agent-os and CLAUDE.md on-demand tables instead
