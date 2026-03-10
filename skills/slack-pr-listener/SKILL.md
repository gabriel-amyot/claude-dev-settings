---
name: slack-pr-listener
description: Poll a Slack PR review channel for new pull request links, then automatically trigger local code review agents. Use when user says "watch PRs", "listen for PRs", "monitor PR channel", or "start PR listener".
argument-hint: [#channel-name]
disable-model-invocation: true
allowed-tools: Bash(curl *), Bash(jq *), Bash(gh *), Agent
---

# Slack PR Review Channel Listener

Poll a Slack channel for PR/MR links and automatically trigger code review agents.

## Arguments

- `$ARGUMENTS` — channel name (e.g., `#pr-reviews` or `pr-reviews`)

## Setup

1. **Resolve the channel ID:**
```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=200" | \
  jq -r '.channels[] | select(.name == "CHANNEL_NAME") | .id'
```

2. **Ensure the bot is in the channel.** If not:
```bash
curl -s -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "CHANNEL_ID"}' \
  "https://slack.com/api/conversations.join"
```

## Polling Loop

3. **Fetch recent messages** (last 30 minutes or since last check):
```bash
# Calculate timestamp for 30 min ago
OLDEST=$(date -v-30M +%s 2>/dev/null || date -d '30 minutes ago' +%s)

curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.history?channel=CHANNEL_ID&oldest=$OLDEST&limit=50" | jq .
```

4. **Extract PR/MR links** from messages. Look for patterns:
   - `github.com/ORG/REPO/pull/NUMBER`
   - `gitlab.com/ORG/REPO/-/merge_requests/NUMBER`
   - Raw PR URLs in Slack unfurls

5. **For each new PR found**, report it to the user and ask whether to review:
   - Show: repo, PR number, title, author
   - Ask: "Review this PR? (y/n/all)"
   - If "all", auto-review remaining without asking

6. **Trigger the review** using the pr-review-toolkit agent:
   - For GitHub PRs: use `gh pr view NUMBER --repo ORG/REPO` to get details
   - Then spawn the `pr-review-toolkit:code-reviewer` agent with the PR context

## Review Trigger

For each approved PR, launch a review agent:

```
Use the Agent tool with subagent_type "pr-review-toolkit:code-reviewer"
providing the PR URL, repo, and branch information.
```

Alternatively, if the `/pr-review` skill is preferred, invoke it with the PR URL.

## Output

After each review completes:
1. Post a summary back to the Slack channel (brief, with link to full review):
```bash
curl -s -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "CHANNEL_ID", "text": "Review complete for PR #NUMBER: SUMMARY", "thread_ts": "ORIGINAL_MSG_TS"}' \
  "https://slack.com/api/chat.postMessage"
```
2. Show the full review results locally in Claude Code

## Important
- This is a one-shot poll, not a persistent daemon. Run `/slack-pr-listener` periodically or when you want to check.
- Always confirm before posting review results back to Slack.
- Use `$SLACK_BOT_TOKEN` for all API calls in this skill.
