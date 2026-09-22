---
name: advance
description: Attempt to advance to the next phase. Validates gate conditions before transitioning.
---

# /harness advance

Validate the current phase's gate conditions and advance to the next phase if satisfied.

## Instructions

1. **Read the state file** at `.claude/sprint-harness-state.yaml`. If it doesn't exist, report "Harness not active" and stop.

2. **Read current phase** and run the appropriate gate check:

### Gate Checks by Phase

**spec-gate → context-gate:**
- Check: `tickets/{TICKET}/reports/status/spec-gate-report.yaml` exists
- Check: `status` field is NOT `abort`
- If abort: report "Spec gate aborted. Ticket blocked pending Jira clarification. Use '/harness abort' to exit cleanly."
- If report missing: report "Spec gate report not found. Run Leo spec quality gate first."

**context-gate → planning:**
- Check: `tickets/{TICKET}/reports/status/context-manifest.yaml` exists
- Check: `status` field is NOT `not-ready`
- If not-ready: report which checks failed (read the manifest) and what needs fixing
- If manifest missing: report "Context manifest not found. Run context curator first."

**planning → implementation:**
- Check: at least one file exists in `tickets/{TICKET}/reports/architecture/` that was created/modified today
- If missing: report "No implementation plan found in reports/architecture/. Write the plan first."

**implementation → review:**
- Check: Run `git diff --name-only` to verify files were actually modified
- Check: Tests should have been run (look for test output in recent bash output, or ask Claude to confirm)
- Note: This is a soft gate. The agent attests that tests pass. The review phase will verify.

**review → verification:**
- Check: A review report exists in `tickets/{TICKET}/reports/reviews/` created today
- Check: The report does not contain findings with severity "CRITICAL"
- If CRITICAL findings exist: report "CRITICAL findings in review. Address them before advancing. Return to implementation phase if code changes needed."
  - If code changes needed: set phase back to `implementation` instead of advancing

**verification → ship:**
- Check: Read `jira/ac.yaml` and verify current AC has `status: done`
- If not done: report "AC {current_ac} status is not 'done' in ac.yaml. Update it first."

**ship → done:**
- Check: `git log --oneline -1` shows a commit message referencing the ticket
- Check: `git status` shows clean working tree (all changes committed)
- Check: Branch has been pushed (`git rev-list @{u}..HEAD` is empty, or branch was just pushed)
- If not pushed: report "Changes not pushed. Run `git push` first."

3. **If gate passes:**
   - Determine next phase from the sequence: spec-gate → context-gate → planning → implementation → review → verification → ship → done
   - Update state file: set `phase` to next phase, update `phase_entered_at`, set `last_gate_result: pass`, reset `gate_failures: 0`
   - Report: "Gate passed. Advanced to phase: {next_phase}."
   - If advancing to `done`: report "AC {current_ac} complete! Use '/harness ac {next-AC}' to start next AC, or '/harness reset' if all ACs are done."

4. **If gate fails:**
   - Increment `gate_failures` in state file
   - Set `last_gate_result: fail`
   - Report exactly what condition failed and what Claude needs to do to satisfy it
   - Do NOT advance the phase

## Phase Sequence

```
spec-gate → context-gate → planning → implementation → review → verification → ship → done
```

## Edge Cases

- If `gate_failures >= 3` for the same phase: add a warning "3+ gate failures on this phase. Consider '/harness abort' if blocked."
- If phase is already `done`: report "Already complete. Use '/harness ac' for next AC."
- If review reveals CRITICAL findings requiring code changes: set phase back to `implementation` (not forward to verification).
