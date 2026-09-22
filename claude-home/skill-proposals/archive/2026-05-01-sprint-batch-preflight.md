# Skill Proposal: sprint-batch-preflight
Date: 2026-05-01
Source: Sprint harness build session

## Trigger
When preparing for an overnight sprint run across multiple tickets. User says "validate the sprint" or "pre-check these tickets" before committing to autonomous execution.

## Scope
Global (works for any org with ticket folders)

## Draft Steps
1. Read sprint ticket list (from Jira sprint query or user input)
2. For each ticket: run spec gate (Leo) in dry-run mode
3. For each ticket: run context gate (Curator) in dry-run mode
4. Produce consolidated report: which tickets are ready, which have gaps, which need Jira clarification
5. Output recommended execution order (dependencies first, independent tickets parallelizable)
