---
name: start
description: Initialize the sprint harness for a ticket. Creates state file, enters spec-gate phase.
arguments: ticket-id
---

# /harness start <ticket-id>

Initialize the sprint harness for autonomous execution of a ticket.

## Instructions

1. **Parse the ticket ID** from `$ARGUMENTS` (e.g., `KTP-115`, `KTP-450`).

2. **Locate the ticket folder** at `tickets/{TICKET-ID}/` in the current project. If it doesn't exist, tell the user to run `/ticket-init` first and stop.

3. **Read the AC file** at `tickets/{TICKET-ID}/jira/ac.yaml`. If it doesn't exist, tell the user to run `/pickup-ticket` first and stop.

4. **Read STATUS_SNAPSHOT.yaml** at `tickets/{TICKET-ID}/STATUS_SNAPSHOT.yaml` for current state.

5. **Determine the first AC to work on:**
   - Find the first AC with status != `done` in ac.yaml
   - If all ACs are done, report "All ACs complete" and stop

6. **Create the state file** at `.claude/sprint-harness-state.yaml`:

```yaml
version: 1
active: true
ticket: {TICKET-ID}
ac_file: tickets/{TICKET-ID}/jira/ac.yaml
phase: spec-gate
current_ac: {first-pending-AC}
completed_acs: [{list of done ACs}]
repos:
  - ~/Developer/grp-beklever-com/grp-app/grp-backend
  - ~/Developer/grp-beklever-com/grp-app/grp-frontend
  - ~/Developer/grp-beklever-com/grp-dac
  - ~/Developer/grp-beklever-com/grp-iac
allowed_paths: []
protected_paths: [.env, .env.local, package-lock.json]
started_at: "{ISO-8601-now}"
phase_entered_at: "{ISO-8601-now}"
last_gate_result: null
gate_failures: 0
iteration: 1
spec_gate_report: tickets/{TICKET-ID}/reports/status/spec-gate-report.yaml
context_manifest: tickets/{TICKET-ID}/reports/status/context-manifest.yaml
assumptions: []
```

7. **Report to the user:**
   - Ticket: {ID}
   - Total ACs: N (M done, K remaining)
   - Starting with: {AC-ID}: {AC description}
   - Phase: spec-gate
   - "Hooks are now enforcing phase constraints. Run the spec quality gate (Leo persona) to validate ACs, then `/harness advance`."

## After Start

The harness is now active. The phase-gate hook will enforce spec-gate constraints (read-only, no code writes). Claude should:

1. Run the **Spec Quality Gate** (Leo persona) using the prompt in `gates/spec-gate.md`
2. Write the spec gate report to `tickets/{TICKET-ID}/reports/status/spec-gate-report.yaml`
3. Call `/harness advance` to transition to context-gate
