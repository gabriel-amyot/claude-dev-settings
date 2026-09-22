# Skill Proposal: claude-code-cost-optimization
Date: 2026-04-17
Source: Cost optimization session — reviewing Claude Code changelog + applying settings

## Trigger
User asks to reduce Claude Code costs, optimize their setup, or mentions spending too much on API calls.

## Scope
Global (`~/.claude/`)

## Usefulness
High. Repeatable across any new machine or fresh Claude Code setup. Settings are non-obvious and scattered across changelogs.

## Create vs Update
Create new skill.

## Draft Steps
1. Read `~/.claude/settings.json` to check current state
2. Apply env vars: `ENABLE_PROMPT_CACHING_1H=true`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`
3. Apply settings: `autoCompactWindow: 300000`, `showThinkingSummaries: false`, `cleanupPeriodDays: 365`
4. Confirm `respectGitignore: true` (prevents cache busting from build artifacts)
5. Report what was changed vs already set. Suggest `/cost` habit post-session.

## Reference
`~/.claude/library/context/harness-self-management.md` — full cost context and future ideas (Batch API, auto monitoring).
