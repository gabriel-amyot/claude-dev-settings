# Pilot state

Goal: build and exercise a local read-only Kev-4B recall prototype in the shared-config repository.

Repository: https://github.com/gabriel-amyot/claude-dev-settings
Tracking: https://github.com/gabriel-amyot/claude-dev-settings/issues/1
Worktree: `/Users/gamyot/.claude-shared-config-worktrees/kev-readonly-pilot`
Branch: `GH-1-kev-readonly-pilot`

## Progress

- Inspected and preserved the dirty canonical shared-config checkout.
- Created an isolated worktree from `1f1f4b8`.
- Completed two independent assumption audits. See REVIEW.md.
- Registered protocol before inference. No live hooks changed.
- Enabled GitHub issues as required for requested tracking. Created the parent issue.
- Cloned pinned Kev into the user cache. `uv sync --locked --extra serve --no-dev --python 3.13` succeeded.
- Local hardware: Apple Silicon arm64, 32 GiB unified memory.

## Work in progress

- Root: bootstrap, experiment runner, reports, issue tracking.
- Retrieval worker: immutable library snapshot, offline baselines, metrics, authored diagnostic fixtures, tests.
- Client worker: authenticated loopback client, local process lifecycle, transport and model-validation tests.

## Boundaries

Source corpus is the canonical shared global library, including its recorded dirty state. The clean worktree does not reproduce uncommitted observatory or library changes. Raw data belongs under the ignored pilot `.local/` directory. Authored fixtures do not establish recall quality. Production remains disabled.
