---
name: slack-reply
description: Reply to a Slack DM or thread from Claude Code. Use when user wants to answer a Slack message, respond to someone on Slack, or send a DM.
argument-hint: [@person or #channel] [message]
allowed-tools: Bash(curl *), Bash(jq *)
---

# Reply to Slack Messages

Send a reply to a DM or channel thread directly from Claude Code.

## Arguments

- `$ARGUMENTS` — free-form: can be "@person message", "#channel message", or a reply to a previously shown notification.

## Steps

1. **Determine the target.** If the user references a person shown in a previous `/slack-notifications` call, reuse that user ID and channel. Otherwise:

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

## Rules
- Always confirm the recipient and message with the user BEFORE sending
- Show a preview: "Send to **John Smith**: 'your message here'? (y/n)"
- If the message is ambiguous, ask for clarification
- Never send messages without explicit user approval
- The bot sends as itself (the app name), not as the user. Make this clear.
