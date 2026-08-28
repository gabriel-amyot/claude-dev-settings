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

## The Tier Model: Every Line Is One of Five Things

**Source:** session `lucid-ibis`, restructuring both Klever CLAUDE.md files onto the
Bibliothèque medallion tiers, cutting the always-on layer 74,129 → 52,250 B (2026-08-27).

CLAUDE.md is the always-on rule layer. Every candidate line is one of five kinds, and only
one belongs there:

| Kind | Belongs in | Test |
|---|---|---|
| Rule | CLAUDE.md | Changes behaviour in *every* session, and cannot be a hook or a lookup |
| Fact | GOLD (bibliothèque) | A statement about how the world is. Can go stale. Can be challenged. |
| Locator | SILVER (`ALIASES.md`, `INDEX.md`) | Tells you where to find a fact |
| Origin | BRONZE (`_archive/`) | The ticket or incident a rule came from |
| Check | HOOK | Deterministic and mechanically verifiable |

A raw incident origin in CLAUDE.md is a tier violation: bronze content sitting in the layer
that loads every session. `claude-md-tier-lint.sh` (warn-only, ratchet budget; see
`mechanical-backstops.md`) flags inline "Learned from" narratives and ticket keys cited as
provenance with no library pointer.

**How to apply:** classify a candidate CLAUDE.md line before adding it. If it is a fact, a
locator, an origin, or a deterministic check, it does not belong there.

### Migrating an existing rule to gold: search first

Migrating 17 inline incident narratives out of Klever's CLAUDE.md into gold pages produced
13 EXISTING, 2 EXTEND, 0 NEW. The lessons were already documented; CLAUDE.md was duplicating
gold pages rather than holding unique knowledge. That result is the strongest evidence the
tier model is right.

**How to apply:** before authoring a new gold page for a CLAUDE.md lesson, search the
library first. A migration pass that produces mostly NEW pages means the search was not
thorough enough.

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

**2026-08-27 update — prefer push retrieval over the table itself.** Two hand-maintained
On-Demand Context tables (45 rows, 5.7 KB total) were deleted from both Klever CLAUDE.md
files and replaced by rows in the org's `ALIASES.md`, matched against the user's prompt by
`bibliotheque-recall.sh` and injected automatically. A table requires the agent to notice a
row and choose to read it, and fails exactly when it matters, because an agent only consults
a pointer if it already suspects it needs one; the hook is belief-independent. Coverage went
4/40 → 40/40 global context files, measured at 92% HIT@1 / 96% HIT@5 on a 26-case eval
(`recall-eval.py`). See `bibliotheque-ambient-consultation-hooks.md` in the Klever
bibliothèque for the hook mechanics.

**How to apply:** an index table inside an always-loaded file is a smell. Move it to the
retrieval layer (ALIASES.md + the recall hook) and keep only a short fallback pointer.

## Mandatory Library Infrastructure
`~/.claude/library/CATALOG.md` MUST exist. It is the master index for all library files.

After creating any file in `~/.claude/library/`, update CATALOG.md immediately.
