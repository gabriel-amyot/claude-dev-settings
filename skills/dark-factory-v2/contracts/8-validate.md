# Contract 8 — Validate (post-merge; run by the MAIN LOOP, not the workflow)

Post-merge verification on dev. This makes the run "ticket to dev," not "ticket to MR."

**Not part of the auto-run.** The workflow ends at `READY_TO_SHIP`; the main loop creates the MR and,
once the human merges it, invokes this contract as a separate step. (Reason: a workflow agent has no
native wait primitive and the merge depends on a human — see docs/review-findings-v0.1.0.md V4.)

Adapted from the old skill's Phase 8 (VALIDATE). Backend/Java floor.

## Steps

1. **Confirm the merge.** `git fetch origin` then `git branch --contains <pushed_sha> origin/dev`.
   If the SHA is in `origin/dev`, it merged. Poll at ~60s intervals up to a **hard ceiling of 5 polls
   (~5 minutes)**. If still not merged, return `status: partial` ("awaiting human merge") and stop —
   do not block longer.
2. **Verify on dev (backend/Java).** Once merged, curl the key endpoints on dev and check the
   response shapes match the ACs.
3. **Human gate.** Frontend, or no automated check available → `status: partial` + flag a human must
   verify on dev.
4. **On failure:** log findings. Do NOT reopen the ticket.

## Nightly dev schedule

Klever dev shuts down ~20:00 ET. If dev returns 000/503 in that window, that is the schedule, not a
failure — return `status: partial` noting it and that verification should be re-run in the morning.

## Return

- `status`: pass | partial | stuck
- `summary`: what was verified (or why partial)
- `notes`: anything to re-check later
