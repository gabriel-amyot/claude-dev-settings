---
name: sprint-screenshot-capture
description: Capture visual evidence (screenshots) for frontend ticket ACs. Works at ticket level or sprint level (all open tickets in progress/review). Use when user says "capture screenshots", "screenshot evidence", "visual proof", "validate ticket visually", "evidence for closing". Integrates as pre-step for /sprint-close.
nav:
  bay: review
  when: "Capture visual evidence screenshots for frontend ticket ACs."
  when_not: "Running test suites (use /klever-test). Backend validation."
  org: [klever]
---

# Sprint Screenshot Capture

Captures visual evidence for frontend acceptance criteria. Navigates the app, performs AC trigger actions, and saves annotated screenshots. Works on a single ticket or batch-captures for all in-flight tickets.

**Usage:**
```
/sprint-screenshot-capture KTP-609                    # Single ticket
/sprint-screenshot-capture --sprint                   # All my In Progress + In Review tickets
/sprint-screenshot-capture --sprint --epic KTP-130    # Scoped to one epic
/sprint-screenshot-capture KTP-609 --ac 1,3           # Specific ACs only
```

## Step 0: Preflight

Before capturing anything, verify the local stack:

1. **Frontend running?** `curl -s http://localhost:3000 | head -1` returns HTML.
2. **Backend running?** `curl -s http://localhost:8090/actuator/health` returns UP.
3. **Dev environment accessible?** `curl -s https://demo.dev.beklever.com` (alternative to local).

If nothing is running:
```
Local stack not detected. Options:
1. Run /klever-local-stack to start locally
2. Use --target dev to capture from demo.dev.beklever.com (requires IAP cookie)
```

Stop and suggest remediation. Do NOT proceed without a running target.

## Step 1: Resolve Tickets

**Single ticket mode (`KTP-XXX`):**
- Fetch ticket from Jira: `python3 ~/.claude/skills/jira/jira_skill.py get KTP-XXX --org klever`
- Read local AC file if exists: `tickets/KTP/{EPIC}/KTP-XXX/jira/ac/ac.yaml` or `jira/ac.yaml`

**Sprint mode (`--sprint`):**
- Fetch all in-flight tickets:
  ```bash
  python3 ~/.claude/skills/jira/jira_skill.py search --org klever \
    --jql "assignee = currentUser() AND status in ('In Progress', 'In Review/Testing') ORDER BY priority DESC"
  ```
- If `--epic` provided, add `AND \"Epic Link\" = {EPIC}` to JQL
- Filter to tickets that have frontend ACs (heuristic: summary contains "UI", "display", "show", "map", "panel", "menu", "button", "filter", "dropdown", OR AC text mentions visual elements)
- Prioritize In Review tickets over In Progress (closer to closure)

## Step 2: Classify ACs

For each ticket, read the acceptance criteria and classify each AC:

| Type | Needs Screenshot | Example |
|------|-----------------|---------|
| **Visual** | YES | "Map shows conversion totals in circles" |
| **Behavioral** | YES | "Clicking a store opens the detail panel" |
| **Data correctness** | MAYBE | "Panel shows visit frequency" (screenshot if visible in UI) |
| **Backend only** | NO | "Endpoint returns 200 with correct payload" |
| **Config/setup** | NO | "Feature flag wired in Spring profile" |

Present the classification to the user:
```
KTP-609: Display store visit metrics
  AC-1: Panel shows Visitors count       → VISUAL ✓
  AC-2: Panel shows Visit Frequency      → VISUAL ✓
  AC-3: Panel shows Dwell Time           → VISUAL ✓
  AC-4: Backend adapter wired            → BACKEND (skip)

Capturing 3 of 4 ACs. Proceed?
```

If `--ac 1,3` was specified, only capture those ACs.

## Step 3: Navigate and Capture

For each visual AC, use browser automation to:

1. **Navigate** to the relevant page (Measurement Map, store detail panel, etc.)
2. **Set up state:** select the right advertiser, date range, filters
3. **Perform the AC trigger action:** click store pin, open panel, select dropdown, etc.
4. **Wait** for data to load (check for loading spinners, empty states)
5. **Capture screenshot** with descriptive filename

**Filename convention:**
```
{TICKET}-AC{N}-{slug}.png
```
Examples: `KTP-609-AC1-visitors-count.png`, `KTP-609-AC2-visit-frequency.png`

**Save location:**
```
tickets/KTP/{EPIC}/{TICKET}/design/screenshots/
```

Create the directory if it doesn't exist.

**Capture approach (in priority order):**

1. **agent-browser skill** (preferred):
   ```
   Skill: agent-browser:agent-browser
   Args: "Navigate to http://localhost:3000/proximity, select Shrimp Basket, click store pin, screenshot detail panel"
   ```

2. **Chrome MCP tools** (fallback):
   - `mcp__claude-in-chrome__navigate` to the page
   - `mcp__claude-in-chrome__computer` to interact
   - `mcp__claude-in-chrome__read_page` to verify content loaded
   - Screenshot via `mcp__claude-in-chrome__computer`

3. **Playwright MCP** (headless):
   - `mcp__plugin_playwright_playwright__browser_navigate`
   - `mcp__plugin_playwright_playwright__browser_take_screenshot`

## Step 4: Generate Evidence Summary

After all captures, produce a summary table:

```markdown
## Screenshot Evidence — {date}

| Ticket | AC | Description | Screenshot | Status |
|--------|-----|------------|------------|--------|
| KTP-609 | AC-1 | Visitors count displayed | [KTP-609-AC1-visitors-count.png](./KTP-609-AC1-visitors-count.png) | ✓ Captured |
| KTP-609 | AC-2 | Visit frequency displayed | [KTP-609-AC2-visit-frequency.png](./KTP-609-AC2-visit-frequency.png) | ✓ Captured |
| KTP-609 | AC-3 | Dwell time displayed | — | ✗ Empty state (no data) |
| KTP-609 | AC-4 | Backend adapter wired | — | Skipped (backend) |
```

Save this summary to:
```
tickets/KTP/{EPIC}/{TICKET}/reports/reviews/screenshot-evidence-{date}.md
```

## Step 5: Integration Points

**With `/sprint-close`:** When sprint-close runs, it checks for existing screenshot evidence files before asking for visual proof. If evidence exists, reference it in the closing comment.

**With `/post-comment`:** Screenshots can be attached to Jira closing comments. The evidence summary provides the file paths.

**With `/klever-test`:** If klever-test's AC validation mode found issues, sprint-screenshot-capture can re-capture after fixes to confirm resolution.

## Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| All screenshots show login page | IAP cookie expired | `git fetch` any Klever repo to refresh IAP |
| Screenshots show empty panels | Backend not returning data | Check backend logs, verify advertiser has data |
| agent-browser times out | Local stack crashed | Restart with `/klever-local-stack` |
| "No visual ACs found" | Ticket is backend-only | Confirm with user, skip screenshot capture |
| Screenshot shows loading spinner | Slow backend response | Increase wait time, retry after 5s |

## Notes
- Screenshots are the primary evidence for frontend AC closure. Without them, tickets cannot be closed per team convention.
- In sprint mode, prioritize In Review tickets over In Progress (closer to closure).
- This skill codifies the exact workflow that was previously re-explained each session.
