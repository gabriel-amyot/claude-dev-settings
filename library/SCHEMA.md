# SCHEMA.md — Harness Wiki

This file defines the conventions for the cross-org harness knowledge base. The existing CATALOG.md serves as the floor plan and topic cross-reference. This SCHEMA.md adds the LLM Wiki metadata layer.

**Wiki ID:** `harness`
**Root:** `/Users/gabrielamyot/.claude-shared-config/library/`
**Registry:** `~/.claude-shared-config/library/WIKI_REGISTRY.yaml`
**Catalog:** `CATALOG.md` (floor plan, topic cross-reference, navigation)

---

## Page Types

| Type | Purpose | Naming | Example |
|------|---------|--------|---------|
| `decision` | Architecture decision for the harness | Semantic kebab-case | `memory-management-disable-auto-consolidate-context.md` |
| `pattern` | Reusable agent/context pattern | Semantic kebab-case | `pre-flight-heuristics-hierarchical-coordination.md` |
| `research` | Deep analysis of an approach or technology | Semantic kebab-case | `ai-agent-memory-architectures-patterns-survey.md` |
| `practice` | How-to guide, methodology, checklist | Semantic kebab-case | `test-driven-development-red-green-refactor.md` |
| `context` | On-demand context file loaded by CLAUDE.md triggers | Semantic kebab-case | `shipping-workflow.md` |
| `operations` | Infra topology, troubleshooting, known issues | Semantic kebab-case | `supervisr-cloud-run-topology.md` |

## Naming Convention

All files use self-documenting names: `{domain}-{purpose}-{key-concepts}.md`. The name alone should tell you what's inside without reading the file.

## Wikilinks

Use `[[page-name]]` for same-wiki links. Use `[[wiki-id::page-name]]` for cross-wiki links.

Examples:
- `[[context-engineering]]` — same wiki
- `[[klever::architecture-overview]]` — cross-wiki to Klever
- `[[supervisr::disposition-flow]]` — cross-wiki to Supervisr

Resolution order: ALIASES.md → CATALOG.md topic cross-reference → filename match.

## Relationship to CATALOG.md

CATALOG.md is the authoritative floor plan and remains the primary navigation tool. This SCHEMA.md adds:
- Page type definitions
- Wikilink conventions
- Alias resolution
- Maintenance workflows

CATALOG.md is NOT replaced or superseded.
