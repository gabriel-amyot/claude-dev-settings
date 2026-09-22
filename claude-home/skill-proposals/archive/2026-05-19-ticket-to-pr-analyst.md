# Skill Proposal: ticket-to-pr-analyst
Date: 2026-05-19
Source: Ticket-to-PR Pipeline product brief session

## Trigger
User invokes `/ticket-to-pr-analyst KTP-XXX` or similar. Eventually triggered automatically when a new ticket folder appears with status "To Do" and assigned to Gabriel.

## Scope
global (lives in `~/.claude/skills/`, usable from any org)

## Draft Steps
1. Accept ticket key as argument. Fetch ticket via `/jira` skill (title, description, AC if any, labels, epic context).
2. Assess spec quality: description length, identifiable code area/feature, inferable stakeholder intent. Classify as PASS or FAIL.
3. If FAIL: output structured reason, suggest posting a Jira comment requesting more info. Stop.
4. If PASS: Extract or infer acceptance criteria as numbered, testable items. Categorize each (ui, backend, fullstack, infra, data).
5. Identify affected repos from codebase context (read CLAUDE.md, scan for relevant code areas).
6. Document assumptions (what was unclear, what was assumed, reasoning, alternatives considered).
7. Write structured JSON outputs to the ticket folder: `analyst/acceptance_criteria.v1.json`, `analyst/affected_repos.v1.json`, `analyst/assumptions.v1.json`.
8. Optionally post assumptions to Jira as a comment for stakeholder review.

## Notes
- This is Stage 1 of a larger 5-stage pipeline. Future stages (Architect, Implementer, AC Reviewer, Code Quality) will be separate skills or agents.
- Must work with spikes (research tickets), not just implementable stories.
- Spec quality threshold is a heuristic that will evolve with real-world usage.
- Output schemas defined in `/Users/gabrielamyot/Downloads/ticket-to-pr-spec-v3.md` (JSON Schema Draft 2020-12).
