# Claude Code Setup Optimization Backlog

Last audited: 2026-03-16

## Current Setup Snapshot

| Category | Count | Notes |
|----------|-------|-------|
| Plugins | 9 | ralph-loop, claude-md-management, pr-review-toolkit, skill-creator, frontend-design, claude-code-setup, plugin-dev, slack, jdtls-lsp |
| Agents | 16 | Full BMAD + crawl + shipping pipeline |
| Skills | 35+ | Covers gcloud, gitlab, jira, slack, test-harness, ticket-init, and more |
| MCP Servers | 0 (active) | Slack MCP bundled via plugin but no standalone MCP servers |
| Hooks | 8 event types | peon-ping on all events, config-protect, spec-guard, claude-md-guard, pre-compact-guard |

## Backlog Items

### P1: Install context7 MCP

**Status:** Not started
**Effort:** 1 command
**Why:** Live documentation lookup for Spring Boot, GCP libraries, Retell API. Eliminates guessing at Java method signatures and reduces need to paste docs into context.

```bash
claude mcp add context7 -- npx -y @upstash/context7-mcp@latest
```

### P2: Bump effortLevel to "high"

**Status:** Not started
**Effort:** 1 line edit in `~/.claude/settings.json`
**Why:** Currently set to `"medium"`. Running Opus 4.6 with 1M context, medium reduces reasoning depth. "high" is better for orchestrator sessions (night crawls, BMAD parties). Use `/fast` for quick tasks.

Change `"effortLevel": "medium"` to `"effortLevel": "high"` in `~/.claude/settings.json`.

### P3: Convert PreToolUse CLAUDE.md Prompt to Conditional Command Hook

**Status:** Not started
**Effort:** Medium
**Why:** The current PreToolUse prompt hook fires on every Edit/Write call. It's a long prompt that costs tokens on every tool invocation, even when editing unrelated files. A command hook that checks the filename first (like `config-protect.sh` already does) and only blocks when the file matches `CLAUDE.md`, `settings.json`, or `agent-os/sbe/` would be more efficient.

**Approach:**
1. Write a bash script (e.g., `~/.claude/hooks/claude-md-precheck.sh`) that inspects `$CLAUDE_TOOL_INPUT` for target filenames
2. Return block/allow based on filename match
3. Only inject the full prompt guidance when actually editing a protected file
4. Remove the blanket prompt from the PreToolUse hook

### P4: Add Java Auto-Format PostToolUse Hook

**Status:** Not started
**Effort:** Small (requires `google-java-format` installed)
**Why:** Catches formatting issues before commits. Runs only on `.java` files.

**Prereq:** `brew install google-java-format`

```json
{
  "matcher": "Edit|Write",
  "hooks": [
    {
      "type": "command",
      "command": "FILE=$(echo $CLAUDE_TOOL_INPUT | jq -r '.file_path // empty'); if [[ \"$FILE\" == *.java ]]; then google-java-format --replace \"$FILE\" 2>/dev/null; fi",
      "timeout": 15
    }
  ]
}
```

### P5: Evaluate Jira MCP Server vs Custom /jira Skill

**Status:** Not started
**Effort:** Research
**Why:** Currently using a custom `/jira` skill for all Jira interactions. An MCP server would give native tool access without skill invocation overhead. Worth evaluating whether the official Jira MCP covers JQL needs, AC fetching, and comment posting that the custom skill handles.

**Decision criteria:**
- Does the MCP server support JQL search, issue detail fetch, comment posting?
- Does it handle custom fields (AC, story points)?
- Is the auth setup simpler or more complex than the current skill's approach?
- Would it replace the skill entirely or complement it?

## What NOT to Add (Anti-Backlog)

These were considered and explicitly rejected:

| Item | Reason |
|------|--------|
| More plugins | Already at 9. Plugin bloat increases startup time and prompt size. |
| More agents | 16 is comprehensive coverage. Adding more creates selection ambiguity. |
| GitHub MCP | Uses GitLab, not GitHub. Custom `/gitlab` skill handles it. |
| Memory MCP | Robust file-based memory system already in place. |
| Commit attribution | Empty `attribution` strings are intentional (no co-author tags wanted). |
