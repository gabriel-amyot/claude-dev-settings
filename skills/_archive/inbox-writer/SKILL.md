---
name: inbox-writer
description: Write structured messages to the Mission Control inbox. Use when an agent needs to send a decision, approval, info, or critical message to the user's inbox or another agent's inbox. Triggers on "send to inbox", "write to inbox", "send to my inbox", "put this in my inbox", "notify the user", "queue for review", "send this for approval".
nav:
  bay: ops
  when: "Write structured messages to Mission Control inbox from agents."
  when_not: "External posts (use /post-comment). Jira comments (use /jira)."
---

# Inbox Writer

Writes properly structured JSON messages to the Mission Control v2 inbox system. Every message follows the inbox schema so it renders correctly in the Mission Control dashboard with type badges, priority indicators, selectable options, file links, and action dispatch.

**Never write freeform text or copy files to random folders.** Always use this skill to produce a well-formed inbox message.

---

## Step 0: Determine the inbox target

Messages can go to two places:

| Target | Path | When |
|--------|------|------|
| **User inbox** | `{org_root}/project-management/general/user/inbox/{category}/` | Default. User needs to see, decide, or approve something. |
| **Agent inbox** | `{org_root}/project-management/general/agent/{agent-name}/inbox/` | Async delegation to another agent. |

**Org roots:**
- Klever: `~/Developer/grp-beklever-com/project-management`
- Supervisr: `~/Developer/supervisr-ai/project-management`
- Personal: `~/Developer/gabriel-amyot/project-management`

Determine the org from `$PWD` (longest prefix match). If unsure, use Personal.

## Step 1: Choose the category

| Category | Folder | When to use |
|----------|--------|-------------|
| `decisions` | `general/user/inbox/decisions/` | User must choose between options. Always include `questions` with `type: "choice"` and `options`. |
| `approvals` | `general/user/inbox/approvals/` | User approves or rejects something (PR, spec, proposal). Questions should have Approve/Deny options. |
| `info` | `general/user/inbox/info/` | FYI, status update, reading material. No action required from user. |
| `critical` | `general/user/inbox/critical/` | Urgent blocker, incident, time-sensitive item that needs immediate attention. |

## Step 2: Write the message JSON

**Filename convention:** `{YYYY-MM-DD}-{ticket-or-slug}-{seq}.json`

Examples: `2026-04-22-ktp-510-spec-01.json`, `2026-04-22-homepage-review-01.json`

**Schema:**

```json
{
  "id": "2026-04-22-ktp-510-spec-01",
  "type": "decision",
  "priority": "high",
  "title": "Short descriptive title (under 80 chars)",
  "ticket": "KTP-510",
  "date": "2026-04-22",
  "author": "sprint-crawl",
  "estimate": "5 min",
  "status": "open",
  "body": "Markdown body with full context. Use tables, lists, bold. This renders in the dashboard.",
  "questions": [
    {
      "text": "What is your preferred approach?",
      "type": "choice",
      "options": ["Option A: description", "Option B: description", "Option C: description"]
    },
    {
      "text": "Any additional constraints?",
      "type": "text"
    }
  ],
  "files": [
    "tickets/KTP/KTP-510/reports/spec-interpretation.md"
  ],
  "prompt": {
    "description": "What happens after the user responds.",
    "target_agent": "sprint-crawl",
    "context_path": "tickets/KTP/KTP-510/",
    "instruction": "Detailed instruction for the agent that will execute the follow-up."
  }
}
```

## Field reference

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Must match filename (without .json). Unique. |
| `type` | yes | `decision`, `approval`, `info`, `critical` |
| `priority` | yes | `critical`, `high`, `medium`, `low` |
| `title` | yes | Under 80 chars. Shows in collapsed card. |
| `ticket` | no | Jira key (KTP-510, SPV-92). Empty string if none. |
| `date` | yes | ISO date: `2026-04-22` |
| `author` | yes | Your agent name (e.g., `sprint-crawl`, `dexter`). Use the agent name from your system prompt. |
| `estimate` | no | Time to handle: `"5 min"`, `"15 min"`. Empty string if unknown. |
| `status` | yes | Always `"open"` for new messages. |
| `body` | yes | Markdown. Rendered in dashboard. Include enough context for the user to act without opening other files. |
| `questions` | no | Array of question objects. Required for `decision` type. |
| `questions[].text` | yes | The question text. |
| `questions[].type` | yes | `"choice"` (radio buttons) or `"text"` (free input). |
| `questions[].options` | if choice | Array of option strings. User picks one. |
| `files` | no | Relative paths from org root. These become clickable previews in the dashboard. |
| `prompt` | no | Action dispatch config. What should happen after the user responds. |
| `prompt.description` | yes | Human-readable summary of the follow-up action. |
| `prompt.target_agent` | no | Which agent executes the follow-up. |
| `prompt.context_path` | no | Working directory for the follow-up agent. |
| `prompt.instruction` | no | Detailed instruction for the follow-up agent. |

## Step 3: Write the file

```bash
# Determine org root from $PWD
ORG_ROOT="$HOME/Developer/gabriel-amyot/project-management"  # adjust per org

# Write to the correct category
cat > "$ORG_ROOT/general/user/inbox/decisions/2026-04-22-my-message-01.json" << 'EOF'
{
  ... your JSON ...
}
EOF
```

Or use the Write tool to create the file directly.

## Step 4: Verify

After writing, confirm:
1. The file is valid JSON (no trailing commas, proper quoting)
2. The `id` matches the filename
3. File paths in `files[]` are relative to the org root and actually exist
4. Questions of type `"choice"` have at least 2 options

---

## Common patterns

### Spec review request (approval)
```json
{
  "type": "approval",
  "questions": [
    { "text": "Approve this spec for implementation?", "type": "choice", "options": ["Approve", "Deny — needs revision"] }
  ],
  "prompt": {
    "description": "Begin implementation from approved spec.",
    "target_agent": "sprint-crawl",
    "instruction": "Write implementation plan and start building."
  }
}
```

### Architecture decision (decision)
```json
{
  "type": "decision",
  "questions": [
    { "text": "Which approach?", "type": "choice", "options": ["Option A: ...", "Option B: ..."] },
    { "text": "Any constraints I should know about?", "type": "text" }
  ]
}
```

### Status report (info)
```json
{
  "type": "info",
  "questions": [],
  "prompt": null
}
```

### Blocker (critical)
```json
{
  "type": "critical",
  "priority": "critical",
  "questions": [
    { "text": "How to proceed?", "type": "choice", "options": ["Fix now", "Defer to next sprint", "Escalate to team lead"] }
  ]
}
```

---

## Anti-patterns

- **Never** copy files to `doc/intents/inbox/` or any made-up folder. Use the v2 inbox path.
- **Never** write to `GABRIEL_INBOX.md` directly. That's the legacy v1 format.
- **Never** write a message without `id`, `type`, `date`, and `status` fields.
- **Never** use `type: "text"` for questions that have finite options. Use `type: "choice"`.
- **Never** put absolute paths in `files[]`. Use paths relative to the org root.
