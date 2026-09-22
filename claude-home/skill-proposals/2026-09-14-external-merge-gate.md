# Skill Proposal: external-merge-gate
Date: 2026-09-14
Source: autonomous wayfinder session on map 38 (Powers MCP), KTP-1182 — ran this loop 5 times across 3 MRs, caught 6 real defects

## Why this is worth a skill

Gabriel's standing instruction for autonomous merges is "ask an adversarial review from Codex each time and merge when it passes." Executing that well is not one command — it is a loop with a judgement step in the middle that is easy to get wrong in the expensive direction. In one session it blocked six times: three were pre-existing trunk defects (correctly pushed back, re-verdicted PASS in one round) and three were real diff-introduced defects the *internal* factory gates had already passed (a served instruction naming a nonexistent parameter; a hard-link and a FIFO attack on a lock sidecar). A reviewer that blocks on both classes with identical confidence is only useful if the caller triages provenance before responding.

## Trigger

An autonomous or semi-autonomous run is about to merge to `dev` and the human is not present to review. Phrases: "adversarial review before merge", "Codex-gate this", "review then merge if it passes". Also the natural tail of `dark-factory` / `sprint-crawl` output at `READY_TO_SHIP`, and of any `/klever-mr` where the human pre-authorized merge-on-pass.

Not for: a human-reviewed MR (that is `/crit`), a teammate's MR (`colleague-review-klever`), or post-hoc review of already-merged code.

## Scope

Global — the loop is provider- and repo-agnostic. The Klever specifics (target `dev`, version-bump gate, DAC rules) come from `/klever-mr`, which this skill calls rather than reimplements.

## Draft steps

1. **Build the review brief, not just the diff.** State: what the change does, the invariants that must hold, the exceptions already accepted (with their reason), the scope boundary ("judge THIS diff"), and `End with exactly one line: VERDICT: PASS or VERDICT: BLOCK`. Pipe the brief on stdin, then `git diff origin/<trunk>...HEAD` after it. Mechanics and failure modes: the `codex-cli-adversarial-review-patterns` bibliothèque page plus the two 2026-09-14 inbox entries.
2. **Read the verdict from a file.** stdout to its own path; stderr holds a full echo of the prompt and will bury the verdict if merged.
3. **On BLOCK, triage every finding by provenance BEFORE drafting a response.** For each: `git show origin/<trunk>:<file>` and check whether the diff touches the named lines. Pre-existing and untouched → pushback candidate. Introduced or worsened by this diff → fix it, no exceptions, even when the defect originates in an approved spec. This step is the skill; it is also the step an impatient agent skips.
4. **Pushback, when earned, is four sentences:** the trunk evidence, the house rule (pre-existing defects route to their own ticket, never fold into an unrelated MR), where the finding was routed so it is not lost, and the narrow question "how does THIS diff make it worse than the trunk?" Never argue from review fatigue.
5. **Fix, when earned, is RED-first**, including for hang-class bugs where the RED proof is the hang itself (run that test alone, never inside the suite).
6. **Re-review after every response**, quoting which blockers were fixed and which were routed. Loop until PASS, with a bounded round count — three rounds without convergence is an escalation to the human, not a fourth round.
7. **On PASS: run `/klever-mr`, arm merge-when-pipeline-succeeds, confirm the merge commit on the trunk, clean up the worktree and branch.**
8. **Deposit every routed pre-existing finding** on its ticket or map before closing out, and keep the transcripts as review artifacts under the ticket folder.

## Open questions for the design pass

- Round cap and escalation shape (3 seems right from this session; all convergences happened in 1-2).
- Whether to require a second reviewer instrument when the first PASSes a diff that internal gates also PASSed — `instrument-diversity` argues agreement between same-premise reviewers is not corroboration.
- How much of step 3 can be mechanical (a script that annotates each finding's cited file/line with "touched by this diff: yes/no") versus left to judgement.
