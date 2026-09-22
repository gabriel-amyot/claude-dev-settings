# Skill Proposal: adversarial-fix-loop
Date: 2026-09-21
Source: session `noble-wren` — cesteral study + ttd-mcp port, 9 review passes across 8 build issues

## Trigger
After any builder agent lands a diff that will ship, when the user asks to "adversarially review and address the findings" — especially unattended. Nine passes ran this way in one session and produced 25+ real fixes plus one verified false-positive rejection.

## Scope
Global. The loop is vendor- and language-agnostic; only the reviewer command changes.

## Why a skill rather than a prompt
The loop has four properties that get dropped when improvised, and each one cost something before it was made explicit:
1. A **severity rubric supplied to the reviewer** (CRITICAL / MAJOR / MINOR / NIT with definitions), so its output maps mechanically onto the fix/ignore rule instead of needing interpretation.
2. A **fix scope**: address CRITICAL and MAJOR only; log MINOR/NIT. Without this the loop churns on wording.
3. An **iteration cap** (5) with an explicit escalation, plus the rule that a finding blocked by a *scope constraint* rather than by difficulty escalates immediately — more iterations cannot resolve it.
4. **Pre-existing vs introduced triage.** `git log -- <file>` over the branch range decides whether a finding gets fixed here or filed. Four pre-existing defects were filed rather than smuggled into an unrelated MR.

## Draft Steps
1. Extract the diff for the built unit. Prepend a reusable review template: the repo's non-negotiable invariants, the severity rubric, "cite file:line with a concrete failure scenario", "say plainly if a dimension is clean; do not invent findings", and "end with BLOCK or PASS".
2. Run the reviewer read-only. **Set reasoning effort explicitly** — Codex defaults to `low`. Grep the raw output for severity words; do not filter with a regex that can eat findings.
3. **Verify every finding before accepting it.** Reviewers produce false positives with confident prose (one cited a completeness rule against a field that was not a connection). Reject with evidence and say so.
4. For each verified finding, check `git log --oneline <base>..HEAD -- <file>`: introduced here → fix; pre-existing → file an issue with a reachability note and the reason it is out of scope.
5. Fix CRITICAL + MAJOR. Mutation-check each fix: seed the defect, confirm the new guard goes red, restore (never with `git checkout --` on a file holding uncommitted work).
6. Re-review. Cap at 5 iterations. Escalate to the human on a scope conflict or a surviving CRITICAL.
7. Report per finding: verified or rejected with evidence, what changed, the seed-and-restore result.

## Notes for the author
- A reviewer's BLOCK with an empty findings list is noise; read the enumerated list, not the verdict word.
- Reviewers that cannot run tests are static-only. Run the suite yourself and say which review was static.
- Findings *in the guards* are the highest-value class: a guard weaker than the invariant it pins certifies false confidence. One such round exposed a live production gap.
