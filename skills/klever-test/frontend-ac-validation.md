# Frontend: AC Validation

Per-ticket acceptance criteria validation via browser automation with screenshot evidence.

## Input

- **Ticket key** (required): e.g., KTP-130
- **Environment** (optional): `local` (default) or `dev`
- **AC filter** (optional): `--ac AC-1` to validate a single AC

## Tool: Agent Browser CLI

```bash
# Open page (headless by default, --headed for visible browser)
agent-browser open <url>

# Text snapshot (cheap, use for navigation and reading)
agent-browser snapshot -i

# Screenshot (expensive, use only for evidence)
agent-browser screenshot <path>

# Click element by text/role
agent-browser click "Button text"

# Type into focused element
agent-browser type "text to type"

# Execute JavaScript in page context
agent-browser eval "window.mapStore.getState().selectedLocationId"

# Wait for network idle
agent-browser wait --load networkidle

# Close browser
agent-browser close
```

### Session Persistence (Dev Environment with IAP)

```bash
# First time: user authenticates in headed mode
agent-browser --session-name klever-dev --headed open https://portal.dev.beklever.com
# User logs in via IAP...

# Subsequent commands reuse the authenticated session
agent-browser --session-name klever-dev snapshot -i
agent-browser --session-name klever-dev screenshot evidence.png
```

## Flow

1. **Parse input** — extract ticket key, resolve prefix, determine environment
2. **Load AC** — read `tickets/{PREFIX}/{TICKET-ID}/jira/ac.yaml` or fetch via `/jira`
3. **Preflight** — run checks from parent SKILL.md
4. **For each AC:**
   - Navigate to relevant page
   - Wait for load: `agent-browser wait --load networkidle`
   - Read state via `agent-browser snapshot -i` (cheap)
   - Interact as needed
   - Screenshot for evidence (only when needed)
   - Evaluate PASS/FAIL
5. **Write report** to `tickets/{PREFIX}/{TICKET-ID}/reports/reviews/ac-validation-{date}.md`
6. **Update ac.yaml** verification status
7. **Optional Jira post** via `/post-comment` (never automatic)

## Report Format

```markdown
# AC Validation Report: {TICKET-KEY}
**Date:** {date}
**Environment:** {local|dev}

## Summary
- **Total ACs:** N | **PASS:** N | **FAIL:** N | **SKIP:** N

## Results

### AC-1: {title}
**Status:** PASS | FAIL | SKIP
**Evidence:** [screenshot](../../../design/screenshots/{filename})
**Notes:** {what was observed}
```

Screenshots go to: `tickets/{PREFIX}/{TICKET-ID}/design/screenshots/`
