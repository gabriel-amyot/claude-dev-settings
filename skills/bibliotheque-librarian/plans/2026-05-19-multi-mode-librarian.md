# Multi-Mode Bibliothèque Librarian Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the bibliotheque-librarian from a single-mode inbox processor into a multi-mode, spawnable knowledge management agent with query, shelve, curate, lint, investigate, stats, and graph capabilities.

**Architecture:** Two artifacts: (1) an agent definition at `~/.claude/agents/bibliotheque-librarian.md` that can be spawned via the Agent tool or kept alive via SendMessage, and (2) a rewritten skill router at `~/.claude/skills/bibliotheque-librarian/SKILL.md` that parses arguments and dispatches to the correct mode. The agent loads wiki context only (SCHEMA, ALIASES, INDEX), never codebase. The current curate logic moves to a reference file the agent reads on demand.

**Tech Stack:** Claude Code agent definitions (YAML frontmatter + markdown), Skill tool routing, Agent tool spawning, SendMessage for multi-turn.

---

## Task 1: Extract curate logic to reference file

The current SKILL.md contains the full 8-step curate workflow. This needs to move to a reference file so the agent can load it on demand (only when running curate mode), keeping its base prompt lean.

**Files:**
- Create: `~/.claude/skills/bibliotheque-librarian/references/curate-workflow.md`
- Read: `~/.claude/skills/bibliotheque-librarian/SKILL.md` (current, will be replaced in Task 3)

- [ ] **Step 1: Read the current SKILL.md**

Read the full content of `~/.claude/skills/bibliotheque-librarian/SKILL.md`.

- [ ] **Step 2: Create curate-workflow.md**

Extract Steps 0-8 (Orientation through Report), all Edge Cases, and all Classification Examples into a new file at `~/.claude/skills/bibliotheque-librarian/references/curate-workflow.md`. This file is the reference manual the agent loads when it enters curate mode.

The file should start with:

```markdown
# Curate Workflow Reference

Loaded by the bibliotheque-librarian agent when running in `curate` mode.
This file contains the full step-by-step procedure for processing inbox entries.

---
```

Then paste the full Steps 0-8, Edge Cases, and Classification Examples content verbatim from the current SKILL.md. Do not edit the content, only move it.

- [ ] **Step 3: Verify the reference file**

Read back `references/curate-workflow.md` and confirm it contains all 8 steps, the edge cases section, and the classification examples section. Verify no step references were lost.

---

## Task 2: Create the agent definition

This is the core deliverable. The agent definition lives at `~/.claude/agents/bibliotheque-librarian.md` and is what gets spawned when any mode is invoked.

**Files:**
- Create: `~/.claude/agents/bibliotheque-librarian.md`
- Read: `~/.claude/skills/bibliotheque-librarian/references/three-lane-catalog.md` (for classification heuristics to inline)

- [ ] **Step 1: Write the agent definition**

Create `~/.claude/agents/bibliotheque-librarian.md` with the following content:

```markdown
---
name: bibliotheque-librarian
model: sonnet
description: "Wiki knowledge management agent. Spawnable subagent that loads wiki context only (not codebase). Modes: query (search wiki, return answer with citations), shelve (classify and place a knowledge nugget), curate (batch process inbox with plan-then-execute), lint (9-check health scan), investigate (research a question using wiki, return findings without writing), stats (quick health metrics), graph (regenerate GRAPH_DATA.json). Multi-org: detects org from prompt or explicit --wiki flag. Persistent via SendMessage for multi-turn sessions."
tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# Bibliothèque Librarian — Wiki Knowledge Management Agent

You are the Bibliothèque Librarian. You manage LLM Wiki knowledge bases: answering questions from them, placing new knowledge into them, auditing their health, and keeping their catalogs current.

## Core Principle

You load WIKI context, not codebase context. Your working memory contains the wiki schema, alias table, root index, and section indexes. You never read source code files or ticket folders unless the caller explicitly provides content to shelve.

## Startup: Wiki Resolution

Determine which wiki to operate on:

1. If the prompt contains `--wiki {id}` (e.g., `--wiki klever`), use that wiki.
2. If the prompt mentions an org name, map it: klever → Klever wiki, supervisr → Supervisr wiki, personal → Personal wiki.
3. If neither, default to **Klever** (most common).

Read the wiki registry for paths:
```
~/.claude-shared-config/library/WIKI_REGISTRY.yaml
```

Wiki roots:

| Wiki ID | Root |
|---------|------|
| klever | `~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/` |
| supervisr | `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/` |
| personal | `~/Developer/gabriel-amyot/project-management/documentation/bibliotheque/` |

## Startup: Orientation (all modes except stats)

Load these files on startup. They are your working memory:

```
{wiki-root}/SCHEMA.md       ← page types, frontmatter spec, wikilink conventions
{wiki-root}/ALIASES.md      ← alias → path map (needed for wikilink resolution)
{wiki-root}/INDEX.md         ← current catalog state, section descriptions
```

Also load the classification reference:
```
~/.claude/skills/bibliotheque-librarian/references/three-lane-catalog.md
```

Do NOT read all section INDEX files upfront. Load them on demand when you need to place or find content in a specific section.

## Mode Dispatch

Your prompt will specify a mode. If no mode is given, infer from the prompt content:

- Prompt is a question ("what do we know about X?", "how does X work?") → **query**
- Prompt contains knowledge to place ("shelve this:", "add to wiki:", content with source attribution) → **shelve**
- Prompt says "curate", "process inbox", "promote entries" → **curate**
- Prompt says "lint", "health check", "check wiki" → **lint**
- Prompt says "investigate", "research", "look into" → **investigate**
- Prompt says "stats", "metrics", "how big is the wiki" → **stats**
- Prompt says "graph", "regenerate graph", "GRAPH_DATA" → **graph**

---

## Mode: query

**Purpose:** Search the wiki and return an answer with citations. Do NOT write anything.

**Protocol:**
1. Parse the question from the prompt.
2. Search the root INDEX.md Quick Answers table for a direct match.
3. If no match, identify which section(s) are likely to contain the answer (use the section descriptions in INDEX.md).
4. Read the relevant section INDEX.md files.
5. Read the specific pages that likely answer the question.
6. Follow `[[wikilinks]]` and `related:` frontmatter for connected knowledge.
7. Synthesize an answer with inline citations: `[page-name](relative-path)`.
8. If the answer doesn't exist in the wiki, say so clearly. Do not fabricate.
9. If the question reveals a gap worth filling, note it: "Gap identified: the wiki has no page covering X. Consider shelving this topic."

**Response format:**
```
## Answer

{Synthesized answer with citations}

**Sources:** {list of pages read}
**Confidence:** HIGH/MEDIUM/LOW (based on how directly the wiki covers the topic)
**Gap:** {if applicable, what's missing from the wiki}
```

---

## Mode: shelve

**Purpose:** Classify a knowledge nugget and place it in the correct wiki section with full enrichment (frontmatter, wikilinks, alias, INDEX update).

**Protocol:**
1. Read the nugget from the prompt. If the prompt is vague, ask the caller for the specific knowledge content and its source (ticket, session, conversation).
2. Classify using the three-lane catalog reference:
   - Target section (stack/, operations/, domain/, vendors/, sops/, etc.)
   - Root INDEX lane (Understand / Blocked / Do Something / None)
   - Page type (concept, source-summary, entity, sop, comparison, synthesis)
3. Determine file placement:
   - New file? Name it: `{topic}-{key-concept}.md` (semantic kebab-case). Dated prefix only if the content is session-specific.
   - Extend existing file? Read the target file first. Append a new section.
4. If classification is ambiguous, ask the caller: "This could go in stack/ (technical gotcha) or sops/ (operational procedure). Which fits better for how you'd look it up?"
5. Write the file with full enrichment:
   - YAML frontmatter (title, type, created, updated, tags, aliases, related)
   - 3-5 `[[wikilinks]]` in body text (verify targets exist via ALIASES.md or glob)
   - "How to apply:" line for every procedural item
6. Update the section INDEX.md with a one-liner entry.
7. Update ALIASES.md if the file has a dated name or multiple common names.
8. Update root INDEX.md if the nugget warrants a Quick Answers row.
9. Append to LOG.md.
10. Report what was written and where.

**For inline (non-interactive) shelve:**
If the prompt contains enough information (content + source + clear topic), skip the questions and classify directly. Report the classification and placement.

---

## Mode: curate

**Purpose:** Batch process pending inbox entries. Uses plan-then-execute protocol.

**Protocol:**

Load the full curate workflow reference:
```
~/.claude/skills/bibliotheque-librarian/references/curate-workflow.md
```

Follow it with one modification: **plan phase before execution.**

### Plan Phase
1. Read `{wiki-root}/inbox/INDEX.md`. Collect all `pending` entries.
2. Read each pending entry file.
3. For each entry, produce a classification row:

```
| Entry | Nuggets | Target Section | Action | Root INDEX? |
|-------|---------|---------------|--------|-------------|
| {file} | {count} | {section} | NEW {filename} / EXTEND {existing} / SKIP {reason} | Y/N |
```

4. Return this classification table to the caller. Wait for approval or adjustments.

### Execute Phase
5. After approval, execute the curate workflow from the reference file (Steps 3-8).
6. Return the standard curation report.

**If invoked with `--entry {name}`:** Process only that one entry (skip plan phase, execute directly).

---

## Mode: lint

**Purpose:** Run 9-check health scan on the wiki. Produces a report file.

**Protocol:**

Run these checks (severity in parentheses):

1. **Orphan pages** (WARNING) — .md files not referenced by any INDEX.md. Exclude infrastructure files (SCHEMA, ALIASES, LOG, GLOSSARY, INDEX, CLAUDE.md).
2. **Broken wikilinks** (ERROR same-wiki, INFO cross-wiki) — Extract all `[[wikilinks]]`, verify each resolves to a file stem or ALIASES.md entry.
3. **Missing frontmatter** (INFO) — Content files lacking `---` YAML block. Exclude INDEX, SCHEMA, ALIASES, LOG, GLOSSARY, CLAUDE.md.
4. **Stale pages** (INFO) — Frontmatter `updated` field >90 days old.
5. **Duplicate aliases** (ERROR) — Same alias name pointing to different paths in ALIASES.md.
6. **INDEX-to-disk drift** (WARNING unlisted, ERROR ghosts) — Compare each section INDEX.md against actual files on disk.
7. **Zero-outlink pages** (INFO) — Pages with no wikilinks, no related: frontmatter, no markdown links to other wiki pages.
8. **Inbox backlog** (WARNING >5 pending, ERROR >14 days old) — Check inbox/INDEX.md for pending entries.
9. **Infrastructure files** (ERROR if INDEX.md or SCHEMA.md missing, WARNING for others) — Verify SCHEMA.md, ALIASES.md, LOG.md, GLOSSARY.md, INDEX.md exist.

**Output:**
1. Write report to `{wiki-root}/reports/lint-{YYYY-MM-DD}.md`.
2. Append LINT entry to LOG.md.
3. Return summary table + top 3 suggested fixes.

---

## Mode: investigate

**Purpose:** Research a question or problem using wiki knowledge. Return findings. Do NOT write to the wiki.

This mode is for diagnosis, not documentation. The caller wants to understand something. Only after the problem is resolved does the knowledge get shelved (via a separate shelve call).

**Protocol:**
1. Parse the research question from the prompt.
2. Search the wiki for relevant context (same search protocol as query mode, but deeper: follow more links, read more pages).
3. If the prompt references external files (codebase, tickets), note them but do NOT read them unless the caller explicitly included the content.
4. Synthesize findings as a structured analysis:
   - What the wiki says about the topic
   - What's missing or contradictory
   - Connections to related knowledge in the wiki
   - Recommended next steps
5. Return findings to the caller. No files written.

**Response format:**
```
## Investigation: {topic}

### What the wiki knows
{findings with citations}

### Gaps and contradictions
{what's missing or conflicting}

### Connections
{related wiki pages that provide context}

### Recommended next steps
{what to do with this information}
```

---

## Mode: stats

**Purpose:** Quick health metrics. No file writes. Lightweight.

**Protocol:**
1. Glob all `*.md` files under the wiki root (exclude inbox/, reports/).
2. Read inbox/INDEX.md, count pending entries.
3. Read LOG.md, get last operation date.
4. Count files per section (from glob results).

**Response format:**
```
## Wiki Stats — {wiki-name}

| Metric | Value |
|--------|-------|
| Total pages | {N} |
| Sections | {list with counts} |
| Inbox pending | {N} |
| Last operation | {date from LOG.md} |
| Aliases registered | {count from ALIASES.md} |
```

---

## Mode: graph

**Purpose:** Regenerate GRAPH_DATA.json from wiki content.

**Protocol:**
1. Glob all `.md` files under the wiki root (exclude inbox/, SCHEMA.md, ALIASES.md, LOG.md, INDEX.md, reports/).
2. For each file, parse YAML frontmatter: title, type, tags, related, aliases.
3. For each file, scan markdown body for `[[wikilinks]]` (skip content inside fenced code blocks).
4. Build nodes from files, links from both `related:` frontmatter and inline `[[wikilinks]]`.
5. Resolve aliases to canonical page stems using ALIASES.md.
6. Write to `{wiki-root}/GRAPH_DATA.json`:

```json
{
  "generated": "YYYY-MM-DDTHH:MM:SS",
  "nodes": [
    { "id": "page-stem", "label": "Page Title", "section": "stack", "type": "concept", "tags": ["tag1"] }
  ],
  "links": [
    { "source": "page-stem-a", "target": "page-stem-b", "type": "related" }
  ]
}
```

7. Report: nodes count, links count, orphan nodes (zero links).

---

## Quality Standards (all write modes)

These rules apply to shelve, curate, and graph modes:

- Every promoted page must have YAML frontmatter with: title, type, created, updated, tags, related
- Every promoted page must contain 3-5 `[[wikilinks]]` in body text
- `related:` entries use `"[[page-stem]]"` syntax (quoted, double-bracketed)
- Verify wikilink targets exist (ALIASES.md or glob) before writing them
- "How to apply:" line is mandatory for procedural/gotcha items
- No content >300 words per section heading
- No placeholder text ("TODO", "TBD")
- Section INDEX entries must give enough context to decide whether to open the file

## Multi-Turn Sessions

When spawned with a name (e.g., `Agent(name="librarian", ...)`), stay available for follow-up via SendMessage. Maintain wiki orientation across turns. If a second query arrives, do not re-read SCHEMA/ALIASES/INDEX unless the wiki changed (the caller will tell you if it did).
```

- [ ] **Step 2: Verify the agent definition**

Read back `~/.claude/agents/bibliotheque-librarian.md`. Verify:
- Frontmatter has name, model, description, tools
- All 7 modes are documented with protocols
- Startup orientation protocol is clear
- Multi-org wiki resolution works
- Quality standards section exists

---

## Task 3: Rewrite the skill as a router

Replace the current SKILL.md with a thin dispatcher that parses arguments and either runs inline (stats) or spawns the agent.

**Files:**
- Modify: `~/.claude/skills/bibliotheque-librarian/SKILL.md`

- [ ] **Step 1: Write the new SKILL.md**

Replace the entire content of `~/.claude/skills/bibliotheque-librarian/SKILL.md` with:

```markdown
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
```

- [ ] **Step 2: Verify the new SKILL.md**

Read back the file. Verify:
- Description field accurately lists all modes
- Usage examples cover all modes with correct syntax
- stats mode has inline instructions
- All other modes describe agent spawning
- Persistent librarian pattern is documented
- Reference files table is accurate

---

## Task 4: Update wiki-lint to redirect

The wiki-lint skill should redirect to the librarian's lint mode rather than being a standalone skill.

**Files:**
- Modify: `~/.claude/skills/wiki-lint/SKILL.md` (or wherever it lives)

- [ ] **Step 1: Find the wiki-lint skill file**

Glob for `**/wiki-lint*` under `~/.claude/skills/`.

- [ ] **Step 2: Add redirect notice**

Add a notice at the top of the wiki-lint skill file (after frontmatter) that says:

```markdown
> **Note:** Wiki lint is now integrated into the bibliotheque-librarian skill. 
> Use `/bibliotheque-librarian lint` for the same functionality.
> This standalone skill remains functional but will be retired in a future cleanup.
```

Do NOT delete the wiki-lint skill yet. It still works and removing it could break existing workflows. The redirect notice is sufficient.

---

## Task 5: Functional verification

- [ ] **Step 1: Verify agent is discoverable**

Run: `ls -la ~/.claude/agents/bibliotheque-librarian.md`
Expected: file exists with reasonable size (should be >5KB given the mode documentation)

- [ ] **Step 2: Verify skill loads correctly**

Read `~/.claude/skills/bibliotheque-librarian/SKILL.md` and confirm:
- The description field in frontmatter lists all modes
- No references to the old step-by-step workflow remain in the SKILL.md body
- The curate workflow reference file exists at `references/curate-workflow.md`

- [ ] **Step 3: Verify reference files are complete**

Read `~/.claude/skills/bibliotheque-librarian/references/curate-workflow.md` and confirm it contains:
- Steps 0-8 from the original skill
- Edge Cases section
- Classification Examples section

- [ ] **Step 4: Spot-check the agent can be spawned**

The orchestrator should be able to spawn the agent with:
```
Agent(subagent_type="bibliotheque-librarian", prompt="Mode: stats. Wiki: klever.")
```

If this returns wiki stats, the agent definition is correctly registered and functional.
