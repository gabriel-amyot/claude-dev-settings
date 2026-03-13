# Jira Agent Interaction Rules

These rules apply to all AI agent interactions with Jira, regardless of project or organization.

---

## Rule 0: HUMAN GATE on All Public Writes

**STOP. Before executing ANY write operation (create ticket, update description, add comment, transition), you MUST:**

1. Show the user exactly what you intend to write (full text, not a summary)
2. Get explicit confirmation in the SAME conversation turn ("go ahead", "post it", "yes")
3. Only then execute

This applies even if a plan was previously approved. Plans go stale. Gab's reputation is on every Jira comment and every PR reply. Draft locally first, show it, get the green light.

**Write operations that require this gate:**
- `create` (new tickets)
- `update --description` (ticket descriptions)
- `add-comment` (Jira comments)
- `transition` to Done/Closed (also covered by Rule 1)

**Read operations that do NOT require this gate:** `list`, `get`, `description`, `metadata`, `search`, `subtasks`, `epic`, `comments`, `attachments`, `fetch`

---

## Rule 1: Never Close Tickets Without Human Confirmation

Agent CAN transition tickets to:
- In Progress
- In Review
- Ready to Deploy

Agent CANNOT transition tickets to:
- Done
- Closed

Done/Closed requires explicit human confirmation via:
- A Jira comment from a human confirming acceptance criteria are validated
- A direct instruction in the Claude Code session (e.g., "close SPV-8, ACs are validated")

---

## Rule 2: Comment Tone - Honest, Not Overconfident

- Say "code implementation complete" not "integration complete"
- Say "deployed to dev" not "deployed and working"
- Say "service starts successfully" not "all tests passing" (unless tests were actually run)
- Always mention what has NOT been validated
- No emojis in Jira comments

---

## Rule 3: Agent Comment Attribution Format

Every comment written by the agent must start with:

```
[automated] <tool> | <model> | session: <session-id>
---
```

Where:
- `<tool>`: `claude-code` (the CLI tool name)
- `<model>`: the model ID (e.g., `sonnet-4-5`, `opus-4-6`)
- `<session-id>`: unique session identifier from the transcript path or plan file name

This header serves three purposes:
1. **Human vs agent**: Any comment starting with `[automated]` is agent-written
2. **Traceability**: Session ID lets you find the exact conversation that generated it
3. **Model rating**: Model name lets you evaluate which model performed better

---

## Rule 4: Comment Structure

Comments should be multi-line and scannable:

- Line 1: Agent attribution header
- Line 2: `---` separator
- Line 3: One-sentence summary of what happened
- Blank line
- Body: Details broken into logical groups
- Blank line
- Footer: What is pending, what needs human action

---

## Rule 5: No Emojis

Jira comments written by agents must not contain emojis. Use plain text formatting only.

---

## Rule 6: AC Quality Gate on Ticket Creation

Before executing any `create` command:

1. **Load `~/.claude/context/ticket-quality-standards.md`** for reference
2. **Check for AC section.** If the description has no acceptance criteria, warn the user and ask them to define AC before creating. Do not silently create AC-less tickets.
3. **Apply the litmus test to each AC:** Does it describe WHAT the result looks like (spec-based) or HOW to do it (task-based)? Flag task-list ACs with a suggested rewrite using the anti-patterns table from the standards doc.
4. **Check minimum bar:** At least 2 testable ACs per ticket. Warn if fewer.
5. **Advisory gate, not blocking.** User can override with explicit "create it anyway." Respect their decision without re-asking.

This gate does not apply to spike tickets (where AC define questions to answer, not outcomes).

---

## Future Improvement: Dedicated Agent Account

When available, create a dedicated Jira account (e.g., `ai-agent@origin8cares.com`) so agent comments are visually distinct (different avatar and name). Until then, the `[automated]` header prefix handles traceability.
