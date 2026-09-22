# Skill Proposal: epic-reorganization (update)
Date: 2026-05-06
Source: KTP-130 bloat cleanup session

## Update Target
`~/.claude/skills/epic-reorganization/SKILL.md` (existing skill)

## New Learnings to Add

### Jira hierarchy gate
Before proposing nested structure, check hierarchy constraints:
- Epic can't nest under Epic (company-managed projects)
- Story can't parent Story
- Only valid chain: Epic → Story → Sub-task
- Fallback: flat epic + labels for logical grouping

### Issue linking step
After re-parenting, create "Relates" links between peer epics using REST API (curl, not jira skill).
Auth pattern: `security find-generic-password -s "claude-jira" -a "jira_{org}" -w`

### Type change is manual
Demoting Epic → Story requires manual Jira UI step. Flag this as a human action in the execution plan.

## Trigger
"split epic", "reorganize tickets", "epic is bloated", "extract tickets"

## Scope
org (klever)
