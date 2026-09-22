# Skill Proposal: Ralph-Loop BLOCKED_EXTERNAL State
Status: BUILT (2026-04-21 — functional test: PASS, gated)
Date: 2026-04-21
Source: SPV-165 nightcrawl incident — 15 failed pipelines from registry outage

## Trigger
When ralph-loop is running and the agent encounters an infrastructure failure (registry down, network error, build infra unavailable) that will not resolve within the session.

## Problem
Ralph-loop currently has two states: "completion promise MET" (exit) and "completion promise NOT MET" (re-invoke). When infrastructure is down, NOT MET causes infinite re-invocation. The agent retries the same failing operation each iteration, burning tokens and polluting pipeline history.

## Scope
Global (ralph-loop plugin)

## Draft Steps
1. Add a third completion state: `BLOCKED_EXTERNAL` — agent declares infrastructure is down, not fixable from within the session.
2. When ralph-loop receives BLOCKED_EXTERNAL: either exit entirely, or switch to exponential backoff (15min, 30min, 60min) instead of immediate re-invocation.
3. Agent must write a blocker report to `tickets/{ID}/reports/status/` with: what failed, how many times, the error, and recommended next step.
4. Ralph-loop state file should record the blocked reason so a future session can check if the blocker resolved.
5. Add a max-consecutive-identical-failure counter (default 3) as a fallback circuit breaker in case agents don't explicitly declare BLOCKED_EXTERNAL.
