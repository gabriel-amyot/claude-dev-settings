# Skill Proposal: klever-revert-and-isolate
Date: 2026-10-29
Source: KTP-1289 media-api Boot 4 revert (!46) and isolated security draft (!47)

## Trigger
"revert that MR on dev", "back this out but keep the work for review", "isolate X in its own branch", after a merged change turns out to be unsafe on a Klever app repo.

## Scope
org (Klever GitLab app repos: Java, Node, Python)

## Draft Steps
1. Worktree from origin/dev; `git revert -m 1` each merge (newest first); assert `git diff --stat <pre-merge commit> HEAD` is empty.
2. Fold local reverts into one `{TICKET}: revert ...` commit (unpushed only); restore CHANGELOG from origin/dev and add a Reverted entry; bump the version FORWARD (never back) so the release tag does not collide.
3. Push without `[skip ci]`, wait for the branch test job on the exact commit, create the MR via klever-mr gates, merge only on explicit approval.
4. Re-apply branch from the revert tip: `git checkout <merged final state> -- .`, keep CHANGELOG, bump the minor version, push, open as `Draft:` with a regression checklist for the code owner.
5. Disarm deploy traps: close any open release MR carrying the reverted code; note stale manual DAC apply jobs (cancel does not cancel manual jobs) and let the next dev pipeline move the DAC version variable.
