---
name: wiki-lint
description: Run health checks across one or all LLM wikis. Detects orphan pages, broken wikilinks, missing frontmatter, stale pages, duplicate aliases, INDEX drift, and inbox backlogs. Invoke with /wiki-lint, /wiki-lint --wiki klever, or /wiki-lint --all.
nav:
  bay: know
  when: "Health checks across LLM wikis: orphan pages, broken wikilinks, missing frontmatter."
  when_not: "Context engineering audit (use /context-audit). Harness audit (use /harness-audit)."
---

# Wiki Lint

> **Note:** Wiki lint is now integrated into the bibliotheque-librarian skill. 
> Use `/bibliotheque-librarian lint` for the same functionality.
> This standalone skill remains functional but will be retired in a future cleanup.

Health check tool for the LLM Wiki system. Scans one or all wikis for structural issues.

## Usage

```
/wiki-lint                    # lint current wiki (detect from cwd)
/wiki-lint --wiki klever      # lint specific wiki
/wiki-lint --all              # lint all 4 wikis
```

## Step 0: Resolve Target Wiki(s)

Read the wiki registry:
```
~/.claude-shared-config/library/WIKI_REGISTRY.yaml
```

If `--wiki` is specified, lint only that wiki. If `--all`, lint all wikis in the registry. If neither, detect from cwd:
- cwd contains `grp-beklever-com` → klever
- cwd contains `supervisr-ai` → supervisr
- cwd contains `gabriel-amyot` → personal
- cwd is `~/.claude` or `~/.claude-shared-config` → harness

## Step 1: Load Wiki State

For each target wiki, read:
1. `SCHEMA.md` — page type definitions, frontmatter spec
2. `ALIASES.md` — alias → path map
3. `INDEX.md` — root catalog
4. `LOG.md` — last operation date

Build file inventory: scan all `*.md` files recursively.

## Step 2: Run Checks

### Check 1: Orphan Pages
Pages not referenced in any INDEX.md (section or root) and not linked from any other page via `[[wikilinks]]` or `[markdown](links)`.

**Severity:** WARNING
**Output:** List of orphaned files with their section.

### Check 2: Broken Wikilinks
Extract all `[[wikilinks]]` from all pages. Check each resolves to:
- A file stem in the wiki, OR
- An alias in ALIASES.md, OR
- A cross-wiki reference (`wiki-id::page`) where the target wiki exists in the registry

**Severity:** ERROR for same-wiki broken links, INFO for cross-wiki (target may not be indexed)

### Check 3: Missing Frontmatter
Pages that lack YAML frontmatter (`---` block at top). Per SCHEMA.md, all pages should have at minimum: `title`, `type`, `created`.

**Severity:** INFO (existing pages predate the frontmatter convention)
**Output:** Count and list of pages without frontmatter.

### Check 4: Stale Pages
Pages where `updated` in frontmatter is >90 days old, or where the file modification date is >90 days old (if no frontmatter).

**Severity:** INFO
**Output:** List with last-modified date.

### Check 5: Duplicate Aliases
Check ALIASES.md for duplicate alias names (same alias pointing to different paths).

**Severity:** ERROR
**Output:** The conflicting entries.

### Check 6: INDEX-to-Disk Drift
Compare section INDEX.md file lists against actual files on disk. Report:
- Files listed in INDEX but missing from disk (ghosts)
- Files on disk but missing from INDEX (unlisted)

**Severity:** WARNING for unlisted files, ERROR for ghosts.

### Check 7: Zero-Outlink Pages
Pages with no `[[wikilinks]]`, no `[markdown](links.md)`, and no `related:` frontmatter. These pages are islands in the knowledge graph.

**Severity:** INFO
**Output:** Count and top 10 examples.

### Check 8: Inbox Backlog
Count entries whose final Status cell in `inbox/INDEX.md` is `pending` (not the raw file count, and not rows already `promoted/done/skipped`). Flag if any are >7 days old. Run Check 8.5 first so this reflects true remaining work.

**Severity:** WARNING if >5 pending, ERROR if any >14 days old.

### Check 8.5: Phantom-Pending Reconcile (AUTO-FIX)
The drift killer. `shelve` and direct session writes place knowledge into pages without updating the inbox ledger, so entries stay `pending` forever even though their content is already on disk. For each `pending` entry: read it + its curator note, identify the target page(s), and verify the page exists AND contains the nugget's distinctive content (grep 1-2 verbatim phrases).
- **HIGH confidence already-on-disk:** flip Status to `promoted (reconciled by lint YYYY-MM-DD: already on disk at <path>)`, then archive (see GC sweep).
- **Uncertain / not found:** leave `pending`, list under "needs curate". Never auto-promote on weak evidence.

**Severity:** INFO per reconciled entry; WARNING for genuinely-pending entries remaining.

### GC Sweep (AUTO-FIX)
Any entry whose Status is terminal (`promoted`/`done`/`skipped`) but whose raw file is still in the hot `inbox/`: `git mv` it to `inbox/archive/{YYYY}/` and move its ledger row to `inbox/archive/INDEX.md`. Keeps the folder, ledger, `inbox-guard.sh`, and Check 8 honest. Never delete; move only.

> **This skill now mutates** (Check 8.5 + GC sweep only): they edit `inbox/INDEX.md`, move files, and create `inbox/archive/`. Stage and commit with `knowledge: lint reconcile + archive ({wiki})`. Checks 1-8 and 9 remain read-only.

### Check 9: Wiki Infrastructure Files
Verify the wiki has all required files: SCHEMA.md, ALIASES.md, LOG.md, GLOSSARY.md, INDEX.md.

**Severity:** ERROR for missing INDEX.md or SCHEMA.md, WARNING for others.

## Step 3: Generate Report

Write the report to disk:

```
{wiki-root}/reports/lint-{YYYY-MM-DD}.md
```

Create the `reports/` directory if it doesn't exist.

**Report format:**

```markdown
# Wiki Lint Report — {Wiki Name}

**Date:** {YYYY-MM-DD}
**Files scanned:** {N}
**Checks passed:** {N}/{total}

## Summary

| Check | Status | Count |
|-------|--------|-------|
| Orphan pages | {PASS/WARN/ERROR} | {N} |
| Broken wikilinks | ... | ... |
| ... | ... | ... |

## Findings

### ERROR

{List each ERROR finding with file path and description}

### WARNING

{List each WARNING}

### INFO

{List each INFO finding}
```

## Step 4: Append to LOG.md

```markdown
- **LINT** — {N} files scanned, {errors} errors, {warnings} warnings, {info} info. Report: reports/lint-{date}.md
```

## Step 5: Present to User

Show the summary table inline. If errors exist, highlight them. Suggest fixes for the top 3 most impactful findings.
