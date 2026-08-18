---
name: ticket-inventory-refresh
description: Refresh Jira ticket inventory by diffing open tickets against local folder state. Use when user says "refresh my backlog", "ticket inventory", "what tickets do I have", "update ticket index", "clean up my board". Org-scoped via cwd detection.
nav:
  bay: ops
  when: "Refresh Jira ticket inventory. Diff open tickets against local folder state."
  when_not: "Sprint management (use /klever-sprint-mgmt). Individual ticket details (use /jira)."
---

# Ticket Inventory Refresh

Fetches all open Jira tickets assigned to the user, diffs against local ticket folders, reports gaps, and updates the ticket index.

**Usage:**
```
/ticket-inventory-refresh                    # Full refresh for current org
/ticket-inventory-refresh --stale-only       # Only flag tickets >90 days without update
/ticket-inventory-refresh --epic KTP-453     # Scope to one epic
```

## Step 0: Detect Org

```
If PWD contains /grp-beklever-com → org = klever, PM_ROOT = ~/Developer/grp-beklever-com/project-management
If PWD contains /supervisr-ai    → org = supervisrai, PM_ROOT = ~/Developer/supervisr-ai/project-management
```

## Step 1: Fetch Open Tickets from Jira

```bash
cd ~/.claude/skills/jira
python3 jira_skill.py search --org {org} --jql "assignee = currentUser() AND statusCategory != Done ORDER BY priority DESC, updated DESC"
```

If `--epic` is provided, add `AND \"Epic Link\" = {EPIC}` to the JQL.

Collect: key, summary, status, priority, epic link, updated date.

## Step 2: Scan Local Folders

List all ticket directories under `{PM_ROOT}/tickets/`. For each, read `STATUS_SNAPSHOT.yaml` if it exists to get local status.

Build a local inventory: `{ ticket_key: { path, local_status, last_modified } }`

## Step 3: Diff and Classify

Compare Jira vs local:

| Category | Meaning |
|----------|---------|
| **New** | In Jira but no local folder |
| **Closed** | Local folder exists but Jira status is Done/Closed |
| **Status drift** | Local STATUS_SNAPSHOT.yaml disagrees with Jira status |
| **Missing folder** | Assigned to user, open in Jira, no local folder |
| **Stale** | Last Jira update >90 days ago and still open |
| **Orphan** | Local folder exists but ticket not assigned to user or not found in Jira |

## Step 4: Present Report

```
## Ticket Inventory Report — {org} ({date})

**Open in Jira:** N tickets
**Local folders:** N folders
**Coverage:** N% (folders / open tickets)

### New (in Jira, no local folder) — N
| Key | Summary | Status | Priority | Epic |
...

### Stale (>90 days without update) — N
| Key | Summary | Last Updated | Days Stale |
...

### Status Drift — N
| Key | Jira Status | Local Status | Action Needed |
...

### Orphan Folders — N
| Folder | Jira Status | Notes |
...

### Recommended Actions
1. Create folders for: KTP-XXX, KTP-YYY (missing coverage)
2. Archive folders for: KTP-ZZZ (Done in Jira)
3. Review stale: KTP-AAA (145 days, still To Do)
```

## Step 5: Update Index (optional)

If `{PM_ROOT}/tickets/TICKET_INDEX.md` exists, update it with current state. If not, offer to create one.

## Notes
- Run monthly or when backlog feels overwhelming
- Pairs with `/archive` for closing out done tickets
- Pairs with `/ticket-init` for scaffolding missing folders
