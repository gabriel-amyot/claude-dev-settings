# Inbox v2: Folder-Based Message System

> Last updated: 2026-04-22

## Filesystem Structure

```
general/
  INDEX.md                    # Catalog explaining the messaging system
  user/
    inbox/
      decisions/              # Requires choosing between options
        {message-id}.json
      approvals/              # Approve/reject a proposal or PR
        {message-id}.json
      info/                   # FYI items, readings, status updates
        {message-id}.json
      critical/               # Urgent items, blockers, incidents
        {message-id}.json
  agent/
    {agent-name}/
      inbox/
        {message-id}.json     # Messages queued for a specific agent
```

## Message ID Convention

`{date}-{ticket-or-slug}-{seq}.json`

Examples:
- `2026-04-22-ktp-510-spec-interpretation-01.json`
- `2026-04-21-dooh-audit-01.json`
- `2026-04-19-ktp-521-mr-action-01.json`

## Message JSON Schema

```json
{
  "id": "2026-04-22-ktp-510-spec-01",
  "type": "decision",
  "priority": "high",
  "title": "KTP-510 Spec Interpretation",
  "ticket": "KTP-510",
  "date": "2026-04-22",
  "author": "sprint-crawl",
  "estimate": "5 min",
  "status": "open",
  "body": "Read the ticket and answer three questions about filter UI approach.",
  "questions": [
    "Which filter UI approach: dropdown or sidebar?",
    "If no results, show empty state or redirect?",
    "Which BigQuery table is the source?"
  ],
  "files": [
    "tickets/KTP-510/reports/spec-interpretation.md"
  ],
  "prompt": {
    "description": "Once answered, formalize the decisions into the spec and run adversarial review.",
    "target_agent": "sprint-crawl",
    "context_path": "tickets/KTP-510/",
    "instruction": "Apply the user's answers to the spec at tickets/KTP-510/reports/spec-interpretation.md. Run a full adversarial review on the updated spec."
  }
}
```

## Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique message identifier, matches filename without .json |
| `type` | enum | yes | `decision`, `approval`, `info`, `critical` |
| `priority` | enum | yes | `critical`, `high`, `medium`, `low` |
| `title` | string | yes | Short descriptive title |
| `ticket` | string | no | Jira ticket key (KTP-510, SPV-92, etc.) |
| `date` | string | yes | ISO date when message was created |
| `author` | string | no | Who created this message (agent name or "user") |
| `estimate` | string | no | Time estimate to handle ("5 min", "15 min") |
| `status` | enum | yes | `open`, `resolved`, `stale` |
| `body` | string | yes | Markdown body with full context |
| `questions` | array | no | List of questions requiring answers |
| `files` | array | no | Relative paths to attached files |
| `prompt` | object | no | Action prompt: what happens after user responds |
| `prompt.description` | string | no | Human-readable description of the action |
| `prompt.target_agent` | string | no | Which agent should execute the follow-up |
| `prompt.context_path` | string | no | Working directory context for the agent |
| `prompt.instruction` | string | no | Detailed instruction for the agent |

## Type Definitions

| Type | Color | When to Use |
|------|-------|-------------|
| `decision` | Red | User must choose between options. Has questions. |
| `approval` | Blue | Approve/reject a proposal, PR, or spec. Binary. |
| `info` | Gray | Reading material, status updates, FYI. No action needed. |
| `critical` | Orange/Amber | Urgent blockers, incidents, time-sensitive items. |

## Staleness

Messages older than 3 days are considered stale. The UI shows staleness indicators:
- Green: today or yesterday
- Amber: 2-3 days old
- Red: 4+ days old

## Agent Inboxes

Any agent defined in `~/.claude/agents/` can have an inbox at `general/agent/{agent-name}/inbox/`. Messages use the same JSON schema. The `author` field indicates who queued the message (could be user or another agent).

## Backward Compatibility

If `general/user/inbox/` doesn't exist, the backend falls back to reading `general/GABRIEL_INBOX.md` and parsing it with the v1 markdown parser.
