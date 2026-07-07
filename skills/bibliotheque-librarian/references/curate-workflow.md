# Curate Workflow Reference

Loaded by the bibliotheque-librarian agent when running in `curate` mode.
This file contains the full step-by-step procedure for processing inbox entries.

---

## Step 0: Orientation

Read the wiki schema and root INDEX before touching anything:

```
documentation/bibliotheque/SCHEMA.md    ← page types, frontmatter spec, wikilink conventions
documentation/bibliotheque/ALIASES.md   ← existing alias map (needed for wikilink resolution)
documentation/bibliotheque/INDEX.md     ← current catalog state
```

Note the current state of the lanes and the Sections block. Knowing the current state prevents duplicate entries and collision.

Load the classification reference:

```
~/.claude/skills/bibliotheque-librarian/references/three-lane-catalog.md
```

This is your classification rulebook. Refer to it for every entry you process.

---

## Step 1: Read the Inbox Index

Read `documentation/bibliotheque/inbox/INDEX.md`.

Collect all entries where `Status` is `pending`. Build a working list:

```
pending_entries = [
  { file: "2026-04-21-overnight-crawl-spv165-learnings.md", date: "2026-04-21", source: "..." },
  ...
]
```

If the inbox INDEX has no pending entries, report "Inbox is empty. Nothing to promote." and stop.

---

## Step 2: Read and Classify Each Entry

For each pending entry, read the file. For every nugget inside the entry:

### 2a. Assign a Target Section

Each nugget belongs in one of these section folders. Consult the curator notes in the entry if present — they often pre-answer this.

| Section | What belongs there |
|---------|-------------------|
| `stack/` | Service architecture, data flows, gateway/auth behavior, Datastore schemas, BigQuery, service-to-service quirks |
| `operations/` | Deployment procedures, CI/CD gotchas, recovery playbooks, incident patterns, RCAs |
| `domain/` | Insurance lead lifecycle, compliance rules, partner onboarding, business context |
| `people/` | Team roster, partner contacts, ownership, org dynamics |
| `documentation/process/` | Meta-patterns about how we build, document, or operate (not inside bibliotheque, but a valid destination for structural knowledge) |

**Classification heuristics:**
- "This service does X when Y" → `stack/`
- "Pipeline fails with error Z" → `operations/`
- "This is why we designed X this way" → `domain/` (business reason) or `stack/` (technical reason)
- "Run these steps to recover X" → `operations/`
- "This term means X in our domain" → `domain/` or root `GLOSSARY.md`
- "Pattern for how agents should behave" → `documentation/process/`

When a nugget spans multiple sections, use the primary-mode rule from the three-lane reference: identify what mode the reader is in when they need this knowledge (crisis → operations, learning → stack or domain, executing → operations).

**Fit test — do not force-fit.** The section table above is a default map, not a straitjacket. Before assigning, ask: does this nugget's primary subject genuinely belong to an existing section's charter, or am I shoehorning it because no row matched? A nugget that only fits "by elimination" is a signal. When nothing fits cleanly, do NOT bury it in the least-bad section — instead route it to the closest match for now AND record a **new-section candidate** (see Step 3, option D) so the gap is visible rather than hidden. Glob the wiki's actual top-level folders first (`ls` the wiki root); the real section set may differ from the table above (e.g. Klever uses `stack/`, `sops/`, `vendors/`, `agent-hub/`), and a section may have been added since this doc was written.

### 2b. Determine Root INDEX Lane

Also classify whether this nugget deserves a row in the root INDEX:

- **Understand lane:** Glossary term, service description, data flow explanation, team ownership.
- **Blocked lane:** Observable failure (HTTP error, pipeline failure, empty data) with a specific symptom.
- **Do Something lane:** Repeatable task, deployment step, handoff procedure.
- **No root row:** Supporting detail, minor gotcha covered by a broader entry already in the root, or tooling patch already applied.

Reserve root rows for high-traffic knowledge. Not every file needs one.

---

## Step 3: Determine File Placement

For each nugget, decide whether it:

**A) Creates a new file.** Use this when the nugget is a self-contained piece of knowledge with a clear title. Name the file using the bibliotheque convention: `{topic}-{key-concept}.md` in kebab-case. Examples: `dac-default-branch-model.md`, `webclient-bodyvalue-double-serialization.md`.

**B) Extends an existing file.** Use this when the section already has a file covering the same topic and the nugget adds a new gotcha or variant. Read the existing file first. Append a new section; do not rewrite content that is already accurate.

**C) Belongs in a different document.** For meta-patterns about the Bibliothèque itself (like the three-lane design), the target may be `documentation/process/documentation-standards.md`, `bibliotheque/PROPOSALS.md`, or a CLAUDE.md update rather than a section file.

**D) Warrants a new section.** Use this when the nugget (and ideally one or more others in the backlog) belongs to a durable theme that no existing section covers, and force-fitting it would dilute an existing section's charter.

- **Create the section** (a new top-level folder + bootstrap `INDEX.md`) only when the evidence is strong: either **2+ nuggets in the current backlog share the theme**, or the theme is an obviously distinct, durable domain (a new vendor, a new product surface, a new subsystem). Name it with the same kebab-case convention. Bootstrap its `INDEX.md`, add it to the root `INDEX.md` section list, and flag the creation explicitly in the Step 8 report under **Structural changes**.
- **Propose, do not create**, for borderline cases (a single speculative nugget, an unclear boundary, or a split of an existing section). Add the proposal to `bibliotheque/PROPOSALS.md` with: proposed name, charter (one line), the nuggets that motivated it, and which existing section(s) it would draw from. Park the nugget in the closest existing section meanwhile, and note the proposal in the Step 8 report. Never silently restructure existing content.

**Reorg observations.** While placing nuggets you will see the wiki's current shape. If you notice structural drift — a section mixing unrelated concerns, the same topic split across two sections, a file that clearly belongs elsewhere, an INDEX that no longer matches its folder — do NOT move or merge existing files mid-curate (that is a separate, approval-gated operation). Instead record each observation for the Step 8 report (see **Structural Observations**). Curation places new knowledge; restructuring existing knowledge is a deliberate, human-reviewed pass.

---

## Step 4: Write the Content

Write or update the target file.

**File format:**

```markdown
---
title: {Descriptive Title}
type: {source-summary | concept | entity | sop | comparison | synthesis}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
tags: [{2-4 relevant tags}]
aliases: [{short-name if the filename is dated, otherwise omit}]
related:
  - "[[related-page-stem]]"
  - "[[another-related-page]]"
---

# {Descriptive Title}

**Source:** {ticket or session that produced this knowledge} ({date})

---

## {First Concept Heading}

{Content. Imperative voice for procedures. Descriptive voice for explanations.}

**How to apply:** {One concrete sentence about when and how to use this.}

## {Second Concept Heading}

...
```

**Frontmatter rules:**
- `type` must be one of the types defined in SCHEMA.md
- `tags` should use existing tags from the wiki where possible (check other pages)
- `related` must point to real pages that exist in the wiki. Check ALIASES.md and the section INDEXes. Aim for 3-5 related links per page.
- `aliases` is required for dated filenames (e.g., `2026-04-25-store-locations.md` gets alias `store-locations`)

**Wikilink enrichment (mandatory):**

Every promoted page must contain 3-5 `[[wikilinks]]` in the body text, linking to related pages in the same wiki. These create edges in the knowledge graph.

Rules for placing wikilinks:
- First mention of a known concept or entity gets a wikilink: "The [[architecture-overview]] shows..."
- Cross-section references are high-value: a stack/ page linking to a domain/ concept
- Use the page stem or an alias from ALIASES.md as the link target
- For cross-wiki references, use `[[wiki-id::page-stem]]` syntax
- Do not wikilink common English words. Only link to actual wiki pages.
- Check ALIASES.md for the canonical name before linking

**Graph-ready frontmatter (mandatory for all promoted pages):**

The `related:` field in frontmatter serves double duty: human-readable cross-references AND machine-parseable graph edges. Ensure:
- Every `related:` entry uses the `"[[page-stem]]"` wikilink syntax (quoted, double-bracketed)
- Include at least 2 related pages (prefer 3-5)
- Classify edge types where useful:
  ```yaml
  related:
    - "[[architecture-overview]]"          # context
    - "[[dac-branch-model]]"               # depends-on
    - "[[webclient-body-serialization]]"    # same-domain
  ```
- The `tags:` field enables topic clustering in graph visualizations. Use existing tags from sibling pages.

**Link validation:** Before writing a wikilink, verify the target exists:
1. Check ALIASES.md for the alias
2. Glob the section for the page stem
3. If the target doesn't exist, skip the link or add a `# TODO: page not yet created` comment in `related:`

**Quality rules:**
- No content more than 300 words per section heading. If it exceeds that, split into two files.
- The "How to apply:" line is mandatory for every procedural or gotcha item. It tells the next agent what to DO with the knowledge, not just what to know.
- No placeholder text. No "TODO: populate this section." Write real content or skip it.
- No bullet lists of things you plan to add. If the content isn't ready, don't write the file.

---

## Step 5: Update the Section INDEX

After writing or updating a file, update the section's `INDEX.md`.

**If the section INDEX has bootstrap placeholder text** (lines containing `*Section bootstrapped`), DELETE the placeholder before adding real content. Do not append below it.

Add a one-line entry in this format:

```markdown
- **[filename.md](filename.md)** — {One sentence: what this file contains, what gotcha it explains, what it teaches}. {Where the knowledge came from, e.g., "Learned from SPV-165, 2026-04-21."}.
```

The one-liner must give the reader enough context to decide whether to open the file. Phrases like "contains information about X" are not acceptable. "Explains the dual-header 401 cause and fix when Apollo Router propagates both Authorization and userAuthorization" is.

---

## Step 5.5: Update ALIASES.md and LOG.md

### ALIASES.md

For every promoted page with a dated filename (e.g., `2026-04-25-store-locations-data-pipeline.md`), add an alias entry:

```markdown
| store-locations | stack/data-pipeline/2026-04-25-store-locations-data-pipeline.md | Store location pipeline overview |
```

The alias is the semantic slug (what a reader would type in a wikilink), NOT the full dated filename.

Also add aliases for pages that have multiple common names. Check the `aliases:` field in the page's frontmatter for candidates.

### LOG.md

Append a batch entry to LOG.md:

```markdown
## {YYYY-MM-DD}

- **PROMOTE** — Promoted N inbox entries: {one-liner per file}
- **ALIAS** — Added N aliases to ALIASES.md
```

---

## Step 6: Update the Root INDEX

For every nugget that earned a root INDEX row (classified in Step 2b):

**Understand lane** — add a row:
```
| {Natural question the reader would ask} | [{file or section link}]({path}) |
```

**Blocked lane** — add a row:
```
| {Specific observable symptom, service + error} | {Concise likely cause} | [{file link}]({path}) |
```

The Symptom column must be specific. "401 error" is too generic. "Gateway → subgraph returns 401 when both auth headers sent" is correct.

**Do Something lane** — add a row:
```
| {Imperative task description} | [{file or section link}]({path}) |
```

Also update the "Last updated" date at the top of INDEX.md.

---

## Step 7: Mark Inbox Entries as Promoted

After all nuggets from an inbox entry have been processed (written to files, section INDEXes updated, root INDEX updated), mark the entry as promoted in `inbox/INDEX.md`.

Change its Status cell from `pending` to `promoted`.

If some nuggets from an entry were skipped (need human judgment, insufficient detail, or conflict with existing content), mark the entry as `partial` and add a `Notes` column explaining what was skipped and why.

---

## Step 7b: Archive Resolved Entries (garbage collection)

The inbox is a **hot work queue**, not an archive. Once an entry reaches a terminal status it must leave the hot path, or the folder and ledger grow unbounded and every consumer that counts inbox files (the scheduled drain's `inbox-guard.sh`, lint check 8) reads a false backlog.

After Step 7, for every entry whose final status is **terminal** (`promoted`, `done`, or `skipped` — NOT `pending` or `partial`, which stay hot until resolved):

1. Determine the year from the entry's date prefix (e.g. `2026-06-08-...` → `2026`); fall back to the current year if undated.
2. Move the raw file out of the hot path, preserving git history:
   ```
   mkdir -p {wiki-root}/inbox/archive/{YYYY}/
   git -C {repo-root} mv {wiki-root}/inbox/{file} {wiki-root}/inbox/archive/{YYYY}/{file}
   ```
   If the file is untracked, use a plain `mv` instead of `git mv`.
3. Move its row out of the live `inbox/INDEX.md` table and append it to `inbox/archive/INDEX.md` (create that ledger with a header if missing). Preserve the full Status cell (it holds the promotion provenance: which pages received which nuggets). The live ledger now shows ONLY `pending` and `partial` rows.

**Never delete a raw entry.** Archival is a move, fully reversible via git. The promotion record also lives in `LOG.md`, so provenance survives in three places: the archived file, the archive ledger, and LOG.md.

After archiving, the live inbox folder and ledger reflect true remaining work, so `inbox-guard.sh` (which counts `*.md` files at `-maxdepth 1`) and lint check 8 become accurate for free.

---

## Step 7.5: Update Graph Index

After all entries are promoted, regenerate the wiki link graph data file.

Write to `documentation/bibliotheque/GRAPH_DATA.json`:

```json
{
  "generated": "YYYY-MM-DDTHH:MM:SS",
  "nodes": [
    { "id": "page-stem", "label": "Page Title", "section": "stack", "type": "concept", "tags": ["bigquery", "adapter"] }
  ],
  "links": [
    { "source": "page-stem-a", "target": "page-stem-b", "type": "related" }
  ]
}
```

**How to generate:**
1. Glob all `.md` files under `documentation/bibliotheque/` (excluding inbox/, SCHEMA.md, ALIASES.md, LOG.md, INDEX.md)
2. For each file, parse the YAML frontmatter to extract: title, type, tags, related, aliases
3. For each file, scan the markdown body for `[[wikilinks]]` (skip content inside fenced code blocks)
4. Build nodes from files, links from both `related:` frontmatter and inline `[[wikilinks]]`
5. Resolve aliases to canonical page stems using ALIASES.md

This JSON file is consumed by wiki-graph visualization components (e.g., react-force-graph-2d). It is regenerated on every librarian run.

**Key gotcha:** Never use ResizeObserver to feed dimensions back into ForceGraph2D (causes infinite render loop). This is a consumer concern, but noting it here since the librarian owns the data contract.

---

## Step 8: Report

Output a structured report to the user:

```
## Bibliothèque Inbox Curation Report

**Entries processed:** N
**Entries promoted:** N
**Entries partial:** N (with reason)
**Files created:** [list with one-liner on each]
**Files updated:** [list]
**Root INDEX rows added:** [Understand: N, Blocked: N, Do Something: N]

### Structural changes
[New sections created this run, if any: name + charter + which nuggets motivated each. Empty if none.]

### Structural observations / reorg suggestions
[Drift noticed while placing nuggets, NOT acted on: sections mixing concerns, topics split across sections, files that belong elsewhere, INDEX/folder mismatches. Also list new-section *proposals* (option D, propose-not-create) parked in PROPOSALS.md. Each line is an observation for a future approval-gated restructuring pass — never auto-executed during curate. Empty if none.]

### Needs Human Judgment
[List any nuggets where classification was ambiguous or conflicted with existing knowledge. Propose a resolution; don't block on it.]
```

---

## Edge Cases

### Conflicting information
If an inbox entry contradicts an existing Bibliothèque file, do NOT overwrite the existing file. Add a `## Conflicting Information` section to the existing file noting the discrepancy, linking the inbox entry, and flagging for human review.

### Duplicate nuggets
If a nugget is already represented in the root INDEX (same symptom, same destination), skip adding a duplicate row. Enhance the existing file if the new entry adds depth.

### Meta-knowledge about the Bibliothèque itself
Nuggets about how to structure the Bibliothèque (three-lane catalog design, section trigger language, bootstrap hygiene) do NOT go in `stack/` or `operations/`. Route them to:
1. `documentation/process/documentation-standards.md` — if they extend the three-layer model
2. `bibliotheque/PROPOSALS.md` — if they are improvements not yet implemented
3. Global `~/.claude/CLAUDE.md` or project `CLAUDE.md` Context Engineering section — if they are agent behavior rules

### Project state snapshots
Nuggets like "retell-service not active in prod as of 2026-04-21" are project state, not reusable operational knowledge. Route them to the relevant ticket's `STATUS_SNAPSHOT.yaml` or `reports/status/`, not the Bibliothèque.

### Tooling patches already applied
If a nugget says "Skill X was patched with a warning" and that patch is confirmed in place, the entry is already handled. Mark it promoted but skip creating a Bibliothèque file (the fix lives in the skill itself).

---

## Classification Examples

These worked examples illustrate the classification logic for common entry types.

**Example 1: "DAC Branch Model" (from SPV-165 crawl)**
- Content: push to `dev`, MRs for uat/main, never push to main/uat directly.
- Section: `operations/` (this is an operational procedure for deploying to DAC repos).
- Root lane: Do Something ("Deploy to a DAC repo" → `operations/INDEX.md`).
- Also: Blocked ("DAC pipeline ran on main/prod unexpectedly" → file with the root cause).

**Example 2: "WebClient.bodyValue double-serialization"**
- Content: passing a pre-serialized String to bodyValue causes 400.
- Section: `stack/` (service-to-service behavior, Java client gotcha).
- Root lane: Blocked ("Service → gateway returns 400 / bodyValue with String causes double-serialization").

**Example 3: "Three-Lane Catalog Pattern"**
- Content: how to structure the Bibliothèque root INDEX into three intent lanes.
- Section: NOT in stack/ or operations/ — this is meta.
- Route to: `documentation/process/documentation-standards.md` (extends the three-layer model) AND update this skill's reference file.
- Root lane: None (this is internal maintenance knowledge, not reader-facing).

**Example 4: "RetellFilterCriteria timestamps use epoch milliseconds"**
- Content: API contract detail for Retell API.
- Section: `stack/` (could be a new file `retell-api-timestamp-format.md` or appended to an existing retell file).
- Root lane: Blocked if teams are hitting NumberFormatException; otherwise section-only.
- Also check: `~/.claude/library/context/retell-api-v2-reference.md` — if it belongs there instead, route it there and note the cross-reference.

**Example 5: "Single CLAUDE.md trigger (one front door)"**
- Content: don't add individual file paths to CLAUDE.md on-demand table; use one catalog trigger instead.
- Section: meta-pattern → `documentation/process/documentation-standards.md` or CLAUDE.md context engineering section.
- Root lane: None.
- Action: Update the relevant CLAUDE.md with the rule, mark inbox entry promoted.
