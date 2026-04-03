---
name: ralph-loop-preflight
description: "Validate prerequisites and configure parameters before launching a ralph-loop. Checks that the target agent exists, state file is well-formed, completion promise is reachable, verification gates are defined, specs/scenarios exist, and scope is clean. Outputs a validated invocation command."
---

# /ralph-loop-preflight

Validates everything is in place before launching a ralph-loop. Catches missing state files, unreachable completion promises, absent test scenarios, and dirty repos before you waste iterations.

## Usage

```
/ralph-loop-preflight <agent-name> <ticket-id> [--dry-run]
```

**Examples:**
```
/ralph-loop-preflight dev-crawl SPV-85
/ralph-loop-preflight night-crawl SPV-3
/ralph-loop-preflight dev-crawl SPV-85 --dry-run
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `agent-name` | Yes | Name of the agent to run inside the loop (must exist in `~/.claude/agents/`) |
| `ticket-id` | Yes | Ticket context for the crawl (e.g., SPV-85, SPV-3) |
| `--dry-run` | No | Run all checks but don't generate the invocation command |

---

## Universal Pre-Flight Delegation

Before running ralph-loop-specific checks, run `/pre-flight` with the crawl profile if one exists:
- If the agent has a matching crawl profile at `~/.claude/crawl-profiles/{agent-name}.yaml`, run `/pre-flight --profile {agent-name}`
- If no profile exists, run `/pre-flight` with defaults
- Universal pre-flight covers: repo cleanliness, Docker health, credentials, disk space, network reachability, agent definitions
- If universal pre-flight returns FATAL, stop. Do NOT proceed to ralph-loop-specific checks.

## Ralph-Loop-Specific Checklist

After universal pre-flight passes, run these additional checks. Collect all findings before presenting results. Do NOT stop at the first failure.

### Check 1: Agent Exists

Read `~/.claude/agents/{agent-name}.md`.

- **PASS**: File exists and has valid YAML frontmatter with `name`, `description`, `tools`, `model` fields
- **FAIL**: File missing or frontmatter incomplete

### Check 2: Ticket Context

Locate the ticket folder. Try these paths in order:
1. `tickets/{ticket-id}/` (direct)
2. Search for `tickets/**/{ticket-id}/` (nested under epic)

Within the ticket folder, check for:

| File | Required | Purpose |
|------|----------|---------|
| `README.md` | Yes | Ticket context |
| `jira/ac.yaml` | Yes | Acceptance criteria (the "what are we verifying" definition) |
| `REPO_MAPPING.yaml` | No (check parent) | Service-to-repo mapping |
| `STATUS_SNAPSHOT.yaml` | No (check parent) | Current state |

- **PASS**: README.md and ac.yaml exist
- **WARN**: Missing REPO_MAPPING or STATUS_SNAPSHOT (check parent ticket folder)
- **FAIL**: No README.md or no ac.yaml

### Check 3: State File

Look for the agent's state file. Convention: `{ticket-folder}/reports/status/{agent-name}-state.yaml`

**If exists:** Validate structure:
- Must be valid YAML
- Must have `iteration`, `last_updated`, `phase` fields
- Must have at least one of: `services`, `verification`, `blockers`
- Check `last_updated` timestamp. If older than 48h, warn (stale state).

**If missing:** OK for first run. Note that Phase 0 of the agent will create it.

- **PASS**: State file exists and is well-formed, or doesn't exist (first run)
- **WARN**: State file exists but is stale (>48h old)
- **FAIL**: State file exists but is malformed YAML or missing required fields

### Check 4: Verification Gates

The loop needs at least one way to verify progress. Scan the ticket folder for:

| Gate Type | File Pattern | What It Means |
|-----------|-------------|---------------|
| Test script | `*test-script*`, `*test-plan*` | Manual/automated verification steps |
| Test harness | `tools/test-harness/scripts/test-*.sh` | Local harness scripts |
| AC definitions | `jira/ac.yaml` | Acceptance criteria with pass/fail conditions |
| Health checks | URLs in REPO_MAPPING or state file | Service endpoint verification |

- **PASS**: At least one verification gate found
- **WARN**: Only AC definitions (no executable test scripts)
- **FAIL**: No verification gates at all

### Check 5: Completion Promise

Analyze the agent definition to determine the natural completion condition. Then propose a completion promise.

**Heuristics:**
- If agent has explicit "Completion Criteria" section, extract the primary condition
- If verification gates exist, completion = "all non-escalated gates pass"
- If AC exists, completion = "all AC pass or are escalated"

Proposed promise must be:
- **Verifiable**: The agent can objectively determine truth (not "things look good")
- **Specific**: References concrete state (not "all done")
- **Conservative**: Err on the side of continuing rather than stopping

**Good promises:** `ALL_SERVICES_HEALTHY`, `QA1_STEPS_1_THROUGH_4_PASS`, `DEV_CRAWL_COMPLETE`
**Bad promises:** `DONE`, `LOOKS_GOOD`, `FINISHED`

- **PASS**: A sound completion promise can be derived or was provided
- **WARN**: Promise is vague. Suggest a more specific alternative.

### Check 6: Scope & Repo State

For each repo referenced in REPO_MAPPING (or agent definition):

1. Check if the repo path exists on disk
2. `git status` for uncommitted changes
3. `git branch` for current branch
4. If on a feature branch, warn (should typically start from main/dev)

- **PASS**: All repos exist, clean working tree, on primary branch
- **WARN**: Uncommitted changes or on feature branch
- **FAIL**: Repo path doesn't exist

### Check 7: Iteration Budget

Propose a max-iterations value based on scope:

| Scope | Suggested Budget |
|-------|-----------------|
| Single blocker fix | 5-10 |
| Multiple blockers, same service | 10-15 |
| Multiple services, infrastructure work | 15-25 |
| Open-ended exploration | 25-50 |

Count blockers/ACs from state file and ac.yaml. Each blocker typically needs 2-3 iterations (diagnose + fix + verify).

Formula: `(open_blockers * 3) + (pending_ACs * 2) + 5 (buffer)`

- **PASS**: Budget is reasonable for scope
- **WARN**: Budget seems too low or too high for the work

---

## Output

### Preflight Report

Present results as a table:

```
Ralph Loop Preflight Report
Agent: {agent-name}
Ticket: {ticket-id}
Date: {YYYY-MM-DD}

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Agent exists | PASS/FAIL | ... |
| 2 | Ticket context | PASS/WARN/FAIL | ... |
| 3 | State file | PASS/WARN/FAIL | ... |
| 4 | Verification gates | PASS/WARN/FAIL | ... |
| 5 | Completion promise | PASS/WARN | ... |
| 6 | Scope & repo state | PASS/WARN/FAIL | ... |
| 7 | Iteration budget | PASS/WARN | ... |

Overall: READY / READY WITH WARNINGS / NOT READY
```

### Decision Gate

**If any FAIL:** Stop. Show what needs to be fixed. Do NOT generate an invocation command.

**If WARN only:** Show warnings. Ask user: "Proceed with warnings, or fix first?"

**If all PASS:** Proceed to generate invocation command.

### Invocation Command

Generate the validated ralph-loop command:

```bash
/ralph-loop "{agent-name} {ticket-id}" --completion-promise "{promise}" --max-iterations {budget}
```

Also generate a monitoring one-liner:

```bash
# Monitor progress:
grep -E '^(iteration|phase|last_updated):' {state-file-path}
```

### Save Preflight Report

Write the report to `{ticket-folder}/reports/status/ralph-loop-preflight-{date}.md` and update the nearest INDEX.md.

---

## Edge Cases

- **No agent-name provided:** List available agents in `~/.claude/agents/` and ask user to pick.
- **No ticket-id provided:** Check if `$PWD` is inside a ticket folder. If so, infer. Otherwise ask.
- **Agent has no state file convention:** Warn that state persistence depends on the agent's internal design. Ralph-loop only provides iteration count via `.claude/ralph-loop.local.md`.
- **Multiple REPO_MAPPING files:** Use the one closest to the ticket (child before parent).
- **`--dry-run` flag:** Run all checks, show the report, but do NOT generate the invocation command.
