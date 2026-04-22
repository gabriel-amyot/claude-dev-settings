---
name: morning-primer
description: "Standalone daily recon. No transcript required. Queries Jira + local state, produces a primer document and mission packs for actionable tickets. Invocation: /morning-primer or /morning-primer --sprint {SPRINT-ID}"
user_invocable: true
---

# Morning Primer Skill

## Invocation

```
/morning-primer [--sprint SPRINT-ID]
```

**Examples:**
- `/morning-primer` — runs against active sprint
- `/morning-primer --sprint SP-42` — runs against a specific sprint

## Purpose

Standalone daily recon. No transcript required. Queries Jira + local state, produces a primer document and mission packs for actionable tickets.

## Output Locations

Both outputs land in `daily-brief/` at the project-management root:

| File | Description |
|------|-------------|
| `daily-brief/YYYY-MM-DD-primer.md` | Human-readable daily primer |
| `daily-brief/YYYY-MM-DD/mission-pack-{TICKET}-{date}.yaml` | One per actionable ticket |

---

## Execution Flow

### Phase 1 — Parallel Recon

Spawn **3 Sonnet subagents simultaneously**:

**Subagent A — Jira sprint sweep:**
Use the `/jira` skill with `--org klever`. Query active sprint tickets. Return: ticket ID, status, assignee, AC count, last comment date. Sort: blocked > in-progress > open. If `--sprint` flag was provided, use that sprint instead of the active one.

**Subagent B — Local state sweep:**
Read `tickets/*/STATUS_SNAPSHOT.yaml` for all non-archived tickets (scan `tickets/` but exclude `tickets/archive/`). Check each for: `night-crawl-sendoff.yaml` presence in `reports/status/` (pending vs approved), spec-analysis file presence. Return per-ticket readiness state.

**Subagent C — CI sweep (best-effort):**
Use `/gitlab --org klever` to check pipeline status on active branches. Return: any red/failed pipelines with branch names. If GitLab is unreachable (IAP expired, etc.), return `status: unavailable` and continue. This subagent failing does **not** block Phase 2.

---

### Phase 2 — Synthesis (Opus orchestrator)

Combine all three subagent outputs. Apply priority:
- **P0** — blocked, failing CI
- **P1** — in-progress, ready for pickup
- **P2** — open, needs spec

Write `daily-brief/YYYY-MM-DD-primer.md` using this format:

```markdown
# Morning Primer — YYYY-MM-DD

## Sprint Health
[1-2 sentence summary: tickets in flight, any CI red, any blockers]

## P0 — Needs Immediate Attention
[Ticket | Status | Issue | Suggested action]

## P1 — In Progress / Ready for Pickup
[Ticket | Status | ACs | Readiness]

## P2 — Open / Needs Spec
[Ticket | Status | Notes]

## CI Status
[Green / Red pipelines, branch names]
```

---

### Phase 3 — Mission Pack Generation (Sonnet)

For each ticket classified as P1 with `ready_for_pickup: true` (has ACs, not blocked, no approved sendoff already running):

Write `daily-brief/{date}/mission-pack-{TICKET}-{date}.yaml`:

```yaml
ticket_id: KTP-XXX
date: YYYY-MM-DD
source: morning-primer
priority: P0 | P1 | P2
jira_status: "..."
ac_count: N
context_hints:
  - "Existing pattern in: ..."
  - "Related ADR: ..."
blockers: []
ready_for_pickup: true
```

Context hints come from Subagent B's local state sweep — any related files found in `reports/architecture/` or agent-os directories.

---

### Phase 4 — Human Approval Gate

Display the primer inline.
List all generated mission packs with their file paths.
Print:

```
Mission packs ready:
  KTP-XXX: daily-brief/{date}/mission-pack-KTP-XXX-{date}.yaml
  ...

Reply `run KTP-XXX` to pass a mission to /pickup-ticket.
Reply `run all` to queue all P1 missions in sequence.
Reply `skip` to dismiss without running.
```

**On `run KTP-XXX`:** invoke `/pickup-ticket KTP-XXX` (optionally noting the mission pack path as context).
**On `run all`:** invoke pickup-ticket for each P1 ticket in priority order.
**On `skip`:** dismiss without running.

---

## Model Selection

- **Recon subagents (Phase 1):** Sonnet (3 parallel)
- **Synthesis (Phase 2):** Opus
- **Mission pack generation (Phase 3):** Sonnet
