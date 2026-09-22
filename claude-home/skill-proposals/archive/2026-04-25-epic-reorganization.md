# Skill Proposal: Epic Reorganization
Date: 2026-04-25
Source: KTP-115 epic split — created KTP-558/KTP-559, moved 18 tickets, updated links and local folders
Usefulness: Any time a large epic needs to be split or tickets re-bucketed (sprint planning, scope management). Comes up every 1-2 sprints. Currently fully ad-hoc with high error rate (forgot KTP-130, missed INDEX.md generation, sprint placement bug on ticket creation).
Create vs Update: Create new skill

## Trigger
User says "split this epic", "create a sub-epic for X", "reorganize tickets under a new epic", or "move these tickets to a new epic".

## Scope
org (Klever — uses KTP project conventions)

## Draft Steps
1. **Identify split** — JQL `parentEpic = KTP-XXX` to get current children. Classify into groups (active, refinements, phase 2, done). Surface to user for confirmation.
2. **Create new epics** — `jira_skill.py create --type Epic` for each new grouping. Set description and assignee.
3. **Batch re-parent** — parallel `editJiraIssue` with `{"customfield_10014": "KTP-NEW"}` for each group. Sprint assignment is unaffected.
4. **Add split links** — `createIssueLink` with type "Work item split", `inwardIssue = original`, `outwardIssue = new` for each new epic.
5. **Local folder moves** — Haiku subagent: create new `tickets/KTP/KTP-NEW/` folders, move sub-ticket folders from old epic, leave done/historical tickets in original.
6. **Update product map** — refresh `documentation/architecture/maps-product-map.md` with new epics, edges, and folder tree.
7. **Re-fetch epics** — `jira_skill.py fetch KTP-NEW --depth 1` for each new epic to generate INDEX.md.
