---
name: reset
description: Disable the harness by removing the state file. All hook enforcement stops.
---

# /harness reset

Disable the sprint harness by removing the state file.

## Instructions

1. **Read the state file** to capture final state for the report.

2. **Remove** `.claude/sprint-harness-state.yaml`.

3. **Report:**
   - "Sprint harness disabled."
   - "Final state: ticket={ticket}, phase={phase}, AC={current_ac}"
   - "Completed ACs: {list}"
   - "All hook enforcement is now inactive."
   - "Audit trail preserved at .claude/sprint-harness-audit.log"

4. Do NOT remove the audit log or any reports. Those are permanent artifacts.
