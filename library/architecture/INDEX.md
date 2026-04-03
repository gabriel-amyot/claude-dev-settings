# Architecture

How systems are designed. ADRs, patterns, and vision documents.

## Sections

### decisions/
Architectural Decision Records. Each captures a specific design choice with context, alternatives considered, and rationale.

| File | Summary |
|------|---------|
| `memory-management-disable-auto-consolidate-context.md` | Disable Claude auto-memory, consolidate into file-based context strategy |
| `persona-context-dynamic-loading-from-agent-os.md` | Load persona context dynamically from agent-os and CLAUDE.md (not baked-in) |

### patterns/
Reusable architecture patterns. Each describes a structural approach with trade-offs.

| File | Summary |
|------|---------|
| `minions-isolated-environments-blueprint-interleaving.md` | Minions pattern: isolated agent environments, blueprint interleaving, multi-tier validation |
| `gemini-cache-stability-working-memory-externalization.md` | Gemini-derived: cache stability, working memory externalization, intent governance |
| `pre-flight-heuristics-hierarchical-coordination.md` | Pre-flight heuristics, context optimization, hierarchical coordination, hard-coded nodes |
| `persona-context-repo-discovery-graceful-degradation.md` | SBE: repo agent-os discovery, org-level contracts, graceful degradation when no agent-os |

### vision/
North-star documents. Living architecture, roadmaps, and known failure modes.

| File | Summary |
|------|---------|
| `agent-harness-north-star-industry-patterns-gap-analysis.md` | Living architecture: 9 industry patterns, 7 principles, 15 agents, 40+ skills, gap analysis (241 lines) |
| `agent-harness-phased-roadmap-ralph-loop-to-cloud.md` | 3-phase roadmap: ralph-loop primitive, semantic tools, cloud (155 lines) |
| `agent-harness-known-failure-catalog.yaml` | Known failures: GitLab down, context exhaustion, port conflicts, stale creds (with fallbacks) |
