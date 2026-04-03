---
name: ticket-init
description: "Scaffold a new ticket folder with standard structure: INDEX.md, REPO_MAPPING.yaml, STATUS_SNAPSHOT.yaml, plan/ stubs, jira/ac/ subfolder, reports/ tree, and optional Jira AC fetch. Use when creating a new ticket or epic folder."
---

# Ticket Init

Scaffolds a new ticket folder following the project-management conventions.

**Usage:** `/ticket-init <TICKET-ID> [--epic <EPIC-ID>] [--jira]`

**Examples:**
```
/ticket-init SPV-60                    # New top-level ticket
/ticket-init SPV-60 --epic SPV-3       # Sub-ticket under SPV-3
/ticket-init SPV-60 --jira             # Fetch AC from Jira during init
/ticket-init SPV-60 --epic SPV-3 --jira
```

## Arguments

- `<TICKET-ID>`: Required. The ticket ID (e.g., SPV-60, KTP-42).
- `--epic <EPIC-ID>`: Optional. Parent epic. If provided, creates folder under `tickets/{EPIC-ID}/{TICKET-ID}/`.
- `--jira`: Optional. Fetch ticket details from Jira and populate `jira/` folder.

## Steps

### 1. Determine location

```
If --epic provided:
  base = project-management/tickets/{EPIC-ID}/{TICKET-ID}/
Else:
  base = project-management/tickets/{TICKET-ID}/
```

Check if the folder already exists. If it does, warn the user and stop.

### 2. Create directory structure

```
{base}/
├── INDEX.md
├── REPO_MAPPING.yaml        (if epic-level or cross-service ticket)
├── STATUS_SNAPSHOT.yaml
├── plan/
│   ├── PRD.md               (stub)
│   └── TASKS.md             (stub)
├── jira/                    (if --jira flag)
│   ├── ticket.yaml
│   ├── description.md
│   └── ac/
│       ├── index.yaml
│       └── ac-NNN.md
└── reports/
    ├── architecture/
    ├── implementation/
    ├── reviews/
    └── status/
```

### 3. Populate INDEX.md

```markdown
# {TICKET-ID}: {Title from Jira or placeholder}

**Status:** not_started | **Epic:** {EPIC-ID if provided} | [Jira](https://supervisr.atlassian.net/browse/{TICKET-ID})

## Navigation
| Section | Path | Notes |
|---|---|---|
| Metadata | jira/ticket.yaml | Status, assignee, sprint |
| Description | jira/description.md | Full ticket description |
| Acceptance Criteria | jira/ac/index.yaml | N ACs |
| Plan | plan/PRD.md | stub |
| Tasks | plan/TASKS.md | stub |

## Repos
| Repo | Path | Role |
|---|---|---|
```

### 4. Populate STATUS_SNAPSHOT.yaml

```yaml
ticket: {TICKET-ID}
epic: {EPIC-ID or null}
title: "{Title from Jira or placeholder}"
status: not_started
completion: 0
last_indexed: {current ISO timestamp}
```

### 5. Populate REPO_MAPPING.yaml (epic-level only)

Only create this file if the ticket is an epic or if `--epic` is NOT provided (top-level ticket). For sub-tickets, the parent epic's REPO_MAPPING applies.

```yaml
epic: {TICKET-ID}
repositories: {}
# Populate with: repo name, path, main_branch, cloud_run_service, terraform_repo
# See parent epic's REPO_MAPPING.yaml for examples
```

### 6. Optional Jira fetch (if --jira)

Run the Jira skill to fetch ticket details:
```
/jira get {TICKET-ID} --full
```

Parse the output and populate:
- `jira/ticket.yaml`: Full ticket metadata
- `jira/ac/index.yaml`: Extracted AC list + per-AC `ac-NNN.md` stubs
- Update INDEX.md title and status from Jira data

### 7. Report

Print summary:
```
Ticket {TICKET-ID} initialized at {base}/
  - INDEX.md ✓
  - STATUS_SNAPSHOT.yaml ✓
  - plan/ stubs ✓
  - REPO_MAPPING.yaml ✓ (or skipped for sub-ticket)
  - reports/ tree ✓
  - jira/ ✓ (or skipped)
```
