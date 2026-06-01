---
name: bibliotheque-librarian
description: "Wiki knowledge management hub. Modes: curate (batch inbox), shelve (place a nugget), query (search wiki), lint (health check), investigate (research without writing), stats (quick metrics), graph (regenerate link data). Invoke with /bibliotheque-librarian [mode] [args]. Spawns a dedicated wiki agent for all modes except stats. Multi-org: auto-detects from cwd, or pass --wiki {klever|supervisr|personal}."
---

# Bibliothèque Librarian

Wiki knowledge management skill. Routes to the `bibliotheque-librarian` agent for heavy work, runs inline for lightweight operations.

## Usage

```
/bibliotheque-librarian                     → curate (default: batch process inbox)
/bibliotheque-librarian curate              → same as above
/bibliotheque-librarian curate --entry X    → process single inbox entry
/bibliotheque-librarian shelve              → interactive: ask what to shelve, classify, place
/bibliotheque-librarian shelve "nugget..."  → inline: classify and place the quoted nugget
/bibliotheque-librarian query "question"    → search wiki, return answer with citations
/bibliotheque-librarian lint                → 9-check health scan (absorbs /wiki-lint)
/bibliotheque-librarian investigate "topic" → research using wiki, return findings (no writes)
/bibliotheque-librarian stats               → quick metrics (inline, no agent spawn)
/bibliotheque-librarian graph               → regenerate GRAPH_DATA.json
```

All modes except `stats` spawn the `bibliotheque-librarian` agent via the Agent tool.

## Org Detection

Detect wiki from current working directory:
- cwd contains `grp-beklever-com` → `--wiki klever`
- cwd contains `supervisr-ai` → `--wiki supervisr`
- cwd contains `gabriel-amyot` → `--wiki personal`

Explicit `--wiki` flag overrides auto-detection.

## Mode: stats (inline)

This mode runs in the current context without spawning an agent. It is cheap and fast.

1. Determine wiki root from org detection.
2. Glob `**/*.md` under wiki root (exclude inbox/, reports/).
3. Count files. Count per top-level section.
4. Read `inbox/INDEX.md` — count pending entries.
5. Read `LOG.md` — get last operation date.
6. Read `ALIASES.md` — count alias rows.
7. Output summary table inline.

## All Other Modes: Spawn Agent

For curate, shelve, query, lint, investigate, graph:

1. Detect org and resolve wiki root.
2. Build the agent prompt:
   - Include the mode name
   - Include any arguments (entry name, query text, nugget content)
   - Include `--wiki {id}` for org scoping
3. Spawn via Agent tool:

```
Agent(
  subagent_type="bibliotheque-librarian",
  description="{mode}: {short description}",
  prompt="Mode: {mode}. Wiki: {id}. {mode-specific content}"
)
```

4. Report the agent's response to the user.

## Persistent Librarian (multi-turn)

To keep a librarian agent alive for multiple queries:

```
Agent(
  name="librarian",
  subagent_type="bibliotheque-librarian",
  prompt="Mode: standby. Wiki: klever. Stand by for queries."
)
```

Then use `SendMessage(to="librarian", content="query: how does the data pipeline work?")` for follow-ups.

## Reference Files

These files support the agent and should not be modified without understanding their role:

| File | Purpose |
|------|---------|
| `references/three-lane-catalog.md` | Classification rulebook: Understand/Blocked/Do Something lanes |
| `references/curate-workflow.md` | Full 8-step inbox processing procedure (loaded by agent in curate mode) |
