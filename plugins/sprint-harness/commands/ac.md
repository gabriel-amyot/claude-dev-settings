---
name: ac
description: Switch to a different AC. Resets phase to spec-gate (or planning with --skip-gates).
arguments: AC-N [--skip-gates]
---

# /harness ac <AC-N> [--skip-gates]

Switch the harness to work on a different AC.

## Instructions

1. **Parse arguments** from `$ARGUMENTS`:
   - AC identifier (e.g., `AC-3`, `AC-1`)
   - Optional `--skip-gates` flag

2. **Read the state file.** If harness not active, report error and stop.

3. **Read ac.yaml** and verify the requested AC exists.

4. **Check current phase:** If current AC is in `implementation` or later and not yet `done`, warn: "Current AC {current_ac} is in phase '{phase}' and not complete. Switching will lose progress. Proceed? Use '/harness abort' to explicitly abandon, or '/harness ac {AC-N} --force' to confirm."
   - If `--force` is in arguments, proceed anyway.
   - Otherwise, stop and let Claude decide.

5. **Update state file:**
   - Set `current_ac` to the new AC
   - If `--skip-gates`: set `phase` to `planning` (gates already validated for this ticket)
   - Otherwise: set `phase` to `spec-gate` (re-validate for new AC context)
   - Update `phase_entered_at` to now
   - Reset `gate_failures` to 0
   - Reset `last_gate_result` to null
   - Add the previous AC to `completed_acs` if it was in `done` phase

6. **Report:**
   - "Switched to {AC-N}: {description}"
   - "Phase: {new_phase}"
   - "Run the {spec gate / implementation plan} to proceed."
