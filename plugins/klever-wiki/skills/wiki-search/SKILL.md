---
name: klever-wiki-search
description: "Search and navigate the Klever Notion Wiki. Use when looking for SOPs, processes, team knowledge, tools, onboarding info, or any Klever organizational information. Triggers on: wiki, SOP, process, how-to, Klever knowledge, notion, team page, onboarding, AdOps, Account Management, Finance, Sales, Marketing."
version: 1.0.0
---

# Klever Wiki Search

You have access to the full Klever Notion Wiki v2, cached locally at the Klever project management repo.

## Data Location

```
~/Developer/grp-beklever-com/project-management/documentation/notion-wiki/
```

## Resolution Order (progressive disclosure)

Follow this order strictly. Start narrow, go deep only when needed.

### Level 1: Orientation
Read `INDEX.md` first. It contains:
- Wiki topology (section tree)
- SOP hotspot table (which teams have SOPs and where)
- Cache protocol rules
- Directory layout

### Level 2: Locate
Read `FULL_INDEX.md` to find the exact page. It indexes all 1,551 pages with:
- Section headers with page counts
- Relative file paths into `export/`
- Notion IDs for each page
- Deduplicated database entries

### Level 3: Summarize
Read `pages/{team}.md` for curated team summaries. These have YAML frontmatter with `notion_id`, `last_cached`, `status`. Good for quick overviews and cross-references between teams.

### Level 4: Deep Content
Read `export/{Section}/{Page}.md` for full Notion page content. This is where step-by-step SOPs, detailed procedures, roles & responsibilities, and tool guides live.

### Level 5: Databases
Read `agent-hub/*.csv` or `export/**/*.csv` for structured data (capabilities catalog, tools tracker, roles databases).

## Section Quick Reference

| Section | Key Content |
|---------|-------------|
| **AdOps** | Campaign ops, Ad Ops Processes (SOP hub), Roles & Responsibilities, QA, Reporting, Targeting, Measurement |
| **Account Management** | AM SOPs and Workflows, Training, Proposals, SLAs, Tools & Platforms, Case Studies |
| **Sales** | Sales Process, Onboarding, Capabilities Catalog, Contracts/MSAs, Forecasting |
| **Marketing** | Event Process, Approval Process, List Building, Brand Guidelines, Competitive Landscape |
| **Finance** | Credit Application, Vendor Onboarding, Expense Policy, Contract Review, Billing (6 SOPs) |
| **Operations** | Communication Guidelines, Email Guidelines, Meeting Structure, Vendor List, Privacy |
| **Product** | Grid/Planner, Proximity, Roadmap, Technical Docs, Testing/QA, Experiments |
| **Technology** | Proximity Portal, Tech Requests, AdOps Tech Support, Third-Party AdTech |
| **Analytics** | Tableau, Reporting Best Practices, Naming Conventions, Client Dashboard |
| **AI Resources** | LLM Policy, Claude at Klever, AI Tools Tracker, AdOps AI Tools |

## Freshness

Each `pages/*.md` file has a `last_cached` frontmatter field. If older than 7 days and the user has Notion MCP connected, offer to refresh by fetching the page via `notion_id`. Never delete files. Only add or update.

## Response Format

1. State which page(s) the answer comes from (with file path)
2. Provide the relevant content directly
3. If content might be stale, note the cache date
4. If multiple pages are relevant, synthesize across them

$ARGUMENTS
