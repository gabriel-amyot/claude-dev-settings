# push-adr — Push Architectural Decisions to agent-os

Formalize an architectural decision by creating an ADR and updating all related specifications in a repository's `agent-os/` tree.

## Usage

```
/push-adr                                     # Interactive — asks for repo and decision context
/push-adr <repo-path>                         # Target a specific repo
/push-adr "<decision summary>"                # Provide decision context as hint
/push-adr <repo-path> "<decision summary>"    # Both repo and decision
```

## What It Does

1. **Creates ADR** in `agent-os/specs/architecture/decisions/` following the repo's existing conventions
2. **Updates API contracts** (`agent-os/specs/api-contracts/index.md`) — diagrams, schemas, version
3. **Updates standards** (`agent-os/standards/`) — code examples, patterns, references
4. **Updates ADR index** (`index.yml`) with new entry
5. **Verifies cross-references** across all updated documents

## When to Use

After completing an implementation that involves:
- Changing how services communicate (transport, protocol, format)
- Adding/removing dependencies or integrations
- Changing data models or event formats
- Making a significant architectural choice that future developers should know about

## Process

### Step 1: Gather Context

If not provided via arguments, ask the user:

1. **Which repository?** (absolute path)
2. **What was decided?** (1-2 sentence summary)
3. **What was changed?** (files modified, before/after pattern)
4. **Ticket context?** (optional — for project-management report)

### Step 2: Spawn push-adr Agent

Use the Task tool to spawn the `push-adr` agent:

```
Task(
  subagent_type="push-adr",
  prompt="Push architectural decision to agent-os.
    repo_path: {repo_path}
    decision_summary: {decision}
    implementation_summary: {what changed}
    ticket_id: {ticket_id or 'none'}
  "
)
```

The agent handles all 6 phases autonomously: Discovery → ADR → Contracts → Standards → Cross-References → Summary.

### Step 3: Review Output

Present the agent's summary to the user. Offer to make adjustments if needed.

## Examples

### After switching HTTP to Pub/Sub
```
/push-adr ~/Developer/supervisr-ai/app/micro-services/lead-lifecycle-service "Unified all lead events to use Pub/Sub instead of HTTP POST for consistency with event-driven architecture"
```

### After adding a new service dependency
```
/push-adr ~/Developer/supervisr-ai/app/micro-services/retell-service "Added dependency on lead-lifecycle-service for availability checks via GraphQL"
```

### Interactive mode
```
/push-adr
> Which repository? ~/Developer/.../lead-lifecycle-service
> What was decided? Replaced WebClient HTTP calls with PubSubTemplate for lead events
> What changed? ComplianceErsClient now uses PubSubTemplate + YADTO format
> Ticket? SPV-8
```

## Dependencies

- Target repo must have `agent-os/` directory
- Existing ADRs help establish conventions (but not required)
- Agent reads actual source code to verify documentation accuracy

## Side effects

- The target repo(s)'s 'agent-os' are updated with the project-management high level architecture docs.
- The project-management documents are kept intact (not deleted!) The only exception is if a conflict is identified when trickling down the ard to the repo level. But his scenario requires a subsequent process, and should never be done without consulting the caller
