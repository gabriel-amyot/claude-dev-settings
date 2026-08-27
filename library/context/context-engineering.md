# Context Engineering — Long-Running Agent Sessions

On-demand context: load when running autonomous sessions, hitting compaction, or managing agent drift.

## Core Principles

1. **Progressive disclosure.** Index → metadata → selective read. Never bulk-load.
2. **Recursive INDEX.md.** Every document folder needs one. Read the index, pick selectively.
3. **Metadata before content.** Explore filenames, folder structure, indexes before reading full files.
4. **Distill, don't accumulate.** Write summaries to disk between phases. Index them. Never carry raw material across sessions.
5. **All context is on-demand** except CLAUDE.md files (auto-loaded).
6. **Delegate deep work to subagents.** Research, exploration, large reads go to subagents returning condensed summaries (1-2k tokens). Keep orchestrator context clean.

## Compaction Protocol

When approaching context limits or at logical boundaries:

1. **Write SESSION_STATE.md** to the working or ticket directory. Include:
   - Current goal
   - Progress (what's done, what's next)
   - Decisions with rationale
   - Constraints and blockers
   - Modified files list
2. **Read it back after compaction** before continuing work.
3. **Update ac.yaml** (if ticket work) so the next agent knows exactly where to resume.

## Long-Running Sessions (>30 min)

- Create WIP commits at logical boundaries (per AC or logical unit). Uncommitted code dies with the context window.
- Scope sessions to 2-3 ACs max. Break larger work into sequential sessions.
- Separate research from coding: Session A produces docs/plans (committed). Session B reads the plan and writes code. Session C reviews.

## Subagent Architecture

- **Sonnet** for research, exploration, retries (cheap, parallel)
- **Opus** for judgment, synthesis, orchestration
- **Haiku** for mechanical tasks (file moves, format conversions)
- Subagents return condensed summaries, not raw material
- Never carry raw source material across sessions. Distill to disk.

## Data Stays on Disk

Never load large datasets (CSV, JSON, logs, API dumps, >50 lines) into context. Generate a self-contained script that reads the data and writes results to an output file. Scripts are reusable and cost zero tokens to execute.

## Anti-Patterns

- Bulk-loading entire directories into context
- Carrying raw investigation results across compaction boundaries
- Running research AND implementation in the same session
- Letting orchestrator do work that subagents should handle
- Forgetting to update ac.yaml or SESSION_STATE.md before compaction

## Memory System

- MEMORY.md is an index, not a document. Each entry is one line under ~150 chars.
- Satellite files hold the actual content with frontmatter (name, description, type).
- Types: user, feedback, project, reference.
- Archive stale memories. Delete duplicates of CLAUDE.md rules.
- Never add inline prose to MEMORY.md. If content needs more than one line, create a satellite file and add a pointer.
- Promote to CLAUDE.md when a pattern is confirmed 3+ times or is older than 2 weeks and still actively relevant.

## Bibliothèque Pattern (Cross-Org Reusable)

Proven structure for agent-ready knowledge libraries:

1. `INDEX.md` — card catalog with "Question → file" quick-answer table
2. `GLOSSARY.md` — domain terms with org-specific context
3. Taxonomy folders: `domain/`, `stack/`, `operations/`, `people/` (adapt to org)
4. Section `INDEX.md` files that LINK to existing docs (never duplicate)

The Bibliothèque references authoritative sources, it doesn't replace them. If `documentation/architecture/` already has the answer, the Bibliothèque INDEX.md points there.
