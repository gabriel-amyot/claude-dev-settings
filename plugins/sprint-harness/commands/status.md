---
name: status
description: Display current harness state including phase, AC progress, assumptions, and gate status.
---

# /harness status

Display the current sprint harness state.

## Instructions

1. **Read the state file** at `.claude/sprint-harness-state.yaml`. If it doesn't exist, report "Harness not active. Use '/harness start <ticket-id>' to begin." and stop.

2. **Read ac.yaml** to get full AC list with statuses.

3. **Display state in this format:**

```
Sprint Harness Status
=====================
Ticket:       {ticket}
Phase:        {phase}
Current AC:   {current_ac}: {ac_description}
Iteration:    {iteration}
Started:      {started_at}

AC Progress:
  [x] AC-1: {description} (done)
  [>] AC-2: {description} (current - {phase})
  [ ] AC-3: {description} (pending)

Gate Status:
  Last result:  {last_gate_result}
  Failures:     {gate_failures}

Spec Gate:    {status from spec-gate-report.yaml or "not run"}
Context Gate: {status from context-manifest.yaml or "not run"}

Assumptions:
  - {assumption 1}
  - {assumption 2}

Protected Paths: {list}
Repos: {list}
```

4. If there are assumptions from the spec gate, highlight them prominently.

5. If `gate_failures >= 2`, add a warning about potential blockers.
