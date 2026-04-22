---
name: tribal-knowledge
description: Structured retrieval across all knowledge layers. Searches ADRs, contracts, agent-os specs, MEMORY.md files, and source code in priority order to answer architectural and contextual questions with provenance. Input: natural language question. Returns: answer with source provenance and durability rating (HIGH/MEDIUM/LOW).
---

# Tribal Knowledge Skill

Search all knowledge layers in priority order to answer architectural and contextual questions. Returns the answer with provenance and a durability rating.

**Usage:** `/tribal-knowledge <question>`

**Examples:**
```
/tribal-knowledge How does the webhook retry policy work?
/tribal-knowledge What queue technology do we use and why?
/tribal-knowledge How are feature flags evaluated at runtime?
```

## Arguments

`$ARGUMENTS` is the question to answer. Required.

## Execution Flow

### Step 1: Extract the Question

Parse `$ARGUMENTS` as the question. If empty, ask the user what they want to know.

### Step 2: Search Knowledge Layers in Priority Order

Search each layer in order. Collect ALL matches, but stop expanding search effort once a HIGH durability match is found.

| Priority | Layer | Search Path | Durability |
|----------|-------|-------------|------------|
| 1 | Global ADRs | `documentation/architecture/adr/` | Permanent (HIGH) |
| 2 | Global contracts | `documentation/architecture/contracts/` | Permanent (HIGH) |
| 3 | agent-os per-service specs | `app/micro-services/*/agent-os/` | Permanent (HIGH) |
| 4a | On-demand context files | `~/.claude/library/context/` | Stable (HIGH) |
| 4b | Project MEMORY.md | `~/.claude/projects/*/memory/` | Stable (HIGH) |
| 5 | Ticket-local ADRs | `tickets/{ID}/architecture/adr/` | Unpromoted (MEDIUM) |
| 6 | Ticket reports | `tickets/{ID}/reports/architecture/` | Transient (MEDIUM) |
| 7 | Integration test configs | `tickets/*/integration-tests/config/` | Executable truth (MEDIUM) |
| 8 | Source code | `app/micro-services/*/src/` | Ground truth (LOW) |
| 9 | SpecStory history | `.specstory/history/` | Last resort (LOW) |

Use the Explore agent (Task tool with `subagent_type=Explore`) or Grep/Glob tools to search each layer. Use keyword extraction from the question to form search queries.

For each layer:
1. Glob to confirm the path exists
2. Grep for relevant keywords within that path
3. Read matching files to confirm relevance

### Step 3: Report Results

Use the output format below based on what was found.

## Output Format

### When found (single match):

```markdown
## Tribal Knowledge: <question summary>
**Answer:** <concise answer>
**Found in:** Layer <N> — `<file path>`
**Durability:** <rating>
**Suggested action:** <action or "None — knowledge is at permanent tier.">
```

### Durability ratings:

- `HIGH` — `documentation/architecture/adr/`, `documentation/architecture/contracts/`, `app/micro-services/*/agent-os/`, `~/.claude/library/context/`, `~/.claude/projects/*/memory/`
- `MEDIUM` — `tickets/{ID}/architecture/adr/`, `tickets/{ID}/reports/architecture/`, `tickets/*/integration-tests/config/`
- `LOW` — `app/micro-services/*/src/`, `.specstory/history/`

### When found in multiple layers:

Report the highest-durability match as authoritative, then list others:

```markdown
## Tribal Knowledge: <question summary>
**Answer:** <concise answer>
**Found in:** Layer <N> — `<file path>`
**Durability:** <rating>
**Suggested action:** None — knowledge is at permanent tier.
**Also found in:** Layer <N> — `<path>` (<rating> — lower durability copy)
```

### When MEDIUM or LOW durability:

```markdown
**Suggested action:** Run `/push-adr` to promote to `documentation/architecture/` | Update `documentation/architecture/contracts/` | Add to MEMORY.md
```

### When not found:

```markdown
## Tribal Knowledge: <question summary>
**Answer:** Not found in any knowledge layer.
**Searched:** All 9 layers
**Suggested action:** This knowledge gap should be documented. Consider creating an ADR or MEMORY.md entry.
```

## Guidelines

- Be thorough but efficient. Once a HIGH durability match is found, do a quick scan of remaining layers but don't deep-dive.
- Always include the exact file path so the user can navigate to the source.
- For MEDIUM durability findings, actively recommend promotion — these are knowledge at risk of being lost.
- For LOW durability findings (source code only), recommend documenting the architectural intent, not just the implementation.
- If the question spans multiple topics, break it into sub-questions and search each independently.
