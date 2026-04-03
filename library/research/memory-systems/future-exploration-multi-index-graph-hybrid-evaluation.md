# Memory Management — Future Exploration

**Created:** 2026-02-27
**Status:** Backlog — investigate when current setup shows limitations

---

## Investigate: RAG-based Memory with Vector DB

**What:** Use a vector database (e.g., Supabase pgvector, Chroma, Pinecone) to store and retrieve project knowledge via semantic search instead of flat file loading.

**Why interesting:** Current system relies on keyword grep and manual file reading. A vector DB would allow "find me everything related to webhook retry logic" to surface relevant ADRs, code comments, and past decisions without knowing exact file locations.

**Concerns:** Infrastructure overhead, embedding cost, keeping embeddings in sync with source of truth. May be solving a problem `/tribal-knowledge` already handles well enough.

---

## Investigate: Graph Database for Entity Relationships

**What:** Use a graph DB (e.g., Neo4j, Supabase + pg_graphql) to model service relationships, ownership, dependencies, and decision chains as a queryable graph.

**Why interesting:** Research mentions Mem0/Zep-style knowledge graphs for "relational memory." Would enable queries like "what services are affected if we change the auth token format?" that flat files can't answer efficiently.

**Concerns:** Heavy setup, another system to maintain. The workspace-map.yaml + agent-os specs may cover 80% of this with zero infrastructure.

---

## Investigate: MCP Memory Servers

**What:** Use existing MCP servers (e.g., `@anthropic/memory-server`, community MCP tools) to give Claude persistent memory via tool calls rather than file-based memory.

**Why interesting:** MCP tools integrate natively with Claude Code. Could provide structured memory operations (save, query, update, delete) without custom skills. Some MCP memory servers support semantic search.

**Concerns:** Another dependency. Need to evaluate whether it provides meaningful capability beyond what CLAUDE.md + on-demand context files already do. Vendor lock-in risk.

---

## Investigate: Supabase as Unified Memory Backend

**What:** People report using Supabase as a combined vector store + graph + structured data backend for AI agent memory. Supports pgvector for embeddings, row-level security, real-time subscriptions.

**Why interesting:** Single infrastructure piece for multiple memory needs. Could serve as both the vector DB and the graph DB from the items above.

**Concerns:** Overkill for current scale. Worth investigating only if flat-file memory proves insufficient after 2-3 months of use.

---

## Investigate: Re-enabling Platform Memory with Scope-Switching

**What:** If Claude Code adds the ability for spawned agents to get their own project scope (feature request identified in this session), re-evaluate whether platform auto-memory becomes useful.

**Trigger:** Claude Code release notes mentioning agent scope, memory scope, or project context for spawned agents.

**Current blocker:** Spawned agents inherit parent's project scope. Confirmed by testing — `cd` before spawn does not change the agent's memory scope.

---

## Investigate: Pyramid Summaries (StrongDM Software Factory)

**What:** Multi-resolution summarization, like Mapbox vector tiles for context. Provide zoom levels so agents can load the right fidelity of information for their task.

**Why interesting:**
- Zoom levels: L0 = "10 services, 3 active tickets", L1 = "lead-lifecycle: auth refactor, 4/7 AC", L2 = full CLAUDE.md
- MapReduce pattern: summarize in parallel, cluster, expand on demand
- Our progressive disclosure is currently binary (loaded/not loaded). This adds intermediate zoom levels that could reduce token waste while preserving awareness.

**Source:** https://factory.strongdm.ai/techniques/pyramid-summaries

---

## Investigate: The Filesystem as Memory (StrongDM Software Factory)

**What:** Validates our existing approach: directories + indexes + on-disk state = agent memory substrate. Introduces the concept of "genrefying" (library science term) — reorganizing information structures to optimize future retrieval.

**Why interesting:**
- We already do this: CLAUDE.md files as indexes, agent-os specs as structured knowledge, `mb-doc-housekeeping` as a genrefying agent that keeps the structure clean.
- Confirms we're on the right track. Worth reading for vocabulary and to see if they've found patterns we haven't.

**Source:** https://factory.strongdm.ai/techniques/filesystem

---

## Priority Order

1. MCP Memory Servers — lowest effort to test, native integration
2. Pyramid Summaries — multi-resolution context loading, complements existing progressive disclosure
3. Supabase pgvector — if MCP servers feel limited
4. Re-enable platform memory — dependent on Claude Code updates
5. Graph DB — only if relationship queries become a real bottleneck
6. Full RAG pipeline — only if `/tribal-knowledge` proves insufficient at scale
