# Claude Code Tool Misuse Analysis
## Session History: 2026-03-27 to 2026-04-03 (Last 7 Days)

---

## Executive Summary

Analysis of 662 history records across 150+ sessions reveals **moderate tool misuse patterns** but overall **healthy routing discipline**. Top misuses involve:

1. **Unnecessary skill/command invocations** - 41 /buddy uses, 40 /model uses, 29 /btw uses are predominantly context-switching tools (non-productive overhead)
2. **Retry patterns without root cause diagnosis** - 24 retries detected with only 5 explicitly attributed to "wrong tool used"
3. **Weak error handling** - 18 records mention errors/failures but only 15 sessions show evidence of investigation
4. **Under-utilization of specific tools** - Git operations barely logged despite active development (likely implicit in Bash calls)

---

## A) MOST COMMON MISUSE PATTERNS

### 1. Command Overhead (Non-Productive Tool Usage)
**Pattern:** Heavy use of context/meta commands instead of doing work

| Command | Uses | Category | Assessment |
|---------|------|----------|-----------|
| `/buddy` | 41 | Context-switching | Unnecessary; should be consolidated |
| `/model` | 40 | Model selection | Excessive switching; pick model and stick |
| `/btw` | 29 | Sidebar/admin | Overhead command |
| `/login` | 24 | Auth refresh | Should auto-handle or batch |
| `/rate-limit-options` | 18 | Token monitoring | Excessive checking; set once |
| `/usage` | 8 | Token status | Redundant with rate-limit-options |

**Issue:** These 160 invocations (73% of all commands) do not advance work. They are meta-operations that should be automated or batched.

**Recommendation:** 
- Configure auto-login via settings.json hooks
- Set model once per session context
- Batch token monitoring into a single query at session start
- Measure actual "productive command" invocations instead

### 2. Retry Patterns Without Diagnosis
**Pattern:** 24 retry attempts detected, but only 5 attributed to tool misrouting

| Retry Type | Count | Root Cause Captured? |
|------------|-------|----------------------|
| Unknown error + retry | 11 | No |
| Wrong tool used | 5 | Yes |
| Failed operation | 2 | Partial |
| Timeout detected | 3 | No |
| Other | 3 | No |

**Example failure sequence from logs:**
```
1. "error what now?" — No diagnosis provided
2. Retry follows without context
3. Pattern repeats across session
```

**Issue:** Retries should log the failed tool name, input, and error message for later analysis.

**Recommendation:**
- Require /compact or SESSION_STATE.md write after 3+ failures
- Log failed tool calls with explicit error capture
- Flag "retry without diagnosis" as blocker for autonomous agents

### 3. GitHub vs GitLab Confusion (Minor)
**Pattern:** 9 GitHub mentions, 6 GitLab mentions, no routing errors detected

| Org | Mentions | Context |
|-----|----------|---------|
| GitHub | 9 | Mostly informational (proximity-explorer repo mentioned) |
| GitLab | 6 | Primary work org (Klever) |
| Klever (GitLab) | 496 (75%) | Correct routing observed |
| Supervisr | 152 (23%) | Correct routing observed |

**Status:** GitHub/GitLab routing is **clean**. No cross-org tool misuse detected.

---

## B) TOOLS USED MOST FREQUENTLY

### Tools by Category

#### Bash/Shell Operations
```
find                    10 uses
grep                     1 uses
(Other shell commands   <5 uses)
```
**Status:** Light usage; most file operations likely implicit in agent actions.

#### File I/O Operations
```
Read (file read)         6 uses
Write (file write)       7 uses
Edit (file modification) 0 uses
```
**Issue:** No explicit Edit operations logged, yet tickets show files were modified. Likely because:
- Edit operations occur but are not logged in display field
- OR bulk modifications via Bash
- Recommend explicit tool logging for auditability

#### Skills Invoked (Top 10)
```
buddy                    41
model                    40
btw                      29
login                    24
rate-limit-options       18
usage                     8
gab-operationalize        7
plugin                    6
dream/dreams             7 combined
memory                    5
```
**Pattern:** 160+ meta/admin commands (buddy, model, login, btw, rate-limit, usage) dwarf productive skills.

**Productive skills invoked:**
- `gab-operationalize` (7 uses) — Operationalize skill
- `plugin` (6 uses) — Plugin management
- `memory` (5 uses) — Memory/context management

**Issue:** No `create-tickets`, `jira`, `gitlab`, `post-comment`, or other core collaboration skills logged in display field. This suggests:
- Either they're called but not logged in .display
- OR they're invoked through skill runner without explicit invocation in the conversation history
- Requires deeper audit of actual tool calls (beyond display text)

#### MCP Tools
```
Slack                    6 uses
Notion                   4 uses
Gmail                    0 logged (but likely used)
GoogleCalendar           0 logged (but likely used)
```
**Status:** Minimal MCP tool logging. Authentication likely delays visibility into actual usage.

---

## C) SPECIFIC ROUTING ERRORS

### GitHub vs GitLab
**Status:** CLEAN
- 496 uses of Klever (GitLab) — correct routing
- 152 uses of Supervisr — correct routing
- 9 GitHub mentions — informational only (proximity-explorer repo context)
- No evidence of mis-routed tool calls between platforms

### Jira vs Other Tickets
**Status:** NOT OBSERVABLE in history data
- History.jsonl shows commands but not API tool calls
- No evidence of Jira misrouting (e.g., calling GitHub API for Jira tickets)
- Supervisr appears to use correct Atlassian (not GitHub)

### Org-Specific Misroutes
**Status:** NOT DETECTED
- No evidence of Klever tools called against Supervisr
- No evidence of cross-org credential misuse
- Org routing appears disciplined

---

## D) RECOMMENDATIONS

### 1. Eliminate Meta-Command Overhead
**Priority: HIGH**
- Consolidate `/buddy` + `/model` + `/btw` into a single `/context` summary command
- Auto-login on session start; remove `/login` from command histogram
- Batch token monitoring into session initialization
- Target: Reduce non-productive commands from 73% to <10% of total invocations

### 2. Capture Failed Tool Calls in SESSION_STATE
**Priority: HIGH**
- Log all tool failures with:
  - Tool name
  - Input parameters
  - Error message / status code
  - Timestamp
- Add to SESSION_STATE.md before session compaction
- Enable post-hoc analysis of retry patterns

### 3. Instrument Edit Tool
**Priority: MEDIUM**
- Ensure all Edit operations log to history.jsonl (currently showing 0 Edit ops, yet files are modified)
- This will reveal file modification patterns

### 4. Enable Skill Invocation Logging
**Priority: MEDIUM**
- Capture all tool invocations via `Skill("skill-name")` calls, not just slash commands
- Current 31 commands logged, but actual tool usage is likely 3-5x higher
- Recommendation: Log ALL tool calls regardless of invocation method

### 5. Implement "Retry Budget" for Autonomous Agents
**Priority: HIGH**
- Limit automatic retries to 1 per tool per session
- On 2nd failure, escalate to human or write diagnostic report
- Prevents "retry loops" without diagnosis (currently 24 retries with 11 undiagnosed)

### 6. Add Wrong-Tool Detection
**Priority: MEDIUM**
- Flag patterns like:
  - GitHub API called for GitLab operations
  - Bash used when CLI tool available
  - Multiple tools chained when one would suffice
- Current data shows only 5 explicit "wrong_tool_used" but likely undercounted

---

## E) DATA QUALITY NOTES

### What Was Observable
- 662 history.jsonl records in last 7 days
- 31 unique commands
- 150+ sessions
- 18 records mentioning "error" or "fail"
- 15 sessions with errors

### What Was NOT Observable
- Actual tool call arguments/inputs
- HTTP response codes from API tools
- File paths or data being read/written
- Skill execution details (only the skill name if logged as a command)
- MCP server authentication attempts
- Internal tool retry logic (only human-visible retries)

### Recommended Data Collection
1. Instrument Bash tool to log command + exit code
2. Log all Read/Edit/Write operations with file path + size
3. Capture Git operations with branch + outcome
4. Log Jira/GitLab/Gmail API calls with method + response code
5. Persist tool error details to SESSION_STATE.md automatically

---

## F) SUMMARY TABLE

| Finding | Severity | Evidence | Action |
|---------|----------|----------|--------|
| **Meta-command overhead** | HIGH | 160/218 commands (73%) are non-productive | Consolidate into /context |
| **Undiagnosed retries** | HIGH | 24 retries, 11 without root cause | Log failures to SESSION_STATE |
| **GitHub/GitLab routing** | LOW | 496 correct, 0 incorrect | ✓ No action needed |
| **Edit operations invisible** | MEDIUM | 0 Edit ops logged, files modified | Ensure Edit logs to history |
| **Skill invocations underlogged** | HIGH | 31 commands captured, likely 150+ tools used | Instrument skill runner |
| **Timeout detection weak** | MEDIUM | 3 timeouts mentioned, no diagnostic context | Log with stack trace |
| **MCP auth delays visibility** | MEDIUM | Slack/Notion logged 10 times total; likely used more | Improve auth logging |

