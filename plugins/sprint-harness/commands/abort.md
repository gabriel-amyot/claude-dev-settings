---
name: abort
description: Abort the current AC with a reason. Sets phase to done, allows clean exit.
arguments: reason
---

# /harness abort <reason>

Abort the current AC and allow clean exit.

## Instructions

1. **Parse reason** from `$ARGUMENTS`.

2. **Read current state** from state file.

3. **Update state file:**
   - Set `phase` to `done`
   - Set `last_gate_result` to `abort`

4. **Write abort record** to `tickets/{TICKET}/reports/status/harness-abort-{date}.md`:
   ```markdown
   # Harness Abort: {TICKET} {current_ac}

   **Date:** {now}
   **Phase at abort:** {phase}
   **Reason:** {reason}
   **Gate failures:** {gate_failures}
   **Completed ACs:** {list}
   ```

5. **Report:**
   - "Aborted {current_ac} at phase '{phase}'."
   - "Reason: {reason}"
   - "Abort record written to reports/status/"
   - "Use '/harness ac {next-AC}' to continue with another AC, or '/harness reset' to disable harness."
