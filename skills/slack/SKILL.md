---
name: slack
description: "Interact with Slack workspace. Search messages, reply to DMs/threads, check unread notifications. Modes: /slack search [query], /slack reply [@person] [message], /slack unread. Supports Slack search syntax (from:, in:, after:, has:). Input: mode + arguments. Returns: messages, confirmation, or notification list."
user_invocable: true
allowed-tools: Bash(curl *), Bash(jq *), Bash(date *)
---

# Slack

Unified Slack interface. Supports three modes: `search`, `reply`, and `unread`.

## Usage

```
/slack search [query]
/slack reply [@person or #channel] [message]
/slack unread
```

Parse the first word of `$ARGUMENTS` to determine the mode.

---

## Mode: search

Search across the entire Slack workspace for messages matching keywords, people, channels, or ticket numbers.

### Steps

1. **Build the Slack search query.** Translate the user's intent into Slack search syntax:
   - Person: `from:@username` or `from:email`
   - Channel: `in:#channel-name`
   - Ticket: just use the ticket ID as a keyword (e.g., `SPV-3`)
   - Date range: `after:2026-01-01 before:2026-03-01`
   - Combine as needed: `from:@john SPV-3 in:#engineering`

2. **Execute the search** (requires user token):
```bash
curl -s -G -H "Authorization: Bearer $SLACK_USER_TOKEN" \
  --data-urlencode "query=SEARCH_QUERY" \
  --data-urlencode "sort=timestamp" \
  --data-urlencode "sort_dir=desc" \
  --data-urlencode "count=20" \
  "https://slack.com/api/search.messages" | jq .
```

3. **If searching for a person by name**, first resolve to username:
```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/users.list?limit=200" | jq -r '.members[] | select(.real_name | test("NAME"; "i")) | "\(.id) \(.name) \(.real_name)"'
```

4. **For file/document search**:
```bash
curl -s -G -H "Authorization: Bearer $SLACK_USER_TOKEN" \
  --data-urlencode "query=SEARCH_QUERY" \
  --data-urlencode "count=10" \
  "https://slack.com/api/search.files" | jq .
```

5. **Paginate** if more results needed (use `page=2`, `page=3`, etc.)

### Output Format

Present results as a scannable list:
- **Channel** | **Author** | **Date** | Message preview
- Group by channel or by date depending on what makes sense for the query
- Highlight the matching terms
- Show thread context if the match is a thread reply

### Tips
- Slack search syntax: `has:link`, `has:attachment`, `is:thread`, `before:`, `after:`, `during:today`
- For broad searches, start with 10 results, offer to expand
- The search API requires `$SLACK_USER_TOKEN` (user token with `search:read` scope), NOT the bot token

---

## Mode: reply

Send a reply to a DM or channel thread directly from Claude Code.

### Arguments

Free-form: can be "@person message", "#channel message", or a reply to a previously shown notification.

### Steps

1. **Determine the target.** If the user references a person shown in a previous `/slack unread` call, reuse that user ID and channel. Otherwise:

2. **Resolve user by name or email:**
```bash
# By name (search through users list)
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/users.list?limit=200" | jq -r '.members[] | select(.real_name | test("SEARCH_TERM"; "i")) | "\(.id) \(.real_name)"'

# By email
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/users.lookupByEmail?email=EMAIL" | jq .
```

3. **Open or find the DM channel:**
```bash
curl -s -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"users": "USER_ID"}' \
  "https://slack.com/api/conversations.open" | jq -r '.channel.id'
```

4. **Send the message:**
```bash
curl -s -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "CHANNEL_ID", "text": "MESSAGE_TEXT"}' \
  "https://slack.com/api/chat.postMessage" | jq .
```

5. **For thread replies**, include `thread_ts`:
```bash
curl -s -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "CHANNEL_ID", "text": "MESSAGE_TEXT", "thread_ts": "THREAD_TS"}' \
  "https://slack.com/api/chat.postMessage" | jq .
```

### Rules
- Always confirm the recipient and message with the user BEFORE sending
- Show a preview: "Send to **John Smith**: 'your message here'? (y/n)"
- If the message is ambiguous, ask for clarification
- Never send messages without explicit user approval
- The bot sends as itself (the app name), not as the user. Make this clear.

---

## Mode: unread

Fetch unread DMs, mentions, and recent activity from Slack.

### Steps

1. **List DM conversations** with unread messages:
```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.list?types=im&limit=100" | jq .
```

2. **For each DM with unread_count > 0**, fetch recent messages:
```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.history?channel=CHANNEL_ID&limit=10"
```

3. **Resolve user names** from user IDs:
```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/users.info?user=USER_ID" | jq -r '.user.real_name'
```

4. **Search for mentions** of the authenticated user in recent messages:
```bash
curl -s -H "Authorization: Bearer $SLACK_USER_TOKEN" \
  "https://slack.com/api/search.messages?query=to:me&sort=timestamp&count=20" | jq .
```

### Output Format

Present results grouped by priority:
1. **Unread DMs** (name, preview, timestamp)
2. **Mentions** (channel, who mentioned you, context)
3. **Channels with unread** (channel name, unread count)

Use relative timestamps ("2 hours ago", "yesterday"). Keep it scannable.

### Important
- Use `$SLACK_BOT_TOKEN` for conversations/history APIs
- Use `$SLACK_USER_TOKEN` for search APIs (search.messages requires user token)
- Always resolve user IDs to real names before presenting
- Paginate if needed using `cursor` from response metadata
