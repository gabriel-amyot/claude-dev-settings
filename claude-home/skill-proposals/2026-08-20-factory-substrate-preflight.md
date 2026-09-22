# Skill Proposal: factory-substrate-preflight
Date: 2026-08-20
Source: session swift-shrike — a dark-factory run died mid-`git worktree add` with "No space left on device" after 8 stray project-management worktrees had accumulated to 5.8 GB

## Trigger

Before any `Workflow`-driven factory run (`dark-factory`, `sprint-factory`, `service-factory`), and as a standalone command when a factory run fails with a git checkout error.

## Problem it fixes

Two independent defects that combined into one confusing failure:

1. **The shipped `dark-factory.workflow.js` passes `isolation: 'worktree'` on six `agent()` calls.** When the workflow's cwd is `project-management`, the Workflow tool isolates THAT repo — creating worktrees in a repo whose CLAUDE.md states "NEVER create a worktree here." The pm single-trunk guard hook cannot see Workflow-internal worktrees, so nothing catches it. Runs leave up to 3 behind, each a full copy of a repo carrying a 515 MB `.specstory/` history, plus an orphaned `worktree-wf_*` branch.
2. **No run checks free disk.** The failure surfaces as hundreds of `unable to create file ...: No space left on device` lines followed by `WorktreeIsolationError`, which reads like a git or permissions fault rather than a full volume.

## Scope

Global (the defect is in a global skill), but the disk check is useful for any long agent run.

## Draft Steps

1. `df` the volume holding the target repo. Refuse to start below a threshold (propose 15 GB) with the number in the message, not a vague "low disk".
2. Enumerate `git worktree list` for `project-management`. If any exist: report count and total size, rescue untracked files to `sessions/archive/worktree-rescue-<date>/`, then `git worktree remove --force` + `git worktree prune` + `git branch -D` the `worktree-wf_*` branches. This is the recovery procedure that worked in-session.
3. Refuse (do not warn) if the factory script about to run would isolate `project-management` — grep the resolved script for `isolation: 'worktree'` and compare the workflow cwd against the pm path.
4. Report a one-line verdict: free disk, stray worktrees cleaned, isolation check.

## Upstream fix this proposal does not replace

The real repair is in `~/.claude/skills/dark-factory/dark-factory.workflow.js`: either drop `isolation: 'worktree'` (the in-session run completed fine without it, since the tool belt already tells build/review/QA agents to self-manage a worktree in the TARGET repo) or gate it on the workflow cwd not being `project-management`. The preflight is defense-in-depth, not the cure.

## Related

Same session also found the Workflow tool has no model plumbing for factory agents — a `model` override requires copying the script and wrapping `agent()`. Worth folding into the same dark-factory fix.
