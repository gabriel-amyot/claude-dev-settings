# Library Catalog

Master index for the context-engineering knowledge base.
95 documents across 7 sections. Every filename is self-documenting: domain, purpose, and key concepts are encoded in the name.

**Navigation pattern:** Read this catalog, pick a floor, read its INDEX.md, then selectively read individual files. Never bulk-load.

---

## Floor Plan

| Floor | Section | Books | What lives here |
|-------|---------|------:|-----------------|
| **architecture/** | decisions, patterns, vision | 9 | ADRs, architecture patterns, north-star vision docs |
| **research/** | agent-systems, memory-systems, strategic-planning, security | 11 | Raw research papers, deep analysis, strategic plans |
| **practices/** | development, testing, debugging, collaboration, writing, planning, quality, standards, workflows | 28 | How-to guides, methodologies, checklists, workflow definitions |
| **process/** | — | 3 | PRD creation, task generation, task management protocols |
| **operations/** | troubleshooting, known-issues | 8 | Supervisr infra topology (Datastore, Auth0, services), guardrails, test harness, troubleshooting |
| **archive/** | retired-agents, superpowers-plugin | 29 | Retired agents, plugin snapshots, test cases, historical artifacts |
| **context/** | — | 11 | On-demand context files loaded by CLAUDE.md triggers (workspace map, shipping, Java, tickets, tools) |

---

## Topic Cross-Reference

Use this when you know WHAT you need but not WHERE it lives.

### Agent Architecture
- North star: `architecture/vision/agent-harness-north-star-industry-patterns-gap-analysis.md`
- Roadmap: `architecture/vision/agent-harness-phased-roadmap-ralph-loop-to-cloud.md`
- Failure modes: `architecture/vision/agent-harness-known-failure-catalog.yaml`
- Deep research (39 KB): `research/agent-systems/paradigm-shifts-context-engineering-deterministic-gates-multi-agent.md`
- Pattern (Minions): `architecture/patterns/minions-isolated-environments-blueprint-interleaving.md`
- Pattern (Gemini): `architecture/patterns/gemini-cache-stability-working-memory-externalization.md`
- Pattern (Pre-flight): `architecture/patterns/pre-flight-heuristics-hierarchical-coordination.md`

### Memory Systems
- ADR: `architecture/decisions/memory-management-disable-auto-consolidate-context.md`
- Survey (22 KB): `research/memory-systems/ai-agent-memory-architectures-patterns-survey.md`
- Embedding vs Files (34 KB): `research/memory-systems/embedding-databases-vs-indexed-file-structures.md`
- QMD concept: `research/memory-systems/query-mapping-document-semantic-memory-retrieval.md`
- Future directions: `research/memory-systems/future-exploration-multi-index-graph-hybrid-evaluation.md`

### Context Engineering
- Persona loading ADR: `architecture/decisions/persona-context-dynamic-loading-from-agent-os.md`
- Persona SBE: `architecture/patterns/persona-context-repo-discovery-graceful-degradation.md`
- Principles (on-demand): `../context/context-engineering.md`
- CLAUDE.md authoring (on-demand): `../context/claude-md-authoring.md`

### Code Quality
- Review checklist: `practices/quality/code-review-priority-checklist.md`
- Reviewer persona: `practices/collaboration/code-reviewer-persona-guidelines.md`
- Review requesting: `practices/collaboration/requesting-code-review-preparation-guide.md`
- Review receiving: `practices/collaboration/receiving-code-review-incorporating-feedback.md`
- Defense-in-depth: `practices/quality/defense-in-depth-layered-security-patterns.md`
- Commit format: `practices/standards/commit-message-conventional-format.md`

### Testing
- TDD methodology: `practices/development/test-driven-development-red-green-refactor.md`
- TDD workflow: `practices/workflows/tdd-workflow-test-first-quality-gates.md`
- Anti-patterns: `practices/testing/testing-anti-patterns-and-refactoring.md`
- Skill testing: `practices/testing/testing-skills-with-subagent-harnesses.md`
- Verification: `practices/testing/verification-before-completion-protocols.md`

### Debugging
- Systematic methodology: `practices/debugging/systematic-debugging-failure-trace-hypothesis.md`
- Root cause analysis: `practices/debugging/root-cause-tracing-investigation-artifacts.md`
- Find-polluter utility: `practices/debugging/find-polluter.sh`

### Writing and Communication
- Writing skills (622 lines): `practices/writing/writing-skills-persuasion-clarity-structure.md`
- Anthropic best practices (1150 lines): `practices/writing/anthropic-best-practices-prompt-design.md`
- Persuasion principles: `practices/writing/persuasion-principles-communication.md`

### Strategic Planning
- Reading order: `research/strategic-planning/navigation-guide-reading-order.md`
- Strategic analysis (793 lines): `research/strategic-planning/ultrathink-goal-alignment-risk-mitigation-timeline.md`
- Phase 0 plan (1507 lines): `research/strategic-planning/phase-0-detailed-execution-roadmap.md`
- Model feedback: `research/strategic-planning/opus-4-1-feedback-strategic-recommendations.md`

### Development Workflow
- Plan writing: `practices/planning/writing-effective-implementation-plans.md`
- Plan execution: `practices/planning/executing-pre-written-plans.md`
- Branch finishing: `practices/development/finishing-development-branch-cleanup-merge.md`
- Git worktrees: `practices/development/using-git-worktrees-isolated-branches.md`
- Lean workflow: `practices/workflows/lean-workflow-minimal-process-rapid-iteration.md`
- Parallel agents: `practices/collaboration/dispatching-parallel-agents-coordination.md`
- Subagent dev: `practices/development/subagent-driven-development-specialized-tasks.md`

### Infrastructure & Operations
- Datastore topology (all envs): `operations/supervisr-datastore-topology-environments.md`
- Auth0 tenants and M2M apps: `operations/supervisr-auth0-topology-m2m-apps.md`
- Infrastructure guardrails (incident-driven): `operations/supervisr-infrastructure-guardrails.md`
- Service graph and deployment: `operations/supervisr-service-graph-deployment.md`
- Test harness gotchas: `operations/supervisr-test-harness-gotchas.md`

### Operational Context (loaded via CLAUDE.md triggers)
See `context/INDEX.md` for the full trigger map. These are small, self-contained files designed for just-in-time loading.

Key files:
- Workspace navigation: `context/workspace-map.yaml`
- Shipping/deploy: `context/shipping-workflow.md`
- Java standards: `context/java-standards.md`
- Context engineering: `context/context-engineering.md`
- Ticket quality: `context/ticket-quality-standards.md`
- CLAUDE.md authoring: `context/claude-md-authoring.md`

---

## Librarian Protocol

When adding new books:
1. Choose the correct floor and section based on content type
2. Name the file: `{domain}-{purpose}-{key-concepts}.md` (lowercase, hyphens)
3. Update the section's `INDEX.md` with a one-liner
4. If cross-cutting, add to the Topic Cross-Reference above
5. Run `/index-context library/` to regenerate indexes if bulk additions were made
