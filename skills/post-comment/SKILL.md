---
name: post-comment
description: "Post externally visible content (PR comments, Jira comments, Slack messages, deploy notices) through a safe pipeline: draft on disk, template render, preview, explicit approval, audit log. Supports editing existing posts. Use when user wants to post a comment, reply to a PR, update Jira, or send any external message."
agent: post-comment
---

# /post-comment

Safe external posting pipeline. Enforces: draft on disk, template render, full preview, explicit approval, audit log. Supports new posts, edits, and batch posting.

## Usage

```
/post-comment                          # Agent asks what you want to post
/post-comment /tmp/my-draft.md         # Post from a specific draft file
/post-comment drafts/                  # Batch mode from a folder of drafts
/post-comment edit SPV-3               # List posts for SPV-3, pick one to edit
/post-comment edit https://github...   # Edit a specific comment by URL
```

## Supported Platforms

- **GitHub**: PR comments, review replies, PR descriptions
- **GitLab**: MR comments, review replies
- **Jira**: ticket comments, status updates
- **Slack**: thread replies, DMs

## Edit Flow

When editing an existing comment:
1. Agent reads the post log for the ticket
2. Lists recent posts with timestamp, platform, URL, and content hash
3. You pick which one to edit
4. Agent fetches the current content from the platform
5. You provide a replacement draft (or say "help me draft" to start from the original)
6. Same preview and approval flow as new posts
7. Agent patches the comment in place (or posts a correction for Slack)

## Persistence

Drafts and posted content are saved to `tickets/{TICKET}/reports/ship/posts/`:
- `{date}-{slug}.md` for drafts
- `{date}-{slug}.posted` for rendered content that was actually posted

## Templates

Templates live in `~/.claude-shared-config/skills/templates/`. See `README.md` there for the full list and draft file format.

## Learned Rules

- **Tag the reporter, not "team".** Jira comments should mention the ticket reporter (or a specific person), not a generic audience. Look up the reporter from the ticket context.
- **Never reference local ticket folders.** The `tickets/` tree is local-only (not in Jira). Do not mention "documented in the ticket folder" in external posts.
- **No aggressive deadlines.** Avoid "if I don't hear by EOD I'll proceed" framing. Instead, use warm proactive language: "I'm going to start implementing shortly. Let me know if you disagree or have a better approach."
- **Skip redundant headers.** If the comment purpose is obvious from context (e.g., a single comment on a ticket), do not add a formal header like "Implementation Assumptions (call for correction)".
- **Jira auth: use macOS Keychain, not env vars.** The jira skill stores tokens in keychain (`security find-generic-password -s claude-jira -a jira_{org}`). The `JIRA_API_TOKEN` env var is stale. Always retrieve the token from keychain via the same method the jira skill uses. Config is at `~/.claude-shared-config/skills/jira/jira_config.json`.

## Audit Log

Every post is logged to `tickets/{TICKET}/reports/ship/post-log.yaml` (or `global-post-log.yaml` if no ticket context). Each entry records: timestamp, platform, target, template, draft path, posted URL, content hash, action (new/edit/delete), and replaces_hash (for edits).
