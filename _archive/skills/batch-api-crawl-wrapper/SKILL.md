---
name: batch-api-crawl-wrapper
description: "EXPERIMENTAL. Wrap long-running crawl agents to use Claude Batch API for offline execution. 50% cheaper than interactive. Triggers: 'batch crawl', 'offline crawl', 'batch API crawl', 'run crawl async', 'background crawl'."
nav:
  bay: ops
  when: "Wrap crawl agents for Batch API execution. 50% cheaper than interactive."
  when_not: "Interactive session. Need real-time feedback."
---

# Batch API Crawl Wrapper (EXPERIMENTAL)

Wraps sprint-crawl or night-crawl agents to run via the Claude Batch API instead of keeping a terminal open.

**Status:** EXPERIMENTAL. Depends on Batch API supporting tool use. Check current API capabilities before attempting.

**Usage:** `/batch-api-crawl-wrapper <crawl-command> [--poll-interval 5m]`

## Why

- Batch API is 50% cheaper than interactive API
- No terminal needs to stay open for hours
- Results are available when you return

## Step 1: Prepare Crawl Context

Serialize everything the crawl agent needs:
- Ticket ID and AC list
- REPO_MAPPING.yaml content
- STATUS_SNAPSHOT.yaml content
- Any session state from prior runs

Write to: `tickets/{TICKET-ID}/batch-crawl-context-{date}.json`

## Step 2: Build Batch Request

Construct a Batch API request following the claude-api skill patterns:
- System prompt: the crawl agent's full instructions
- Messages: the serialized context as the first user message
- Tools: the standard tool set (Bash, Read, Write, Edit, Glob, Grep)
- Model: sonnet (per feedback: execution work uses Sonnet)

## Step 3: Submit and Poll

Submit the batch. Write the batch ID to `tickets/{TICKET-ID}/batch-id-{date}.txt`.

Poll at the specified interval (default 5m). Report status on each check.

## Step 4: Process Results

When batch completes:
1. Download the results
2. Extract any file writes the agent attempted
3. Apply the writes to the repo
4. Run verification (tests, health checks)
5. Report what was done and what needs human review

## Limitations
- Batch API may not support all tool types
- No interactive user gates during execution
- State file must be written before submission for ralph-loop recovery
- Max batch duration depends on API limits

## Fallback
If Batch API doesn't support the required tools, fall back to interactive mode with a warning about cost.
