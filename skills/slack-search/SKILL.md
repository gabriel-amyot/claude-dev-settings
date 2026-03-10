---
name: slack-search
description: Search Slack workspace for messages by keywords, themes, people, ticket numbers, or topics. Use when user wants to find something in Slack, search conversations, look up a ticket reference, or find what someone said.
argument-hint: [search query]
allowed-tools: Bash(curl *), Bash(jq *)
---

# Search Slack

Search across the entire Slack workspace for messages matching keywords, people, channels, or ticket numbers.

## Arguments

- `$ARGUMENTS` — the search query (keywords, person name, ticket ID, topic, etc.)

## Steps

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

## Output Format

Present results as a scannable list:
- **Channel** | **Author** | **Date** | Message preview
- Group by channel or by date depending on what makes sense for the query
- Highlight the matching terms
- Show thread context if the match is a thread reply

## Tips
- Slack search syntax: `has:link`, `has:attachment`, `is:thread`, `before:`, `after:`, `during:today`
- For broad searches, start with 10 results, offer to expand
- The search API requires `$SLACK_USER_TOKEN` (user token with `search:read` scope), NOT the bot token
