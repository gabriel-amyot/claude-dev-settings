# Skill Proposal: codex-adversarial-review-loop
Date: 2026-10-27
Source: KTP-1358 (ZIP limit fix): 7 Codex rounds across decision, bug ticket, backend and frontend diffs; every round found a real defect

## Trigger
"review with codex", "adversarially review with codex", before pushing a branch, before posting a decision or bug ticket, after each fix round ("re-check").

## Scope
global

## Draft Steps
1. Write the review prompt to disk with the Write tool (heredocs hung in long sessions). Prompt = role "DISPROVE, do not confirm", read-only rules, files to read, numbered attack list, output contract: verdict line (SHIP / SHIP WITH FIXES / DO NOT SHIP, or AGREE / DISAGREE for decisions), findings with severity + file:line + concrete fix, word cap, "label unverified claims UNVERIFIED".
2. Build a review root in /tmp with symlinks to the repo worktree(s) and the ticket folder, so Codex sees exactly what it needs.
3. Run in background: `codex exec -s read-only -C <root> --skip-git-repo-check -o <ticket>/codex-<name>.md "$(cat <prompt>)" > <log> 2>&1 < /dev/null` (stdin from /dev/null, or it waits on "Reading additional input from stdin").
4. Read the verdict. Spot-check the top 2 or 3 evidence lines yourself before acting. Send fixes to the implementer agent with "test must fail on the current commit first".
5. Re-check with a narrower prompt scoped to the fix commit diff (`git diff <prev>..<fix>`). Stop when only MINOR findings remain, or after the user accepts the residual risk. Route deferred findings into follow-up tickets.
