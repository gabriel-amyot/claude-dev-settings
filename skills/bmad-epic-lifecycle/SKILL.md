---
name: bmad-epic-lifecycle
description: "Full BMAD pipeline from concept through ship. Uses persona subagents (John, Winston, Amelia, Quinn, Leo) with human gates between phases. Triggers: 'full lifecycle', 'BMAD end-to-end', 'concept to ship', 'epic lifecycle', 'full BMAD pipeline'."
nav:
  bay: build
  when: "Full BMAD concept-to-ship pipeline with persona subagents and human gates."
  when_not: "Single ticket (use /dark-factory). Quick task without ceremony."
  personas: [john, winston, amelia, quinn, leo, mary]
---

# BMAD Epic Lifecycle

Run the full BMAD pipeline for a feature: concept → PRD → architecture → tickets → implement → review → ship.

**Usage:** `/bmad-epic-lifecycle <description-or-concept-file> [--epic EPIC-ID] [--start-at PHASE]`

## Personas (MUST READ from disk, never improvise)

| Role | Persona | File |
|------|---------|------|
| PM | John | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/pm.md` |
| Architect | Winston | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/architect.md` |
| Developer | Amelia | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/dev.md` |
| QA | Quinn | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/qa.md` |
| Spec Coach | Leo | See BMAD persona guide |

## Phase 1: Concept Roundtable (John)

John reviews the concept/description and produces:
- Problem statement
- Target user and value proposition
- Scope boundaries (in/out)
- Success criteria
- Dependencies and risks

Output: `tickets/{EPIC}/reports/architecture/concept-{date}.md`

## Phase 2: PRD (John)

John writes a Product Requirements Document:
- User stories with acceptance criteria
- Feature breakdown
- Priority ordering (MoSCoW)
- Technical constraints from Phase 1

Output: `tickets/{EPIC}/reports/architecture/prd-{date}.md`

## ---- HUMAN GATE: User reviews concept + PRD ----

Present concept and PRD. Ask: "Proceed to architecture?"

## Phase 3: Architecture (Winston)

Winston designs the technical approach:
- System design with component diagram
- Data model changes
- API contract additions/changes
- ADR for any architectural decisions
- Risk assessment

Output: `tickets/{EPIC}/reports/architecture/design-{date}.md`

## ---- HUMAN GATE: User reviews architecture ----

## Phase 4: Ticket Breakdown

Break the PRD into implementable tickets:
- Create epic in Jira via `/jira` skill (if --epic not provided)
- Create child stories with ACs
- Scaffold local ticket folders via `/ticket-init`

## Phase 5: AC Quality Gate (Leo — blocking)

Leo reviews every AC for:
- Observable outcomes (not task lists)
- Given/When/Then structure
- Testability
- No vague language

If Leo rejects, rewrite ACs before proceeding.

## Phase 6: Implementation (Amelia)

For each ticket in priority order:
- Use sprint-crawl for autonomous execution, OR
- Implement interactively with the user

Commit per AC. Push branches. Create PRs.

## Phase 7: Adversarial Review (Quinn + Leo — blocking)

Run `/crawl-adversarial-review-cascade` on the implementation:
- Quinn: code quality, test coverage, silent failures
- Leo: AC coverage, spec compliance

Fix CRITICAL/HIGH findings before proceeding.

## Phase 8: Ship

- Push branches, create PRs
- Run `/pre-ship-check` across all repos
- Promote ADRs from `tickets/{EPIC}/` to `documentation/architecture/adr/`

## Phase 9: Handoff

Write closing summary. Update STATUS_SNAPSHOT. Archive ticket if complete.

## Rules
- Never skip human gates (Phases 2→3 and 3→4)
- Always read persona files from disk before adopting a role
- Use Sonnet for mechanical subagents, Opus for reasoning
- `--start-at` allows resuming from any phase (reads prior phase outputs)
