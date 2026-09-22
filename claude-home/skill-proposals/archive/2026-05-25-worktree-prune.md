# Skill Proposal: worktree-prune
Date: 2026-05-25
Source: Frontend worktree housekeeping session

## Trigger
"prune worktrees", "clean up worktrees", "too many worktrees", "worktree sprawl", or when `git worktree list` for any repo returns >10 entries.

## Scope
global (works on any git repo)

## Draft Steps
1. **Inventory** — `git worktree list` + `git fetch origin {default-branch}` + classify each worktree (merged/unmerged/active based on last commit date and merge status)
2. **Adversarial verify** — For each candidate: check ahead count, diff against default branch, uncommitted/untracked files, whether code shipped via different branch name
3. **Present** — Show classified table with safety assessment per worktree
4. **User selects** — AskUserQuestion: prune merged only, prune all dead, pick individually
5. **Execute** — `git worktree prune` first, then `git worktree remove --force` for approved removals. Report final count.

## Notes
- Should detect default branch automatically (dev for Klever DAC, main/master for others)
- `/tmp` worktrees that no longer exist get cleaned by `git worktree prune` without force
- Worktrees with `node_modules`/`.next` as only untracked content are safe to force-remove
- The `batch-pr-consolidation` skill should ideally clean up constituent worktrees after shipping, but that's a separate enhancement
