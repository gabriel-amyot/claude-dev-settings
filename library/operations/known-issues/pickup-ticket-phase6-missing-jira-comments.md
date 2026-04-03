# pickup-ticket Agent — Phase 6 Gap

## Issue

Phase 6 (Spec Clarity Gate) in `~/.claude/agents/pickup-ticket.md` does not instruct agents to check the `jira/comments/` folder before flagging blocking questions as NEEDS_CLARIFICATION.

## Impact

When a ticket has existing comments that answer blocking questions (e.g., product owner responding to spec gaps), the agent ignores them and still marks the ticket as needing clarification.

**Example:** KTP-182 — Marc-André commented on 2026-03-10 at 21:21 answering all three spec gaps, but the pickup-ticket agent that ran later still flagged NEEDS_CLARIFICATION because it didn't read the comments folder.

## Root Cause

The Jira skill's `fetch` command correctly downloads comments to `jira/comments/`, and the comments are on disk. But pickup-ticket Phase 6 says to analyze the description and AC only — it doesn't instruct the agent to read existing comments first.

## Fix

Add this section to `~/.claude/agents/pickup-ticket.md` right before "### Gate Output" in Phase 6:

```markdown
### Pre-Gate: Read Existing Comments

Before writing any blocking questions, check `jira/comments/` in the ticket folder:
1. If `jira/comments/index.yaml` exists, read each comment file.
2. For each potential blocking question, check if a comment already answers it.
3. If a comment (especially from the author or a senior team member) answers the question, mark it RESOLVED, cite the comment, and do NOT list it as blocking.

**Rule:** Never flag a question as NEEDS_CLARIFICATION if the answer already exists in the ticket comments.
```

## Status

**Pending approval** — Awaiting user confirmation to edit the agent file (2026-03-13).
