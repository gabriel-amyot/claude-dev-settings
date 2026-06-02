# Contract 8 — Validate

Post-merge verification on dev. This is what makes the run "ticket to dev," not "ticket to MR."

Adapted from the old skill's Phase 8 (VALIDATE). Backend/Java floor.

## Steps

1. **Check for the merge.** `git fetch origin` then `git branch --contains <pushed_sha> origin/dev`.
   If the SHA is in `origin/dev`, the MR is merged. Poll at ~60s intervals, but do NOT busy-loop
   indefinitely — if it is not merged within a reasonable window, return `status: partial` noting
   "awaiting human merge" and stop. (A future version can background this wait; the seed does not.)
2. **Verify on dev (backend/Java).** Once merged, curl the key endpoints on dev and verify the
   response shapes match the ACs.
3. **Human gate.** If the ticket touches frontend, or no automated check exists, return
   `status: partial` and flag that a human must verify on dev.
4. **On failure:** log findings. Do NOT reopen the ticket.

## Nightly dev schedule

Klever dev shuts down after ~20:00 ET. If dev returns 000/503 during that window, that is the
schedule, not a failure — return `status: partial` noting the schedule and that verification should
be re-run in the morning.

## Return

- `status`: pass | partial | stuck
- `summary`: what was verified (or why partial)
- `notes`: anything to re-check later
