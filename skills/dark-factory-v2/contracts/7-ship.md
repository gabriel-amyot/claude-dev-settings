# Contract 7 — Ship

Version bump, push, create the MR, update Jira. The orchestrator already ran the pre-ship gate
before calling you (execution verified, no open CRITICAL, QA green) — do not re-litigate it, do the
ship.

Adapted from the old skill's Phase 7 (SHIP). Klever repos.

## Steps

1. **Version bump + CHANGELOG.** `/klever-mr` handles this via its gates. Final commit in the
   worktree: `<TICKET>: version bump + changelog`.
2. **Push the branch** (the branch from Phase 4). Handled by `/klever-mr`.
3. **Create the MR** via the `/klever-mr` skill — **WITHOUT** auto-merge. It enforces pre-flight
   gates (dev sync, version bump, CHANGELOG) and builds a WHY + WHAT description.
4. **Post the Jira comment** via `/post-comment` (draft on disk → preview → explicit approval →
   post). Include: MR link, AC summary, evidence highlights from the QA report, assumptions applied.
5. **Transition the ticket** to "In Review" or "In Testing" — the ceiling. Never higher.
   `cd ~/.claude/skills/jira && python3 jira_skill.py transition <TICKET> "In Review" --org <ORG>`.

## Guardrails (carried from v1)

- No direct push to `dev`/`main`. Feature branch + MR only.
- No destructive git (`--force`, `--amend` on pushed commits, rebase on shared branches).
- DAC repos: `dev` only, never `uat`/`main`.
- No IAM/auth changes without a human gate.
- The human merges the MR. You do not.

## Return

- `status`: pass | partial | stuck
- `summary`: include the MR URL
- `artifacts`: MR URL, Jira comment reference
