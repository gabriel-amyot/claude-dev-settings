# Skill Proposal: ticket-inventory-refresh
Date: 2026-05-04
Source: Ticket backlog audit session

## Trigger
"refresh my backlog", "ticket inventory", "what tickets do I have", "update ticket index", "how many tickets do I have", "clean up my board"

## Scope
org (Supervisr.AI project-management repo, but pattern works for any org)

## Draft Steps
1. Fetch all open Jira tickets assigned to user via `jira_skill.py search` (org-scoped)
2. Read existing `tickets/TICKET_INDEX.md` for previous state
3. Diff: new tickets, closed tickets, status changes, priority shifts
4. Check local folder coverage (which tickets have `tickets/{KEY}/` folders)
5. Present summary: new, closed, moved, missing local folders
6. Update `tickets/TICKET_INDEX.md` with current state and priority ranking
7. Flag tickets >90 days without update as stale candidates

## Notes
- Should run monthly or when user feels overwhelmed
- Haiku subagent for the Jira fetch (I/O bound, no reasoning needed)
- Could also flag tickets referenced in AGENT_BRIEFING that aren't in open search
