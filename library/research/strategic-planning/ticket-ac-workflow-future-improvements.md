# Future: AC-Centric Ticket Workflow

**Context:** Emerged from KTP-182 ticket folder restructure session (2026-03-13).
The new ticket structure introduces per-AC files as agent scratchpads. This doc captures
the intended workflow that builds on top of that foundation.

---

## Vision

Every ticket is driven by its acceptance criteria. AC files are the unit of work — not
tasks, not sprints. Agents plan against AC, implement against AC, and validate against AC.

---

## Phase: PRD Generation (`plan/PRD.md`)

**Trigger:** After pickup-ticket runs and spec clarity is CLEAR.

**Process:** Interactive session with BMAD + user.
- Input: `jira/description.md`, `jira/ac/index.yaml`, codebase context from Phase 5
- Output: `plan/PRD.md` at ticket root (NOT in BMAD's `_BMAD_OUTPUT/`)
- Content: What + why in depth, constraints, non-goals, open questions resolved

**Note:** pickup-ticket should create a stub `plan/PRD.md` capturing intent at pickup time
(title, one-sentence goal, unresolved questions). BMAD then enriches it.

---

## Phase: Task Generation (`plan/TASKS.md`)

**Trigger:** After PRD.md is approved by user.

**Process:** Agent reads PRD.md + AC files + codebase, generates nested task breakdown.
- Each task is scoped to one AC (referenced in `jira/ac/ac-NNN.md`)
- Tasks include investigation tasks, implementation tasks, and verification tasks
- Effort estimate per task
- Output: `plan/TASKS.md` with nested structure

**TASKS.md structure (proposed):**

```
# Tasks: {TICKET-ID}

## AC-1: {description}
- [ ] T1.1 Investigate: {what to explore first}
- [ ] T1.2 Implement: {what to build}
- [ ] T1.3 Verify: {how to confirm AC passes}

## AC-2: {description}
...
```

---

## Phase: Agent Scratchpad Usage (`jira/ac/ac-NNN.md`)

**During implementation:** Agents working on a specific AC update its file:
- `## Strategy` — filled at start of implementation
- `## Tasks` — links to TASKS.md items for this AC
- `## Progress Log` — running notes: what was tried, what worked, what didn't
- `## Blockers` — active blockers with date

**Key rule:** `ac-NNN.md` is never overwritten by jira_skill re-fetch. Agent notes are preserved.
Only `jira/ac/index.yaml` is refreshed (status field updated from Jira or by agents).

---

## Phase: AC Validation Gate (Final)

**Trigger:** All tasks in TASKS.md checked off, or agent signals "implementation complete."

**Process:** Validation agent reads each AC from `index.yaml`, runs or reviews tests, confirms pass/fail.
- Updates `ac-NNN.md` status field to `done` or `blocked`
- Updates `index.yaml` statuses
- Writes validation report to `reports/reviews/ac-validation-{date}.md`
- Only when all ACs are `done`: ticket can move to in_review

---

## Bulk Migration

All existing workspace tickets need migration to the new structure:
- Delete: `README.md`, `ticket-overview.md`, `jira/overview.md`, `jira/ac.yaml`, `jira/comments.yaml`
- Create: `INDEX.md`, `plan/` stubs, `jira/ac/` subfolder
- Script location (future): `~/.claude-shared-config/scripts/migrate-ticket-structure.sh`

Migration can be done ticket-by-ticket at session start, or in a bulk cleanup pass.

---

## pickup-ticket Changes Needed

1. Generate `INDEX.md` instead of `README.md`
2. Create `plan/` with stub files (PRD.md and TASKS.md with "not yet created" placeholder)
3. Reference `jira/ac/index.yaml` (not `jira/ac.yaml`) in spec clarity gate
4. Optionally: capture user intent in `plan/PRD.md` stub at pickup time (one-sentence goal)
