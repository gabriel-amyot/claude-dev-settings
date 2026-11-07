---
name: vendor-api-ingest
description: "Fetch, store, index, and analyze vendor API documentation. Creates bibliotheque vendor section with API catalog, usage guide, and capabilities summary. Trigger: 'download the API docs', 'ingest the vendor docs', 'save these API pages'. Klever org. Input: list of vendor doc URLs + vendor name. Returns: indexed vendor docs in bibliotheque."
nav:
  bay: know
  when: "Fetch, store, index vendor API documentation. Creates bibliotheque vendor section."
  when_not: "API spike on undocumented API (use /api-spike). Already have vendor docs."
  org: [klever]
---

# Vendor API Ingest

## Host compatibility

Read [the shared host mapping](../../docs/skill-host-compatibility.md) before execution. Use native tools and the existing shared agent instructions. Required executors and companion skills remain real dependencies.


## Shared maintenance note (2026-10-26)

Highest priority: shared knowledge, durable memory and continuity. Preserve one library for Claude and Codex. Compatibility or maintenance issues are work to assess, not a reason to demote this area. See [the shared selection record](../../docs/harness-skill-selection.md).


Fetches vendor API documentation from URLs, stores locally, and creates an indexed reference in the bibliotheque.

## Steps

### 1. Parse Input

Accept:
- Vendor name (e.g., "Placer", "Goldfish", "TTD")
- List of documentation URLs, optionally grouped by category

### 2. Create Directory Structure

```
documentation/bibliotheque/vendors/{vendor}/
  api/
    INDEX.md          (endpoint catalog)
    {endpoint-page}.md (fetched + distilled pages)
  CLAUDE.md            (usage guide: auth, endpoint selection, constraints)
  INDEX.md             (catalog of all vendor docs)
  api-summary.md       (capabilities overview)
  {reference-pages}.md (glossary, FAQ, error codes)
```

### 3. Fetch Documentation

Use the host's available web retrieval tool for each URL. Run independent fetches in parallel grouped by category.

For each fetched page:
- Extract the meaningful content (strip nav, footer, boilerplate)
- Preserve: endpoint paths, request/response schemas, parameter descriptions, error codes
- Save as markdown in `api/{page-name}.md`

If a page fails to fetch (JS-heavy, requires login):
- Note it in the INDEX as "not fetched, reason: {reason}"
- Suggest alternative sources (spike reports, email threads, contracts)

### 4. Create API INDEX

`api/INDEX.md` should be a table:

```
| Endpoint | Method | Path | Purpose | Custom POI Support | Auth |
|----------|--------|------|---------|-------------------|------|
```

### 5. Create Vendor CLAUDE.md

Usage guide for future sessions:

Link this guide from the vendor INDEX.md so both Claude and Codex can find and read the same file. Do not assume Codex automatically loads a vendor CLAUDE.md.
- How to authenticate
- Which endpoint to use for common tasks
- Known constraints (rate limits, async polling, pagination)
- Common gotchas

### 6. Create API Summary

`api-summary.md`: high-level capabilities overview:
- What the API can do
- What it cannot do
- Data freshness and coverage
- Integration patterns (sync/async, batch/stream)

### 7. Create Vendor INDEX

`INDEX.md` at vendor level: catalog of all docs with key findings and "go here when..." triggers.

### 8. Update Bibliotheque Root

Add new vendor entry to `documentation/bibliotheque/vendors/INDEX.md` and update `documentation/bibliotheque/INDEX.md` root catalog.

### 9. Ticket-Level Analysis (if applicable)

If a ticket context exists, write a comparison report at:
`tickets/{PREFIX}/{TICKET-ID}/reports/architecture/{vendor}-api-analysis-{date}.md`

Compare: new docs vs prior research, what changed, what's new, delta analysis.

## Notes

- WebFetch can't render JS-heavy pages. Flag partial fetches explicitly.
- Some vendor docs require login (Goldfish showed this). Skill should handle gracefully: consolidate from spike/email/contract instead.
- Pattern: raw docs in `api/`, distilled reference at vendor level, ticket-specific analysis in ticket reports.
- Always update the nearest INDEX.md after creating files (context engineering rule).
