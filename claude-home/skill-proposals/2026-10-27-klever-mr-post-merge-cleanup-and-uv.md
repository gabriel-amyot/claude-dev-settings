# Skill Proposal: klever-mr post-merge cleanup + uv invocation (update to existing klever-mr)
Date: 2026-10-27
Source: KTP-1358. Gabriel: "delete worktrees asap, that should be automatic after a MR is merged". Also klever-mr's gitlab_skill calls failed on this Mac.

## Trigger
klever-mr detects its MR as merged (Step 6 poll, or a later `/klever-mr status`), or the user says "it's merged".

## Scope
org (Klever), update to `~/.claude/skills/klever-mr/SKILL.md`

## Draft Steps
1. Invoke the gitlab skill as `uv run --quiet --with requests python ~/.claude-shared-config/skills/gitlab/gitlab_skill.py ...` (plain python3 lacks `requests` on Gabriel's Mac). If config is missing, point to `gitlab_config_setup.py configure klever --op-item <1Password item>`.
2. On merge: find the squash commit on origin/dev (`Merge branch '<branch>' into 'dev'` parent). Prove `git diff --stat <branch-HEAD> <squash-commit>` is empty.
3. `git worktree remove <worktree>` (no --force; stop and ask if git refuses because of untracked, non-ignored files), `git branch -D <branch>`, `git worktree prune`.
4. Confirm the remote branch is gone (`git ls-remote --heads`); GitLab usually deletes it.
5. Remove /tmp review clones for the ticket after looking at any `*.bak` files. Report what was removed.
