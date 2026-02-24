# Jira Agent Interaction Rules

These rules apply to all AI agent interactions with Jira, regardless of project or organization.

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

## Future Improvement: Dedicated Agent Account

When available, create a dedicated Jira account (e.g., `ai-agent@origin8cares.com`) so agent comments are visually distinct (different avatar and name). Until then, the `[automated]` header prefix handles traceability.
