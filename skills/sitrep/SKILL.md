---
name: sitrep
description: "Org-scoped situation report. Parallel-fetches inbox, active tickets, Jira, and memory to synthesize a CRITICAL/DECISIONS/IN-FLIGHT briefing. Triggers: 'big picture', 'sitrep', 'situation report', 'what is happening', 'where are we', 'status of everything'."
nav:
  bay: know
  when: "Org-scoped situation report. Parallel-fetches inbox, tickets, Jira, memory."
  when_not: "Daily recon (use /morning-primer). Session health (use /session-check)."
---

# Sitrep — Situation Report

Produces a tiered org briefing by parallel-fetching all context sources. Auto-scopes to the current org. Never crosses org boundaries.

**Usage:** `/sitrep [focus-area]`

## Step 1: Resolve Org

Determine the active org from the current working directory:
- `~/Developer/supervisr-ai/` → org = `supervisrai`, PM root = `~/Developer/supervisr-ai/project-management/`
- `~/Developer/grp-beklever-com/` → org = `klever`, PM root = `~/Developer/grp-beklever-com/project-management/`

If cwd does not match a known org, ask the user.

## Step 2: Parallel Fetch (all independent, run concurrently)

Launch these reads simultaneously:

### 2a. Inbox (critical + decisions)
```
Glob: {PM_ROOT}/general/user/inbox/critical/*.json
Glob: {PM_ROOT}/general/user/inbox/decisions/*.json
Glob: {PM_ROOT}/general/user/inbox/approvals/*.json
```
Read each JSON file. Filter for `"status": "open"` only. Extract: title, priority, ticket, estimate, questions.

### 2b. Active Tickets
```
Glob: {PM_ROOT}/tickets/**/STATUS_SNAPSHOT.yaml
```
Read each. Filter for `status: in_progress`. Extract: epic, completion, blockers, next_actions.

### 2c. Jira Active Tickets
```bash
python3 ~/.claude/skills/jira/jira_skill.py search --org {ORG} --jql "assignee = currentUser() AND status NOT IN (Done, Closed) ORDER BY priority DESC" --max-results 25
```

### 2d. Memory Context
Read MEMORY.md project entries for current context. Filter for entries less than 14 days old.

## Step 3: Synthesize into Three Tiers

### CRITICAL — Blocked on you, time-sensitive
- Inbox items with priority `high` or `critical` and status `open`
- Tickets with `critical_blockers` that require human action
- Anything with an estimate under 10 minutes (quick wins)

### DECISIONS — Queued, can answer in 5 minutes
- Inbox items of type `decision` with status `open`
- Open questions in STATUS_SNAPSHOT `open_decisions`

### IN-FLIGHT — Awareness only, no action needed
- Tickets in progress with no blockers
- Jira tickets in standard workflow states

## Step 4: Recommend Next Actions

After presenting the three tiers:
1. Identify what the user can do RIGHT NOW (shortest unblock time first)
2. Identify what agents can do IN PARALLEL while the user handles manual gates
3. Flag anything that's been open > 7 days without progress

## Output Format

```markdown
## SITREP — {Org Name} — {Date}

### CRITICAL (blocked on you)
{numbered list with ticket, action, estimate}

### DECISIONS (5 min reading)
{numbered list with ticket, question summary}

### IN-FLIGHT (awareness)
{table: ticket | status | note}

### RECOMMENDED NEXT
{what to do first, what to parallelize}
```

## Rules
- Never query other orgs. "The company" = current org.
- When dispatching Jira subagents, pass `--org {resolved_org}` explicitly.
- Keep the briefing under 100 lines. Link to detail files, don't inline them.
- If a focus area was specified, filter all tiers to that area.
