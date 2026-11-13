---
name: research-intake
description: Route and persist harness-level research (AI tooling, agentic workflows, development process tools, context engineering systems). Use when new research lands — a repo, article, gist, paper, or blog post about tools that could affect the development harness. Determines what it is, where to persist the raw source, where to put analysis, and what (if anything) gets distilled into the operational shared library. Input: URL, repo link, article, or description. Returns: files written + routing decision.
allowed-tools: Read, Write, Edit, Glob, Bash
nav:
  bay: ops
  when: "Route and persist harness-level research: repos, articles, papers about dev tools."
  when_not: "Domain knowledge (use /bibliotheque-librarian). Tribal knowledge extraction (use /gab-operationalize)."
---

# Research Intake Skill

Route incoming harness research to the right place. Raw sources and synthesis are separate. Operational distillates go to the shared library.

## When to use this Skill

Use when:
- A repo, gist, article, or paper lands that's about: agentic workflows, AI tooling, context engineering, LLM memory systems, autonomous coding agents, spec-driven dev, SDLC process tools
- User says "archive this", "save this research", "add this to the research", "file this"
- A session produces synthesis worth keeping (tool comparison, architectural decision, adoption verdict)
- Something from research gets operationalized and needs to move to the shared library

Do NOT use for:
- Non-harness research (business strategy, product research, domain research) — those go to org-specific bibliothèques
- Code snippets, implementations, or scripts — those go into the relevant project
- Meeting notes, standups, or ops notes — those go to the org inbox

---

## The Two Locations

### 1. Personal Research (Lab Notebook)

```
~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/research/
├── raw/        ← Third-party source material. Immutable. No opinions.
└── analysis/   ← Our thinking: comparisons, synthesis, adoption verdicts, session outputs
```

**Rule:** Raw = stuff created by others. Analysis = our work on that stuff.

### 2. Shared Operational Library (Production Intelligence)

```
~/.claude-shared-config/library/
├── research/          ← Distilled conclusions only. Not sources, not raw analysis.
│   ├── agent-systems/ ← Distilled knowledge about agent frameworks and orchestration
│   ├── memory-systems/ ← Distilled knowledge about context and memory patterns
│   └── security/      ← Security-relevant findings
├── context/           ← Actionable guides for agents to use in real-time decisions
├── practices/         ← Validated process patterns ready for adoption
└── architecture/      ← Architecture decisions and patterns in use
```

**Rule:** Only distilled, opinionated, actionable conclusions go here. Not source material. Not exploration. The test: "Does an agent need this RIGHT NOW to make a decision?" If no, it belongs in the dark factory.

---

## Decision Tree

```
New research arrives
│
├── Is it a third-party source (README, article, gist, blog post)?
│   └── YES → Archive to raw/
│              Format: raw/{descriptive-name}.md
│              Include frontmatter: source URL, author, archived date, brief note
│
├── Is it our analysis or synthesis?
│   ├── In-progress session output → analysis/{date}-{topic}.md
│   ├── Adoption verdict → analysis/{date}-{topic}-verdict.md
│   └── Exploration session output → analysis/{date}-{topic}-session.md
│
└── Is something being operationalized (adopted, extracted, integrated)?
    └── YES → Distill to shared library
               Determine target: context/ practices/ or research/{subdomain}/
               Write ONLY the actionable conclusion (not the journey)
               Update CATALOG.md and the relevant INDEX.md
```

---

## Step-by-Step: Archiving a Raw Source

**Step 1 — Fetch the content**

Use a Haiku agent to fetch (saves tokens):
```
Agent(model: haiku, prompt: "Fetch raw content from {URL}. Return full content, no commentary.")
```

Or use WebFetch directly for small pages.

**Step 2 — Write to raw/**

Filename: `raw/{tool-or-topic-slug}.md`

Frontmatter required:
```markdown
---
source: {URL}
author: {name or org}
archived: {YYYY-MM-DD}
note: {one-line context — why this landed, relation to existing stack}
---
```

Then the content (cleaned, not summarized — raw means raw).

**Step 3 — Update the INDEX**

Add a row to `research/INDEX.md` under "Raw Sources":
```markdown
| `raw/{filename}` | {source description} | {type: README/Article/Gist/Paper} | {date} |
```

---

## Step-by-Step: Writing Analysis

**When to write analysis:**
- After reading a raw source and forming a view
- After an exploration/comparison session
- When producing an adoption verdict

**Filename:** `analysis/{YYYY-MM-DD}-{topic-slug}.md`

**Required frontmatter:**
```markdown
---
date: {YYYY-MM-DD}
tools: {tools covered, comma-separated}
status: intake | exploring | verdict-adopt | verdict-park | verdict-cross-pollinate
---
```

**Required sections:**
- What it is (one paragraph, no fluff)
- Relation to existing stack (specific — what does it overlap with, complement, or replace?)
- Cross-pollination opportunity (what specific concept is worth extracting without full adoption?)
- Verdict: adopt / cross-pollinate / park + one-sentence rationale

**Update the INDEX** under "Analysis" after writing.

---

## Step-by-Step: Operationalizing to the Shared Library

When a verdict is "adopt" or "cross-pollinate," something needs to move from research into the operational library.

**What moves:** The conclusion and how to apply it. NOT the journey, NOT the raw source.

**Where it goes:**

| If the knowledge is about... | Goes to... |
|------------------------------|------------|
| How to structure agents or orchestration | `library/research/agent-systems/` |
| Memory, context persistence, wiki patterns | `library/research/memory-systems/` |
| Process patterns ready for use | `library/practices/` |
| Architectural patterns, ADR-level decisions | `library/architecture/` |
| Agent decision guides (what to do when X) | `library/context/` |

**Filename pattern:** `{domain}-{purpose}-{key-concepts}.md` (Librarian Protocol from CLAUDE.md)

**After writing:**
1. Update the section's `INDEX.md`
2. Add to `library/CATALOG.md` Topic Cross-Reference if cross-cutting
3. Note in the analysis file that the operationalization happened: add `operationalized: {date} → {library path}` to frontmatter

---

## Examples

### Example 1: New repo lands

```
User: "Found this — https://github.com/someuser/cool-agent-tool — archive it"

You:
1. Spawn Haiku agent to fetch README
2. Write raw/cool-agent-tool-readme.md with frontmatter
3. Update research/INDEX.md
4. Report: "Archived to raw/. No analysis yet — want me to run an intake analysis?"
```

### Example 2: Post-exploration, writing verdict

```
User: "We tested G-Stack. It works well for sprint execution, not for multi-repo."

You:
1. Write analysis/2026-05-01-gstack-verdict.md
   status: verdict-cross-pollinate
   Cross-pollination: extract /parallel and /mirror patterns as new superpowers skills
2. Update INDEX
3. Report: "Analysis written. Should I operationalize the /parallel pattern to the shared library?"
```

### Example 3: Operationalizing a pattern

```
User: "Let's add the Karpathy Wiki Ingest pattern to the shared library"

You:
1. Read analysis/2026-04-25-new-tools-intake.md for the verdict
2. Distill: write library/practices/llm-wiki-ingest-pattern.md
   — only the how-to-apply, not the exploration journey
3. Update library/practices/INDEX.md
4. Update analysis file frontmatter: operationalized: 2026-05-01 → library/practices/llm-wiki-ingest-pattern.md
5. Report location and what was written
```

---

## Harness Research Scope

This skill applies to research about:
- Agentic coding tools (e.g., G-Stack, AutoResearch, AutoGen)
- Context engineering and memory systems (e.g., Karpathy Wiki, OB1, RAG patterns)
- SDLC process frameworks (e.g., BMAD, Spec Kit, SDD workflows)
- AI-native development practices (e.g., Stripe Minions, Dark Factory patterns)
- Claude Code harness improvements (skills, hooks, agents, subagent patterns)
- Autonomous agent architectures and orchestration patterns

When in doubt: if it could change how the harness works, it's harness research.

---

## Related Skills

- `archive` — for archiving completed project tickets (not research)
- `bibliotheque-librarian` — for org-specific domain knowledge (not harness-level)
- `index-context` — for updating context indexes after writing
