# Pilot state

Current status (2026-11-13): archived for now at Gabriel's request. The native study completed on 2026-10-31; quality remains `INSUFFICIENT_EVIDENCE`. See [the archive](results/2026-11-13-archive.md) and [final aggregate evidence](results/final-native-evidence.json). The progress notes below are historical and do not indicate a running study. Independent evaluation and harness-health implementation are parked, with no automatic restart.

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

## Prelaunch evidence and publication

- The implementation and independent review fixes pass 53 offline tests.
- A real pinned tokenizer bounded 57 corpus packets to at most 7,584 state tokens.
- The frozen corpus has 57 documents, 60 files, and 55 in-scope alias rows. Nine other alias targets are explicitly excluded.
- A detached study is running at `.local/studies/20261031T150227.051702Z` in the execution worktree. It is waiting for the pinned base-weight download, then runs tests, starts MLX offline, executes probes and measurements, and stops its exact model instance.
- Quality remains `INSUFFICIENT_EVIDENCE`. There is no live integration.
- Publication worktree: `/Users/gamyot/.claude-shared-config-worktrees/kev-pilot-review`, branch `GH-1-kev-pilot-review`.
- Publication contains only pilot changes on `origin/main`. Three pre-existing local commits remain on the original branches and are not pushed as part of this pilot.

## Native deployment observed

- The pinned adapter and base download completed with file hashes.
- Actual metadata: MLX, mps, bfloat16, temperature 2.406050072164233, truncation disabled.
- Native authentication: missing and wrong keys return 401. The valid key returns 200.
- Fifteen authored probe requests completed. Seventeen expected semantic outcomes matched. Choice probabilities varied by up to 0.0981 across six option orders. These are diagnostic observations, not calibration or security guarantees.
- The benchmark is still running. `results/provisional-native-evidence.json` is timestamped partial evidence, not a final report.
- Native deployment exposed a macOS launcher identity change. The corrected ownership comparison preserves PID, birth time, exact Kev arguments, and raw legacy receipts. The live process was not restarted. Fifty-seven offline tests pass after the fix.

## Boundaries

Source corpus is the canonical shared global library, including its recorded dirty state. The clean worktree does not reproduce uncommitted observatory or library changes. Raw data belongs under the ignored pilot `.local/` directory. Authored fixtures do not establish recall quality. Production remains disabled.
