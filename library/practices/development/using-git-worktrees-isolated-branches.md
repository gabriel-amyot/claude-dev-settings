---
name: using-git-worktrees-tombstone
description: Tombstone. The worktree procedure now lives in the owned skill at skills/using-git-worktrees/.
superseded_by: skills/using-git-worktrees/SKILL.md
tombstoned: 2026-09-10
---

# Moved — see `skills/using-git-worktrees/SKILL.md`

The worktree procedure is now an owned skill:

```
~/.claude-shared-config/skills/using-git-worktrees/SKILL.md
```

Invoke it as `using-git-worktrees`. Git rules beyond worktrees live in the `git` skill.

## Why this file is a stub

This path held a 213-line copy of the procedure while the superpowers plugin cache held
its own 218-line copy. Nobody owned either, and they drifted. The copy that lived here
carried a weaker gitignore check: a repo-local, exact-anchored `grep` of `.gitignore`
instead of `git check-ignore`.

The `grep` form reports "not ignored" for a directory that is ignored globally, or
ignored by any pattern written differently (no trailing slash, or a parent-directory
rule). Following it led to a redundant `.gitignore` entry at best and a wrong safety
verdict at worst. The owned skill carries the `git check-ignore` form.

The stub stays rather than being deleted, because `library/practices/INDEX.md` and old
session transcripts point here.

`harness/no-vendored-worktree-skill` asserts this file stays a stub, that the owned skill
keeps the `git check-ignore` form, and that nothing references the plugin cache copy.
