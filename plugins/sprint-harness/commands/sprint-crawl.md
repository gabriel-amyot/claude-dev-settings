---
name: sprint-crawl
description: Launch autonomous sprint execution for a ticket. Single command, single agent, full lifecycle.
arguments: ticket-id [--skip-gates] [--ac AC-N] [--dry-run]
---

# /sprint-crawl <ticket-id> [options]

Launch the sprint-crawl agent for autonomous ticket execution.

## Instructions

1. **Parse arguments** from `$ARGUMENTS`:
   - Ticket ID (required): e.g., `KTP-450`
   - `--skip-gates`: Skip spec and context gates
   - `--ac AC-N`: Start from specific AC
   - `--dry-run`: Run gates only, report findings, don't implement

2. **Read the sprint-crawl agent** at `~/.claude/agents/sprint-crawl.md`

3. **Follow the agent's lifecycle exactly**, starting from Phase 0.

4. **If running under ralph-loop:** The stop hook will re-feed this prompt on each iteration. The harness state file persists your progress. On re-entry, read the state file and resume from your current phase.

This is the ONLY command needed for autonomous work. It replaces the old pattern of choosing between night-crawl/dev-crawl and manually configuring harness profiles.
