---
name: claude-code-cost-optimization
description: "Apply cost-saving Claude Code settings to reduce API spend. Checks env vars, settings.json, and shell profile for optimization opportunities. Trigger: 'reduce costs', 'optimize Claude Code', 'too expensive', 'cost settings'. Global scope. Input: none. Returns: report of applied vs already-set optimizations."
nav:
  bay: ops
  when: "Reduce Claude Code API spend. Checks env vars, settings, shell profile."
  when_not: "General harness audit (use /harness-audit)."
---

# Claude Code Cost Optimization

Applies known cost-saving settings to reduce Claude Code API spend.

## Steps

### 1. Audit Current State

Read `~/.claude/settings.json` to check current configuration.
Check shell profile (`~/.zshrc` or `~/.bashrc`) for env vars.

### 2. Environment Variables

These should be in the user's shell profile. Check if present, instruct to add if missing:

| Var | Value | Effect |
|-----|-------|--------|
| `ENABLE_PROMPT_CACHING_1H` | `true` | Extends cache TTL from 5min to 1hr. Major savings for long sessions. |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `1` | Disables telemetry and non-essential API calls. |

If missing, instruct user to add to `~/.zshrc`:
```bash
export ENABLE_PROMPT_CACHING_1H=true
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

### 3. Settings.json Optimizations

Check and apply via Edit tool on `~/.claude/settings.json`:

| Setting | Recommended | Why |
|---------|-------------|-----|
| `autoCompactWindow` | `300000` | Compact at 300k tokens instead of waiting longer |
| `showThinkingSummaries` | `false` | Saves output tokens on thinking display |
| `cleanupPeriodDays` | `365` | Keep transcripts for knowledge mining |
| `respectGitignore` | `true` | Prevents cache busting from build artifacts |

### 4. Report

Print a table:

```
| Setting | Previous | New | Savings Estimate |
|---------|----------|-----|------------------|
| ENABLE_PROMPT_CACHING_1H | not set | true | ~30% on cache hits |
| autoCompactWindow | default | 300000 | reduces reprocessing |
```

### 5. Habits

Suggest: run `/cost` after sessions to track spend over time.

## Notes

- Never overwrite the entire settings.json. Use Edit tool for targeted changes.
- Prompt caching 1h is the single highest-impact optimization.
- The Batch API wrapper (separate skill proposal) could save 50% on overnight crawls but is not yet built.
