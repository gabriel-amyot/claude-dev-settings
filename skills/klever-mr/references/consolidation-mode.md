# klever-mr Multi-Branch Consolidation (`/klever-mr consolidate`, pre-MR mode)

Use it when several finished feature branches need to ship as one MR. Common cause: multiple branches each bumped the version independently, so merging them sequentially causes tag collisions. Consolidating onto one branch with a single version bump avoids that.

This mode runs BEFORE the normal MR flow. It produces one consolidated branch, then falls through to the standard gates and MR creation.

1. **Identify branches** to consolidate. Verify the feature files are disjoint (no two branches touch the same file). Map any overlaps.
2. **Create the consolidated branch** from `origin/dev`: `git checkout origin/dev -b {TICKET-ID}-consolidated` (or a descriptive name covering the set).
3. **Pull each branch's feature files** with `git checkout origin/{branch} -- {files}`. For directory renames, `git rm` the old path and check out the new one.
4. **Single version bump + CHANGELOG** covering all consolidated work. Find the next available tag (Gate 4). Bump once, not once per branch.
5. **Build + type-check** to verify the combined set compiles.
6. **Commit**, then fall through to the standard MR Creation flow.

**Disjoint-files only.** The `git checkout origin/{branch} -- {files}` method works only when feature files do not overlap. If files overlap, fall back to sequential `git cherry-pick` with conflict resolution. This mode differs from the GitHub-oriented `/batch-pr-consolidation`. This one is for GitLab feature branches pre-MR.
