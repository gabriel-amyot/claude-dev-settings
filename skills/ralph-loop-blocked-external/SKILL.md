---
name: ralph-loop-blocked-external
description: "Detects external infrastructure blockers during a ralph-loop session and declares BLOCKED_EXTERNAL state. Use when CI/CD pipelines fail repeatedly, registry is down, or infrastructure is unavailable and retrying is futile."
---

# /ralph-loop-blocked-external

Protocol for detecting, declaring, and recording external infrastructure blockers from within an agent session running under ralph-loop. When infrastructure outside the agent's control is down, continuing to retry burns tokens, pollutes pipeline history, and produces no value. This skill provides the protocol to declare BLOCKED_EXTERNAL cleanly, write a structured blocker report, and exit or pause gracefully.

This skill does NOT modify the ralph-loop plugin. It is the agent-side complement to the circuit-breaker rule in CLAUDE.md: max 3 retries for the same error, then declare blocked.

---

## When to Invoke This Skill

Invoke this skill when ANY of the following conditions are met:

1. The same CI/CD pipeline error appears 3 or more consecutive times without change in the error text.
2. A known nightly downtime window is active (Datasophia registry: ~11 PM to 5 AM ET).
3. An external service returns a 5xx error or DNS failure on 3 or more consecutive probes.
4. A build artifact (Docker image, Maven dependency, npm package) cannot be fetched and there is no local fallback.
5. Auth credentials have expired and the rotation path requires human action (e.g., Auth0 M2M client secret rotation).
6. The ralph-loop iteration count has reached a threshold where every iteration is attempting the same blocked operation.

Do NOT invoke this skill for:
- Transient errors on the first or second attempt (wait for a third identical failure).
- Errors caused by agent code bugs (those are fixable from within the session).
- Auth failures that can be resolved by clearing a token cache or re-fetching M2M credentials automatically.

---

## Detection Protocol

### Step 1: Classify the Failure

Read the last 3 pipeline or command outputs. Ask:

- **Is the error text identical or near-identical across all 3?** If yes, this is not a fluke.
- **Is the failing component external to the repo?** (registry, build server, auth provider, cloud API) If yes, the agent cannot fix it.
- **Has any iteration made forward progress?** If no iteration produced a different outcome, retrying is not a strategy.

Cross-reference the error text against `references/failure-patterns.md` to identify the pattern and classification.

### Step 2: Check Known Downtime Windows

Before concluding blocked, verify the time of day:

- If current time is between 11 PM and 5 AM ET AND the error matches the Datasophia registry pattern, this is a scheduled outage. Declare BLOCKED_EXTERNAL immediately. No further retries.
- If the error matches a pattern classified as `persistent` in `references/failure-patterns.md`, declare BLOCKED_EXTERNAL.
- If the error matches a pattern classified as `transient` and fewer than 3 consecutive identical failures have occurred, continue with caution.

### Step 3: Confirm No Local Workaround

Before declaring blocked, verify:

- Can the failing operation be skipped or deferred within this session?
- Is there a local fallback (cached image, local Maven repo, `.env` override)?
- Can a different sub-task be executed instead, preserving forward progress on other ACs?

If a workaround exists: use it and document it in the session state. Do NOT declare BLOCKED_EXTERNAL.

If no workaround exists: proceed to declaration.

---

## Declaration Protocol

### Step 1: Write to ralph-loop State File

The ralph-loop plugin maintains `.claude/ralph-loop.local.md` in the repo root. Append a BLOCKED_EXTERNAL section:

```markdown
## BLOCKED_EXTERNAL
declared_at: {ISO-8601 timestamp}
blocker_type: {REGISTRY_OUTAGE | NETWORK_TIMEOUT | BUILD_INFRA | AUTH_EXPIRY | CLOUD_QUOTA | OTHER}
error_fingerprint: "{first ~100 chars of the repeating error}"
consecutive_failures: {count}
recommended_action: "{human-readable next step}"
estimated_resolution: "{e.g., 'After 5 AM ET', 'Requires Auth0 secret rotation', 'Unknown — check Datasophia status page'}"
```

Do NOT overwrite the entire state file. Append only. The existing iteration count and progress log must be preserved for the next session.

### Step 2: Write Blocker Report

Write a blocker report to `tickets/{TICKET-ID}/reports/status/blocked-external-{YYYY-MM-DD}.md`.

Use this template:

```markdown
# BLOCKED_EXTERNAL Report

**Ticket:** {TICKET-ID}
**Session date:** {YYYY-MM-DD}
**Declared at:** {HH:MM TZ}
**Blocker type:** {type from classification}

## What Failed

{One paragraph describing the operation that failed and what it was trying to accomplish.}

## Error Evidence

```
{Paste the repeating error message verbatim. Truncate to 30 lines if longer.}
```

## Failure Count

- First observed: iteration {N}, {timestamp}
- Last observed: iteration {N}, {timestamp}
- Consecutive identical failures: {count}
- Total pipeline triggers this session: {count}

## Why This Is External

{One to three sentences explaining why the agent cannot fix this. E.g., "The Datasophia Terraform registry is an external infrastructure dependency. The registry is unavailable during its nightly maintenance window. No code change can resolve a network-level service outage."}

## Work Completed Before Block

{Bullet list of ACs or sub-tasks that were completed or partially completed before the blocker was hit. Be specific — "AC-2 code complete, not deployed" is better than "partial progress."}

## Recommended Next Step

{Concrete human action. Examples:
- "Wait until after 5 AM ET and re-trigger the pipeline."
- "Rotate the Auth0 M2M client secret and update the DAC CI/CD variable."
- "Check cicd.prod.datasophia.com status page. If still down, file a support ticket."}

## Resume Instructions

When the infrastructure recovers, the next session should:
1. Read this report.
2. Read `tickets/{TICKET-ID}/reports/status/` for the most recent session state.
3. {Specific resume step: e.g., "Trigger a new pipeline on the `dev` branch for the commit tagged {TAG}."}
4. Verify the fix is deployed before marking ACs complete.
```

### Step 3: Update the Nearest INDEX.md

After writing the blocker report, update `tickets/{TICKET-ID}/reports/status/INDEX.md`. Add an entry:

```markdown
- `blocked-external-{YYYY-MM-DD}.md` — BLOCKED_EXTERNAL declaration. {blocker type}. Consecutive failures: {N}. Resume: {one-line action}.
```

If the INDEX.md does not exist, create it with a header and the entry.

### Step 4: Exit the Session

Output this message to the conversation (verbatim structure, fill in values):

```
BLOCKED_EXTERNAL declared.

Blocker: {type}
Error: {first line of repeating error}
Failures: {N} consecutive identical failures

Work saved: {list of completed ACs or sub-tasks}
Blocker report: tickets/{TICKET-ID}/reports/status/blocked-external-{date}.md

Next step: {recommended action from report}

Exiting session. Ralph-loop will not be re-invoked until the blocker resolves.
```

Do not continue attempting the blocked operation. Do not trigger additional pipelines. Exit cleanly.

---

## Passive Circuit Breaker (No Explicit Declaration)

If the agent running under ralph-loop does not explicitly call this skill, a passive circuit breaker still applies. Agents MUST self-enforce:

1. Track consecutive identical failures with an internal counter.
2. At 3 consecutive identical failures: call this skill immediately.
3. Never trigger more than 5 pipelines for the same commit in a single session, regardless of error type.
4. If the ralph-loop iteration count shows no forward progress across 3 consecutive iterations, treat it as a blocked state even if the errors are not identical.

These rules override any completion promise. A completion promise of `ALL_ACS_DONE` does not justify infinite retries on a down registry.

---

## Recovery Check (Next Session)

At the start of any new session where a previous session declared BLOCKED_EXTERNAL:

1. Read `.claude/ralph-loop.local.md`. Check for the `BLOCKED_EXTERNAL` section.
2. Read the blocker report from `tickets/{TICKET-ID}/reports/status/blocked-external-*.md`.
3. Verify the blocker has resolved before proceeding:
   - For registry outages: curl the registry endpoint and verify 200.
   - For auth expiry: verify the credential can be fetched and used.
   - For build infra: attempt a single small build operation before launching a full pipeline.
4. If the blocker has NOT resolved: declare BLOCKED_EXTERNAL again immediately. Do not proceed.
5. If the blocker HAS resolved: clear the `BLOCKED_EXTERNAL` section from the state file and proceed with resume instructions from the report.

---

## Blocker Type Reference

See `references/failure-patterns.md` for full pattern catalog with error strings, classification, and recommended actions.

Quick classification table:

| Type | Fixable By Agent? | Typical Duration | Action |
|------|------------------|-----------------|--------|
| `REGISTRY_OUTAGE` | No | Hours (nightly) | Wait for window to close |
| `NETWORK_TIMEOUT` | No (if persistent) | Unknown | Check status page, wait |
| `BUILD_INFRA` | No | Hours | Check status, wait |
| `AUTH_EXPIRY` | Sometimes | Until rotated | Rotate or escalate |
| `CLOUD_QUOTA` | No | Until quota resets | Escalate to human |
| `IMAGE_PULL_FAILURE` | No | Until image exists | Verify tag, check registry |

---

## Examples

### Example 1: Datasophia Registry Nightly Outage

Agent is in iteration 4 of a DAC deploy loop. Three consecutive pipelines have failed with:
```
Error accessing remote module registry: cicd.prod.datasophia.com
```

Current time is 12:30 AM ET.

Agent action:
1. Cross-reference failure-patterns.md: matches `REGISTRY_OUTAGE` pattern, classified `persistent-nightly`.
2. Current time is within 11 PM to 5 AM ET window.
3. Declare BLOCKED_EXTERNAL. Blocker type: `REGISTRY_OUTAGE`.
4. Write blocker report. Estimated resolution: "After 5 AM ET."
5. Exit.

### Example 2: Auth0 M2M Token Expiry

Agent is in iteration 2. A service-to-service call returns 401. Agent clears the token cache and retries. Still 401. Agent retries again. Still 401.

Three consecutive 401s from the same endpoint after cache-clearing.

Agent action:
1. Cache clearing did not resolve. This is a credential issue, not a cache issue.
2. Declare BLOCKED_EXTERNAL. Blocker type: `AUTH_EXPIRY`.
3. Recommended action: "Rotate the Auth0 M2M client secret and update the CI/CD variable in the DAC repo."
4. Write blocker report.
5. Exit.

### Example 3: Transient Network Error (Do NOT declare)

Agent calls an API endpoint. It returns a 503. Agent waits and retries. Second call succeeds.

No BLOCKED_EXTERNAL declaration. Log the transient error in session notes and continue.
