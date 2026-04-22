---
name: bibliotheque-librarian
description: Processes tribal knowledge inbox entries into the Supervisr Bibliothèque. Invoke with /bibliotheque-librarian, "curate the inbox", or "process inbox entries" to promote pending captures to the correct section and update the three-lane root catalog.
---

# Bibliothèque Librarian

Curates the tribal knowledge inbox, classifies each entry into the correct section of the Bibliothèque, and keeps the three-lane root catalog up to date.

This skill is distinct from `/bibliotheque-refresh`, which processes Notion wiki exports. This skill processes captures written by `/operationalize` and by agents during sessions.

**Bibliothèque root:** `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/`

---

## Step 0: Orientation

Read the root INDEX before touching anything:

```
documentation/bibliotheque/INDEX.md
```

Note the current state of the three lanes ("I Need to Understand Something", "I Am Blocked by an Error", "I Need to Do Something") and the Sections block. You will be adding rows and updating section descriptions. Knowing the current state prevents duplicate entries and collision.

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

---

## Step 4: Write the Content

Write or update the target file.

**File format:**

```markdown
# {Descriptive Title}

**Source:** {ticket or session that produced this knowledge} ({date})

---

## {First Concept Heading}

{Content. Imperative voice for procedures. Descriptive voice for explanations.}

**How to apply:** {One concrete sentence about when and how to use this.}

## {Second Concept Heading}

...
```

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
