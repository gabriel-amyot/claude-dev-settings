# Context Engineering Principles

Distilled from Anthropic's "Effective context engineering for AI agents" (2025-09-29) and applied to Claude Code workflows.

## Core Mental Model
Context is a finite resource with diminishing marginal returns. Every token competes for attention. The goal: **smallest set of high-signal tokens that maximizes desired outcome.**

## The Three Levers for Long-Horizon Tasks

### 1. Compaction
Distill conversation history into compressed summaries. Preserves decisions, unresolved issues, and implementation state. Discards redundant tool outputs.

**Failure mode:** Overly aggressive compaction loses subtle but critical context (architectural decisions, constraints, "why not X" reasoning). This causes agent drift.

**Mitigation:** Before compaction, persist critical state to disk. Tune compaction for recall first (capture everything important), then precision (trim the noise).

### 2. Structured Note-Taking (Agentic Memory)
Agent writes persistent notes outside the context window, reads them back after compaction or in new sessions.

**Pattern:** Maintain a working document (NOTES.md, TODO list, session state file) that tracks:
- Current goal and remaining tasks
- Decisions made and WHY (the "why" is what drifts first)
- Blockers and dependencies
- What was tried and failed (prevents loops)

**Key insight:** Without notes, agents after compaction re-derive context from code alone, losing intent and constraints that existed only in conversation.

### 3. Sub-Agent Delegation
Specialized subagents handle focused tasks with clean context windows. Each explores deeply (10k+ tokens) but returns only condensed results (1-2k tokens).

**When to use:**
- Deep research or exploration (codebase search, architecture analysis)
- Parallel independent tasks
- Any work that would pollute the orchestrator's context with raw data

**When NOT to use:**
- Simple directed searches (use grep/glob directly)
- Tasks requiring the orchestrator's full conversation context

## Progressive Disclosure
Don't front-load. Maintain lightweight references (file paths, index entries, query patterns) and load content on demand.

**Hierarchy:** Index → metadata → selective content read

## Just-In-Time Context
Prefer runtime retrieval over pre-computed context injection. Let the agent navigate to what it needs rather than dumping everything upfront.

**Hybrid model (what Claude Code does):** CLAUDE.md loaded upfront (small, high-signal). Everything else via tools (glob, grep, read) at the moment of need.

## Applying to Claude Code Sessions

### Before Starting Work
- Read only the relevant index/README, not all files
- Load context triggered by the task, not "just in case"

### During Work
- Write session state to disk at logical boundaries (per AC, per subtask)
- Use subagents for research; keep orchestrator context clean
- Scope sessions to 2-3 ACs max

### Before Compaction (Critical)
- Persist to disk: current plan, progress, decisions, constraints
- The file survives compaction; the conversation doesn't

### After Compaction
- Read back the persisted state file before continuing
- Verify alignment with original goals before proceeding
