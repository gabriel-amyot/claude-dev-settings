# Agent Harness Library

Cross-org, cross-project knowledge base for the Claude agent harness. Distilled operational knowledge, architecture decisions, engineering practices, and infrastructure reference. This is the universal layer — things that apply regardless of org.

**Org-specific knowledge lives elsewhere:**
- Klever: `~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/INDEX.md`
- Supervisr.AI: `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/INDEX.md`
- Global on-demand context: `~/.claude/library/INDEX.md`

**Navigation pattern:** Read this INDEX → go to a section INDEX → read individual files. Never bulk-load.

Last updated: 2026-05-02

---

## I Need to Understand Something

| Question | Where to Look |
|----------|--------------|
| What is the overall agent harness architecture? | [architecture/vision/agent-harness-north-star-industry-patterns-gap-analysis.md](architecture/vision/agent-harness-north-star-industry-patterns-gap-analysis.md) |
| What is the phased roadmap for the harness? | [architecture/vision/agent-harness-phased-roadmap-ralph-loop-to-cloud.md](architecture/vision/agent-harness-phased-roadmap-ralph-loop-to-cloud.md) |
| What agents, skills, and plugins are installed? | [operations/setup-snapshot-plugins-agents-skills-backlog.md](operations/setup-snapshot-plugins-agents-skills-backlog.md) |
| How should I think about agent memory? | [research/memory-systems/INDEX.md](research/INDEX.md) — 4 files covering architectures, embedding vs files, QMD |
| What context engineering patterns apply? | [context/context-engineering.md](context/context-engineering.md) |
| What are known failure modes of the harness? | [architecture/vision/agent-harness-known-failure-catalog.yaml](architecture/vision/agent-harness-known-failure-catalog.yaml) |
| How do I write effective plans? | [practices/planning/writing-effective-implementation-plans.md](practices/planning/writing-effective-implementation-plans.md) |
| What testing practices apply? | [practices/testing/INDEX.md](practices/INDEX.md) |
| What is the strategic direction for the platform? | [research/strategic-planning/navigation-guide-reading-order.md](research/strategic-planning/navigation-guide-reading-order.md) — start here |

---

## I Am Blocked by an Error or Situation

| Symptom | Likely Cause | Go Here |
|---------|-------------|---------|
| Git push behind IAP fails with "device not configured" | TTY needed for credential helper, not available in agent context | [operations/troubleshooting/git-iap-push-device-not-configured-tty-fix.md](operations/troubleshooting/git-iap-push-device-not-configured-tty-fix.md) |
| Agent reports task complete but test/behavior path is wrong | False completion anti-pattern: agent found alternate code path | [operations/known-issues/test-harness-false-completion-path-divergence.md](operations/known-issues/test-harness-false-completion-path-divergence.md) |
| pickup-ticket agent missing spec clarifications from Jira | Phase 6 skips `jira/comments/` — known gap | [operations/known-issues/pickup-ticket-phase6-missing-jira-comments.md](operations/known-issues/pickup-ticket-phase6-missing-jira-comments.md) |
| Tests pass locally but fail in unexpected ways | Testing anti-patterns: over-mocking, flaky setup | [practices/testing/testing-anti-patterns-and-refactoring.md](practices/testing/testing-anti-patterns-and-refactoring.md) |
| Long agent session losing coherence / drifting | Context window pressure or compaction drift | [context/context-engineering.md](context/context-engineering.md) |
| Supervisr Datastore wiped or wrong data | Env topology confusion | [operations/supervisr-datastore-topology-environments.md](operations/supervisr-datastore-topology-environments.md) |
| Auth/M2M issues on Supervisr services | Wrong tenant or M2M app | [operations/supervisr-auth0-topology-m2m-apps.md](operations/supervisr-auth0-topology-m2m-apps.md) |

---

## I Need to Do Something

| Task | Where to Look |
|------|--------------|
| Debug a hard problem systematically | [practices/debugging/systematic-debugging-failure-trace-hypothesis.md](practices/debugging/systematic-debugging-failure-trace-hypothesis.md) |
| Write a good implementation plan | [practices/planning/writing-effective-implementation-plans.md](practices/planning/writing-effective-implementation-plans.md) |
| Execute an existing plan | [practices/planning/executing-pre-written-plans.md](practices/planning/executing-pre-written-plans.md) |
| Dispatch parallel agents effectively | [practices/collaboration/dispatching-parallel-agents-coordination.md](practices/collaboration/dispatching-parallel-agents-coordination.md) |
| Review code with depth | [practices/collaboration/requesting-code-review-preparation-guide.md](practices/collaboration/requesting-code-review-preparation-guide.md) |
| Finish and merge a feature branch | [practices/development/finishing-development-branch-cleanup-merge.md](practices/development/finishing-development-branch-cleanup-merge.md) |
| Write and ship a skill | [practices/development/subagent-driven-development-specialized-tasks.md](practices/development/subagent-driven-development-specialized-tasks.md) |
| Create a PRD | [process/product-requirements-document-creation.md](process/product-requirements-document-creation.md) |
| Set up CLAUDE.md for a new repo | [context/claude-md-authoring.md](context/claude-md-authoring.md) |
| Navigate to the right org/project | [context/workspace-map.yaml](context/workspace-map.yaml) |
| Ship a Supervisr service | [context/shipping-workflow.md](context/shipping-workflow.md) |

---

## Sections

Each section has its own INDEX.md with full contents. Read the section INDEX before diving into files.

- **[architecture/](architecture/INDEX.md)** — ADRs, architecture patterns, north-star vision. Read when designing or evaluating structural decisions.
- **[research/](research/INDEX.md)** — Deep research: agent systems, memory architectures, strategic planning, security. Heavy reading; informs decisions but not prescriptive.
- **[practices/](practices/INDEX.md)** — How to do things well: development, testing, debugging, collaboration, writing, planning, quality, standards, workflows. 28 files.
- **[process/](process/INDEX.md)** — How work flows: PRD creation, task generation, task management. Powers `/create-prd`, `/generate-tasks`, `/process-task-list`.
- **[operations/](operations/INDEX.md)** — Infrastructure reference: Supervisr topology (Datastore, Auth0, services), guardrails, test harness, troubleshooting, known issues.
- **[context/](context/INDEX.md)** — On-demand context files loaded by CLAUDE.md trigger rules. Do not bulk-load. Each file is self-contained.
- **[archive/](archive/INDEX.md)** — Retired agents, plugin snapshots, historical artifacts. Pattern mine only.
- **[inbox/](inbox/INDEX.md)** — Raw captures awaiting promotion. Land nuggets here; promote on review.

---

## Contributing

After adding a file to any section:
1. Update that section's INDEX.md with a one-line summary
2. If it answers a common question, add a row to the appropriate table above
3. If cross-cutting, add to CATALOG.md Topic Cross-Reference
4. Update "Last updated" date above

Librarian protocol (naming): `{domain}-{purpose}-{key-concepts}.md` — lowercase, hyphens, no dates in filenames.
