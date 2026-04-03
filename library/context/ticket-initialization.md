# Ticket Initialization & Organization Guide

Standards for initializing and organizing ticket folders after Jira fetch. Applies to ALL projects (Klever, Supervisr, etc.).

---

## Phase 1: Jira Fetch (Automated by `/jira` skill)

After fetching a ticket, the minimum local structure is:

```
{TICKET-ID}/
├── README.md                # Brief: ID, title, status, assignee, description excerpt
└── jira/
    ├── ticket.yaml          # Full Jira fields (key, summary, status, type, assignee, etc.)
    └── comments.yaml        # All comments (if any exist)
```

This is the **raw state** — ticket exists locally but isn't organized for work.

---

## Phase 2: Work Initialization (When you start working on a ticket)

Before writing any implementation docs, create the reports scaffold:

```
{TICKET-ID}/
├── README.md                          # Update with scope, dependencies, context
├── STATUS_SNAPSHOT.yaml               # Living current state (agents read this FIRST)
├── jira/
│   ├── ticket.yaml
│   ├── comments.yaml
│   └── ac.yaml                        # Acceptance criteria (create from Jira or define manually)
└── reports/
    ├── architecture/                  # Design docs, specs, implementation plans
    ├── implementation/                # PRDs, implementation summaries, release notes
    ├── reviews/                       # Code reviews, adversarial findings
    ├── status/                        # Historical dated snapshots, progress logs
    └── ship/                          # Shipping pipeline reports (validation, release, deploy)
```

### ac.yaml Format

```yaml
ticket: {TICKET-ID}
title: "{Ticket title}"
story_points: {N}
assignee: {Name}

criteria:
  - id: AC-1
    description: "{What must be true for this to be done}"
    points: 1
    status: not_started       # not_started | in_progress | pending_validation | done | blocked

  - id: AC-2
    description: "{Second criterion}"
    points: 1
    status: not_started
```

**Status values:** `done`, `in_progress`, `pending_validation`, `not_started`, `blocked`

---

## Phase 3: File Placement Rules

| Document Type | Location | Examples |
|---|---|---|
| Specs, data contracts, architecture docs | `reports/architecture/` | `spec-data-requirements.md`, `data-contract.md` |
| PRDs, implementation plans, summaries | `reports/implementation/` | `prd-*.md`, `*-implementation-summary-*.md` |
| Code reviews, adversarial findings | `reports/reviews/` | `*-review-*.md`, `*-adversarial-*.md` |
| Progress logs, dated snapshots, briefs | `reports/status/` | `WORK_COMPLETED.md`, `brief-for-*.md` |
| Ship reports (validation, release, deploy) | `reports/ship/` | `validation_*.md`, `release_*.md` |
| Interview notes, meeting notes | `{topic}/` at ticket root | `jaspreetInterview/`, `meeting-notes/` |
| Jira data (AC, ticket metadata, comments) | `jira/` | `ac.yaml`, `ticket.yaml`, `comments.yaml` |

### What stays at ticket root:
- `README.md`, `STATUS_SNAPSHOT.yaml`, `jira/`, topic-specific folders

### What does NOT belong at ticket root:
- Specs, PRDs, contracts → `reports/architecture/` or `reports/implementation/`
- Progress tracking, briefs → `reports/status/`
- Reviews → `reports/reviews/`

---

## Phase 4: Ongoing Maintenance

1. **Update ac.yaml** as work progresses (status changes, validation dates)
2. **Run `/status-index`** to recalculate completion and update STATUS_SNAPSHOT
3. **Dated snapshots:** Periodically copy STATUS_SNAPSHOT to `reports/status/{ticket-id}-status-snapshot-{date}.yaml`
4. **Promote artifacts:** After ticket completion, promote ADRs and contracts to `documentation/architecture/`

---

## Epic-Level Structure

```
{EPIC-ID}/
├── README.md                          # Epic overview, critical path, ticket table
├── STATUS_SNAPSHOT.yaml               # Epic-level rollup (sub-ticket completion %)
├── REPO_MAPPING.yaml                  # Maps repos/services to tickets (optional)
├── jira/ticket.yaml
├── reports/{architecture,implementation,reviews,status,ship}/
├── {SUB-TICKET-1}/
│   ├── README.md
│   ├── STATUS_SNAPSHOT.yaml
│   ├── jira/ac.yaml
│   └── reports/
└── {SUB-TICKET-2}/
```

## File Naming Convention

**Pattern:** `{context}-{type}-{date}.md`
- **context:** Service name, ticket ID, or topic (kebab-case)
- **type:** Report category (spec, architecture, prd, review, etc.)
- **date:** ISO YYYY-MM-DD (required for point-in-time, optional for living docs)
