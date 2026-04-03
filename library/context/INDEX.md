# Context Files Index

On-demand context files loaded by CLAUDE.md trigger rules. Now part of the library at `library/context/`. Each file is self-contained, loaded only when its trigger condition matches.

## Trigger Map

| File | Trigger | Summary |
|------|---------|---------|
| `workspace-map.yaml` | Navigating orgs/projects, starting tickets | Org/project roots, paths, conventions for Personal, Klever, Supervisr |
| `shipping-workflow.md` | Tagging, shipping, deploying, MRs, CI/CD | Pre-tag checklist, version format, JIB build, full deploy sequence |
| `java-standards.md` | Writing/reviewing Java code | Mockito strictness, test naming, structure, helper methods |
| `claude-md-authoring.md` | Editing any CLAUDE.md file | Token budget, deduplication, extraction rules, scope guidelines |
| `context-engineering.md` | Long-running agents, compaction, context limits | Three levers (compaction, notes, sub-agents), mental models, mitigations |
| `ticket-initialization.md` | Initializing tickets, organizing folders | Phase 1 (Jira fetch), Phase 2 (work init with reports scaffold) |
| `ticket-quality-standards.md` | Creating tickets, writing AC, reviewing quality | User story format, BDD acceptance criteria, litmus test |
| `gemini-cli-reference.md` | Using Gemini CLI for codebase analysis | File/directory inclusion with @ notation, usage examples |
| `tools-catalog.md` | Creating PRDs, tickets, contracts, changelogs | Project management tools and ADR template locations |
| `swarm-diagnostics.md` | Multi-service debugging, parallel investigation | Failure chain mapping, parallel haiku agents, Opus synthesis |
| `autopilot-session-state.md` | Resuming supervisr-autopilot work | Branch, commits, 10-phase architecture status, design decisions |
