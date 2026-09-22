---
description: "Force refresh stale Klever Wiki pages from Notion. Use when wiki content seems outdated or after someone updates Notion."
---

# Wiki Refresh

Check and update the local Klever Wiki cache against Notion.

## Steps

1. **Scan for stale pages**: Read all files in `~/Developer/grp-beklever-com/project-management/documentation/notion-wiki/pages/*.md` and check their `last_cached` frontmatter date.

2. **Report staleness**: List all pages older than 7 days (or 3 days for SOP pages) with their cache dates.

3. **Check MCP availability**: Try to use the Notion MCP tools (`mcp__notion__notion-fetch`). If not available, report which pages are stale and stop.

4. **Refresh stale pages**: For each stale page:
   a. Read the `notion_id` from frontmatter
   b. Fetch the page via `mcp__notion__notion-fetch` using the ID
   c. Update the local `.md` file body with fresh content
   d. Bump `last_cached` to today
   e. If the page title changed, update `FULL_INDEX.md`

5. **Discover new pages**: When fetching a page, look for child page references not yet in the cache:
   a. Create new cache files for discovered pages
   b. Add them to `FULL_INDEX.md`
   c. Log additions in the `INDEX.md` change log

6. **Handle missing pages**: If a fetch returns 404:
   a. Do NOT delete the file
   b. Set `status: archived` and `archived_on: {today}` in frontmatter
   c. Log in change log

7. **Report results**: Summarize what was refreshed, discovered, and archived.

## Cache Protocol Rules
- **Never destructive.** Never delete files. Only add, update, or mark as archived.
- **Additive growth.** New pages discovered during refresh get their own cache files.
- **SOP pages** (tagged `<<<< SOP` in INDEX.md) have a 3-day staleness threshold.
- **Archive pages** are never refreshed.

$ARGUMENTS
