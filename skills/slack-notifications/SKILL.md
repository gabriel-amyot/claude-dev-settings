---
name: slack-notifications
description: Read pending Slack notifications, unread DMs, and mentions. Use when user asks about Slack notifications, unread messages, "what did I miss", or "check Slack".
allowed-tools: Bash(curl *), Bash(jq *), Bash(date *)
---

# Read Slack Notifications

Fetch unread DMs, mentions, and recent activity from Slack.

## Steps

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

## Output Format

Present results grouped by priority:
1. **Unread DMs** (name, preview, timestamp)
2. **Mentions** (channel, who mentioned you, context)
3. **Channels with unread** (channel name, unread count)

Use relative timestamps ("2 hours ago", "yesterday"). Keep it scannable.

## Important
- Use `$SLACK_BOT_TOKEN` for conversations/history APIs
- Use `$SLACK_USER_TOKEN` for search APIs (search.messages requires user token)
- Always resolve user IDs to real names before presenting
- Paginate if needed using `cursor` from response metadata
