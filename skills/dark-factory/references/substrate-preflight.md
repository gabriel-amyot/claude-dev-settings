# Substrate preflight (0.10.6)

Two defects made one confusing failure. A dark-factory run died in `git worktree add` with hundreds of
`No space left on device` lines and a `WorktreeIsolationError`. Eight stray project-management worktrees
held 5.8 GB (2026-08-20). An earlier sweep found 20 of them (2026-06-16).

## What the workflow does now

| Input (Workflow `args`) | Effect |
|---|---|
| `cwd` = the directory the Workflow tool runs from | Runtime `isolation: 'worktree'` is used only when `cwd` is set and is not project-management. Otherwise each code agent creates its own worktree in the target repo and removes it before it returns. |
| `free_disk_gb` = free GB on the target-repo volume | Below the floor the run returns `HALT_SUBSTRATE` before the Concierge. No Retro runs. |
| `min_free_gb` (optional, default 15) | The floor. |
| `pm_worktrees` (optional) | The count of stray project-management worktrees. It is reported, never cleaned. |

A missing `free_disk_gb` does not halt. The run logs that the disk was not checked. Pass the numbers.

## Main-loop steps before the Workflow call

1. Measure the volume that holds the TARGET code repo, not project-management:
   `df -g <target repo>`. Use the `Avail` column as `free_disk_gb`.
2. Pass `cwd` as the directory the Workflow tool runs from (usually project-management).
3. Count stray project-management worktrees: `git -C <project-management> worktree list`, minus one
   for the main checkout. Pass the count as `pm_worktrees`.

For a headless launch, `scripts/headless_launch_guard.py preflight --repo <target repo>` prints a
`workflow_args` block with `cwd` and `free_disk_gb` for you.

## Stray-worktree cleanup (manual, human-approved only)

The preflight never deletes anything. Cleanup is destructive. Ask Gabriel first, then for each stray
project-management worktree:

1. Rescue untracked and modified files to
   `project-management/sessions/archive/worktree-rescue-<date>/<worktree name>/`.
2. Compare the rescued tree against `main` and keep anything not on `main`.
3. `git -C <project-management> worktree remove <path>`. Use `--force` only after step 1 and 2.
4. `git -C <project-management> worktree prune`.
5. Delete each orphaned `worktree-wf_*` branch only after you confirm its commits are on `main` or rescued.

Free disk for other reasons through the `disk-management` skill.

## Guard

`tests/substrate-scope.test.mjs` (cases S0-S13, W1-W4). It fails on 0.10.5, which still carried six
hard-coded isolation options.
