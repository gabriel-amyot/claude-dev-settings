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

## Output (write to disk — always, even at zero criticals)

Write `<ticket_folder>/review/findings.json` (path in your prompt; this is a write, not a read of the
withheld design context). Persist it on EVERY run, including `criticals_open: 0`, so a later PARTIAL or
audit can be reconstructed without re-deriving from a raw diff. Shape:
```json
{
  "criticals_open": 0,
  "findings": [
    { "severity": "HIGH", "title": "...", "file": "<path>:<lines>", "demonstrated": true,
      "test_ref": "<test name + command + observed failure>" }
  ],
  "summary": "..."
}
```

## Return

- `criticals_open`: integer ≥ 0 — count of CRITICAL findings you DEMONSTRATED with a failing test and
  that remain unresolved.
- `findings_artifact`: the ABSOLUTE path of the `review/findings.json` you wrote above. This field is
  **schema-required** (0.9.3): a return without it is rejected. Write the file first, then return its
  path — never return a path you did not write. (QA spot-checks the file exists on disk.)
- `findings`: array of `{ severity, title, file, demonstrated }`. Set **`demonstrated: true` if and
  only if** you wrote a test, ran it, and it FAILED (proving the bug). Set `demonstrated: false` for
  hunches you could not demonstrate.
- `summary`: 1-3 sentences.

The orchestrator halts if `criticals_open > 0`. Do not inflate severity on undemonstrated hunches; do
not downgrade a demonstrated CRITICAL to keep the pipeline moving.
