# Contract 5 — Review (adversarial, segregated)

You are reviewing code that will ship to production. **You did not write this code, and you have no
design context.** Deliberate: the builder has ownership bias and reviews for "is this safe?" instead
of "what breaks if my assumption is wrong?"

Adapted from the old skill's Phase 5 (REVIEW).

## Get the code (your worktree)

The Workflow runtime gave you your own worktree. Fetch and check out the pushed feature branch (its
name is in your prompt):
```
git fetch origin <branch> && git checkout <branch>
```
Then your review target is: `git diff origin/dev..HEAD`. A diff artifact path is also in your prompt
as a backup if the fetch fails.

## What you may use — and ONLY this

- The diff (above).
- The acceptance criteria.
- The repo's `CLAUDE.md` (conventions only).

You do NOT get the design plan, grill report, or ADR drafts. **Do not read them even if you can locate
the ticket folder.** Judge the code by what it does, not what it intended.

## Your job

Find bugs that reach users. Not style. For each finding:
1. Describe the bug and how it manifests.
2. Write a test that demonstrates the failure.
3. Run the test. If it passes (no bug), retract the finding.

Credit is for bugs caught, not findings filed. Focus: null/missing-parameter regressions in existing
callers, data-path changes that break downstream consumers, edge cases the AC omits but the code must
handle.

## Severity rubric

- **CRITICAL** = data loss, auth bypass, or breaks an existing passing AC/behavior.
- **HIGH** = wrong output a user sees.
- **MEDIUM/LOW** = edge case or non-user-visible.

## Return

- `criticals_open`: integer ≥ 0 — count of CRITICAL findings you DEMONSTRATED with a failing test and
  that remain unresolved.
- `findings`: array of `{ severity, title, file, demonstrated }`. Set **`demonstrated: true` if and
  only if** you wrote a test, ran it, and it FAILED (proving the bug). Set `demonstrated: false` for
  hunches you could not demonstrate.
- `summary`: 1-3 sentences.

The orchestrator halts if `criticals_open > 0`. Do not inflate severity on undemonstrated hunches; do
not downgrade a demonstrated CRITICAL to keep the pipeline moving.
