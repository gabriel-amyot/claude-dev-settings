# CLAUDE.md Authoring Guide

On-demand context: load when editing any CLAUDE.md file.

## Purpose
CLAUDE.md files are auto-loaded every session. Every line costs tokens on every interaction. Treat them as premium real estate.

## DRY Principle
- Inline only decision tables and rules consulted mid-task
- Extract multi-step procedures to satellite files (`documentation/process/` or `~/.claude/library/context/`)
- Replace extracted content with a 2-3 line pointer
- Never duplicate rules across CLAUDE.md layers (global, org, project, subdirectory)

## Hierarchy
1. `~/.claude/CLAUDE.md` — universal rules, all orgs
2. `{org}/.claude/CLAUDE.md` — org-specific (Work Assistant, org conventions)
3. `{project}/CLAUDE.md` — project rules, file placement, workflow
4. `{project}/.claude/CLAUDE.md` — subdirectory-specific nuances only

Each layer adds context-specific nuances. Never repeat what a parent layer already says.

## Self-Correcting Memory
When Claude receives a correction during a session:
- **Minor** (naming, file placement, process step): Update relevant CLAUDE.md with a concise rule.
- **Moderate** (repeated pattern, workflow gap): Propose codifying as a skill or process doc.
- **Major** (architecture anti-pattern, security): Propose dedicated process doc in `documentation/process/`.

Always tell the user what you're updating and why. Keep updates concise: one rule per lesson. Reference the trigger context (e.g., "Learned from KTP-115 session: ..."). Check for existing similar rules before adding.

## What Belongs Inline vs. Extracted

| Inline (auto-loaded) | Extracted (on-demand) |
|---|---|
| Decision tables (YES/NO criteria) | Multi-step procedures (SOPs) |
| Short rules (<3 lines) | Checklists (>5 steps) |
| File placement mappings | ASCII directory trees |
| Trigger → file pointers | Full workflow descriptions |
| Security gates | Incident lessons (>2 lines) |

## Memory Governance
- Promote to CLAUDE.md when a pattern is confirmed 3+ times or older than 2 weeks and still relevant
- Monthly review MEMORY.md for stale entries
- Target ~20 memory entries max
- No duplicates between MEMORY.md and CLAUDE.md

## On-Demand Context Table Hygiene
After adding an entry to any On-Demand Context table, create the referenced file immediately. Even a 5-line stub is better than a dead link.

**Rule:** Never commit a CLAUDE.md with an On-Demand Context entry pointing to a file that doesn't exist.

## Mandatory Library Infrastructure
`~/.claude/library/CATALOG.md` MUST exist. It is the master index for all library files.

After creating any file in `~/.claude/library/`, update CATALOG.md immediately.
