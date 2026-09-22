# Skill Proposal: 3Ps Adversarial Gate
Date: 2026-05-05
Source: 3Ps generation session where KTP-606 was falsely claimed as complete

## Trigger
Built into klever-3ps skill, between Phase 1 (gather data) and Phase 2 (present context). Not a standalone skill.

## Scope
org (Klever, embedded in klever-3ps)

## Draft Steps
1. For each ticket a subagent claims as "complete" or "done," query Jira for: status, assignee, comment count
2. Reject claims where: Jira status is TO DO or In Progress, assignee is not Gabriel, zero evidence comments exist
3. Downgrade rejected claims from Progress to Plans (or drop entirely)
4. Flag inflated counts (e.g., "6 follow-on tickets" when Jira shows 9)
5. Present corrected claims to Gabriel with a diff showing what was changed and why
