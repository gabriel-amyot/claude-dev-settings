---
name: worktree-prune
description: "Safely inventory and remove stale git worktrees. Use whenever the user mentions worktree cleanup, worktree sprawl, 'too many worktrees', 'prune worktrees', 'clean up worktrees', or when `git worktree list` returns more than ~10 entries. Classifies each worktree as merged / unmerged / active, adversarially verifies before removing, asks which to drop, then prunes. Reach for this proactively after a stretch of feature work or at session cleanup when worktrees have piled up — leftover worktrees waste disk and make `git worktree list` unreadable, but removing one with unmerged work loses it."
nav:
  bay: ops
  when: "Inventory and safely remove stale git worktrees. Classifies merged/unmerged/active, verifies, then prunes."
  when_not: "Creating a new worktree (use superpowers:using-git-worktrees). Pruning git branches without worktrees (plain git branch -d)."
---

# Worktree Prune

Remove stale git worktrees without losing unmerged work. Worktrees accumulate fast during feature work — one per ticket, plus `/tmp` scratch worktrees — and `git worktree list` becomes unreadable past a dozen entries. The danger isn't disk; it's force-removing a worktree that still holds the only copy of unmerged commits or uncommitted edits. This skill classifies every worktree, proves each removal candidate is safe, and only then removes what you approve.

## When this runs

Trigger on "prune worktrees", "clean up worktrees", "too many worktrees", "worktree sprawl", or any time `git worktree list` shows more than ~10 entries. Operate on whichever repo the user is in (or names). It's a global skill — works on any git repo.

## Step 1: Inventory

Establish the repo and its default branch first — every safety check compares against it.

```bash
git rev-parse --show-toplevel              # confirm we're in a repo
git worktree list --porcelain              # full worktree list
git remote show origin | sed -n 's/.*HEAD branch: //p'   # default branch
```

Default-branch detection: Klever DAC repos use `dev`; most others use `main` or `master`. The `git remote show origin` line is authoritative — use it rather than guessing. If origin is unreachable, fall back to checking which of `dev`/`main`/`master` exists on the remote (`git ls-remote --heads origin`).

Then refresh the merge baseline so "merged" checks are accurate:

```bash
git fetch origin <default-branch>
```

## Step 2: Classify each worktree

For every worktree except the main checkout, assign a class. The main worktree (the primary checkout) is never a removal candidate — skip it.

| Class | Meaning | Default disposition |
|-------|---------|--------------------|
| **merged** | Branch's commits are all in `origin/<default>`, nothing ahead | Safe to remove |
| **gone** | Worktree path no longer exists on disk (stale registration) | Cleaned by `git worktree prune` (no force) |
| **unmerged** | Has commits ahead of `origin/<default>` not yet merged | Keep — needs verification before any removal |
| **active** | Uncommitted or untracked changes present | Keep — would lose work |

## Step 3: Adversarially verify before trusting "merged"

"Merged" by branch name is not proof. Code often ships under a different branch (consolidation, rename, cherry-pick), and a branch can look unmerged when its content already landed. For each removal candidate, gather hard evidence:

```bash
# Commits ahead of the default branch (0 = nothing unique here)
git -C <worktree-path> rev-list --count origin/<default>..HEAD

# Actual diff against the default branch (empty = content already on default)
git -C <worktree-path> diff origin/<default> --stat

# Uncommitted + untracked work (anything here means DO NOT force-remove)
git -C <worktree-path> status --porcelain
```

Resolve the two failure modes explicitly:
- **Looks unmerged but isn't:** ahead-count > 0 but `git diff origin/<default>` is empty → the content already landed (likely via a differently-named branch). Safe to remove.
- **Looks merged but isn't:** branch appears merged but `status --porcelain` shows uncommitted/untracked changes → NOT safe. Untracked content that is *only* `node_modules/` or `.next/` (build artifacts) is safe to force-remove; real source files are not.

When uncertain, keep it. A surviving stale worktree costs disk; a wrongly removed one costs work.

## Step 4: Present the classified table

Show the user one table so they can decide with full context:

```
Repo: <repo>   Default: <branch>   Worktrees: <N>

| Path | Branch | Class | Ahead | Diff | Dirty | Safe? |
|------|--------|-------|-------|------|-------|-------|
| /tmp/KTP-501-foo | KTP-501-foo | merged   | 0 | empty | no  | ✅ remove |
| ~/wt/KTP-510     | KTP-510     | unmerged | 4 | 12 files | no | ⚠️ keep (unmerged) |
| ~/wt/KTP-520     | KTP-520     | active   | 2 | 5 files | yes | ⛔ keep (uncommitted) |
| /tmp/old-scratch | (gone)      | gone     | – | – | – | ✅ prune |
```

## Step 5: Ask what to remove

Use AskUserQuestion. Offer: **merged only** (the conservative default), **all dead** (merged + gone), or **pick individually**. Never default to removing unmerged or active worktrees — those require an explicit, per-item override from the user, with a warning that commits/edits will be lost.

## Step 6: Execute

Always prune stale registrations first (this handles `gone` worktrees with no force needed):

```bash
git worktree prune -v
```

Then remove each approved worktree:

```bash
git worktree remove <path>           # clean worktrees
git worktree remove --force <path>   # only when status was clean OR untracked is build-artifacts only
```

Reserve `--force` for worktrees you verified in Step 3. If `git worktree remove` refuses because of dirty state you didn't expect, STOP and re-show the user — don't reach for `--force` to silence it.

## Step 7: Report

```
Pruned: <N> worktrees (merged: <a>, gone: <b>, user-forced: <c>)
Kept:   <M> (unmerged: <x>, active: <y>)
git worktree list now shows <final-count> entries.
```

## Boundaries

- Never touch the main worktree.
- Never remove an unmerged or active worktree without an explicit per-item user override.
- This skill removes worktrees, not branches. The branch ref survives a worktree removal; deleting branches is a separate, more destructive action — don't bundle it in unless the user asks.
- Pairs with `superpowers:using-git-worktrees` (creation) and `batch-pr-consolidation` (which should ideally clean up its constituent worktrees after shipping).
