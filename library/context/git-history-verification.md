# Git History Verification Rules

Load this file before writing or reviewing any PR body, commit message, or external content that asserts something about code history ("X was deleted," "X never existed," "X was added in commit Y").

Learned from SPV-72 (2026-05-06): an agent fabricated "Git history shows no warm-up ever existed in this codebase." The warm-up DID exist (added in DS-880 commit `bf4c1a7`, removed in SPV-21 commit `45998c2`). Dan found it in 3 minutes. Two agent sessions across 4 days missed it.

---

## Methodology: pickaxe (`-S`) over `--grep`

| Goal | Correct command | Wrong command |
|------|----------------|---------------|
| Find when code was added/removed | `git log -S "<token>" --all --oneline` | `git log --grep="<concept>"` |
| Find when a function was touched | `git log -S "<function_name>" --all` then `git show <commit> -- <file>` | `git log --diff-filter=D` (file-level, not code-level) |
| Verify a specific commit changed something | `git show <commit> -- <file>` | Searching commit messages for keywords |

`-S` (pickaxe) searches **actual diff content**. `--grep` searches **commit messages only**. A developer who writes "refactored auth" in a commit message may have deleted a warm-up call without mentioning it. `--grep` will never find that.

## Search code tokens, not concepts

The warm-up was implemented as `doOnSubscribe(subscription -> { webErsService.checkHealth()...})`. Searching for "warm-up" or "warmup" in diffs finds nothing. Search for the actual code tokens: `doOnSubscribe`, `checkHealth`, the method name, the variable name. Try at least 3 distinct tokens before concluding absence.

## When a ticket cites a commit, examine that commit first

If the ticket says "restore X deleted in commit Y," run `git show Y -- <likely-file>` BEFORE any broader search. If you cannot find X in Y's diff, the search is wrong, not the ticket. Widen the file path, check renames, check adjacent commits.

## Absence of evidence is not evidence of absence

If your searches return nothing, the correct conclusion is "my searches did not find it," NOT "it never existed." Before asserting non-existence in any external content:
1. Verify you searched with `-S`, not just `--grep`
2. Verify you searched for code tokens, not concept names
3. Verify you checked `--all` (all branches, not just current)
4. Try at least 3 different search terms
5. If a ticket or PR comment claims it existed, assume THEY are right and your search is incomplete

## Factual claims in external content require verification

Every PR body assertion about code history must pass this gate before publishing:
- "X was deleted in commit Y" -> `git show Y -- <file>` must show the deletion
- "X never existed" -> `git log -S "<token>" --all` must return empty for at least 3 relevant tokens
- "X was added in commit Y" -> `git show Y -- <file>` must show the addition

If you cannot verify the claim, do not make it. Write "See commit <hash>" and let the reader verify, or state what you found ("the earliest appearance in git history is commit X") rather than what you didn't find.

## Intra-session contradiction detection

If your investigation contradicts your own earlier statements in the same session, STOP. Do not quietly overwrite the earlier conclusion. Flag the contradiction explicitly, re-investigate with different search terms, and only proceed when you can explain why one conclusion is correct and the other was wrong.

## Reviewing agent-written PR bodies

When reviewing a PR body authored by a prior agent session, treat all historical claims as **unverified assertions**. Run the verification gate above on each factual claim before approving the PR body for publication.
