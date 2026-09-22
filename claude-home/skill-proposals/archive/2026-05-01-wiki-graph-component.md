# Skill Proposal: wiki-graph-component
Date: 2026-05-01
Source: Mission Control Library graph spike

## Trigger
When user asks to add a knowledge graph, wikilink visualization, or Obsidian-style graph to any project with markdown files that use `[[wikilinks]]`.

## Scope
global (reusable across any React + FastAPI project)

## Draft Steps
1. Add backend endpoint that scans `.md` files, parses `[[wikilinks]]` (skipping code blocks), resolves aliases, returns `{nodes, links}` JSON
2. Install `react-force-graph-2d`, create generic `WikiGraph` component with fixed dimensions (no ResizeObserver)
3. Integrate into target view with collapsible panel + expand mode
4. Wire click-to-navigate from graph nodes to file viewer

## Key Gotchas
- Never use ResizeObserver to feed dimensions back into ForceGraph2D (infinite loop crash)
- Strip fenced code blocks before regex extraction
- Use `rglob` for files but `buildSubTree()` with relative paths for nested folder display
