---
name: agent-debate-review
description: Post PR comments with BMAD persona attribution, then spawn an adversarial agent to counter-check claims and post replies. Creates a visible debate on the PR for the author to read. Use when the user wants to surface findings on a PR with built-in self-correction.
user_invocable: true
---

# Agent Debate Review

Post technical findings on a PR as inline comments with BMAD persona attribution, then adversarially challenge each claim and post counter-arguments as replies. The result is a visible debate the PR author can read with full context.

**Usage:** `/agent-debate-review <PR_URL> [hint]`

**Examples:**
```
/agent-debate-review https://github.com/org/repo/pull/30
/agent-debate-review https://github.com/org/repo/pull/30 "focus on the mvSync feature"
```

## Workflow

### Step 1: Research

1. Fetch the PR diff using `gh api`
2. Read the actual source files in the repo (not just the diff)
3. **Check for follow-up PRs by the same author.** Before claiming something is broken, verify the current state on `main`. Use `gh pr list --author` and `git log` to find subsequent fixes.
4. Identify issues worth commenting on

### Step 2: Draft Comments

For each finding, create a draft file at `tickets/drafts/posts/`:

**Persona assignment:**
| Issue Type | Persona |
|---|---|
| Architecture, dependencies, system design | **Winston (Architect)** |
| Data pipelines, idempotency, event handling, MV writes | **Atlas (Data Engineer)** |
| Code quality, implementation patterns | **Amelia (Developer)** |
| Test coverage, validation gaps | **Quinn (QA Engineer)** |

Each comment MUST:
- Start with `**{Persona} ({Role}):**`
- Address the PR author by first name
- Include the actual error message or code snippet (never paraphrase)
- Explain the mechanism precisely (see "Verify Error Mechanisms" rule below)
- State observations factually, not prescriptively. Let the author solve it.

### Step 3: Adversarial Counter-Check

Spawn an Opus subagent with this prompt:
- "You are an adversarial reviewer. Verify every claim in these draft comments against the actual source code."
- The agent MUST read the actual files on the current `main` branch
- The agent MUST check for follow-up PRs that may have already fixed issues
- For each claim, verdict: CONFIRMED, PARTIALLY CORRECT, or WRONG
- Include specific evidence (file paths, line numbers, code snippets)

### Step 4: Post

1. Post the original comments as inline PR review comments (use `gh api` with PR reviews endpoint)
2. Get the comment IDs from the response
3. Post adversarial replies using `in_reply_to` on each comment
4. Log everything to `tickets/drafts/posts/post-log.yaml`

### Step 5: Slack Summary (Optional)

If the user wants to notify the author, draft a casual Slack message with:
- What agents were involved and their personas
- Links to each comment thread
- What's still open vs what was self-corrected
- Let the user copy-paste it (don't auto-send)

## Critical Rules

### Verify Error Mechanisms (Learned from ERF PR #30)
Always quote the actual error message and diagnose from that. Never attribute a theoretical root cause without verifying the mechanism. Example of what NOT to do: claiming "ClassCastException from two classloaders" when the actual error is a Java module access restriction and Spring Boot uses a single classloader.

### Check Follow-Up PRs (Learned from ERF PR #30)
Before posting blame on a merged PR, always check subsequent PRs by the same author. The issue may have been self-corrected. Posting without acknowledging the fix is misleading and unfair.

### Don't Fabricate Evidence
Never claim "confirmed via bytecode analysis" or similar unless you actually performed that analysis in the current review. Cross-session findings must be attributed as such.

## GitHub API Notes

For inline comments on merged PRs, use the PR reviews endpoint:
```
gh api repos/{owner}/{repo}/pulls/{number}/reviews \
  --input payload.json
```

Payload format:
```json
{
  "event": "COMMENT",
  "body": "Review summary",
  "comments": [
    {
      "path": "src/main/java/...",
      "line": 35,
      "side": "RIGHT",
      "body": "**Winston (Architect):**\n\n..."
    }
  ]
}
```

For replies to existing comments:
```
gh api repos/{owner}/{repo}/pulls/{number}/comments \
  -f body="reply text" \
  -F in_reply_to={comment_id}
```
