# Skill Proposal: batch-branch-consolidation
Date: 2026-05-11
Source: KTP-510/582/641 batch merge session

## Trigger
"Consolidate these branches", "batch merge", "combine branches into one MR", or when multiple feature branches are ready but have stale version bumps causing tag collisions.

## Scope
org (Klever, any repo with /klever-mr gates)

## Draft Steps
1. Identify branches to consolidate, verify zero file overlap (or map overlaps)
2. Create consolidated branch from dev
3. `git checkout origin/{branch} -- {files}` for each branch's feature files
4. Handle directory renames (git rm old, checkout new)
5. Version bump + CHANGELOG (find next available tag)
6. Build + type check verification
7. Commit, push, hand off to /klever-mr

## Notes
- Differs from /batch-pr-consolidation (GitHub PRs). This is for GitLab branches pre-MR.
- The checkout-files method only works when feature files are disjoint. If files overlap, fall back to sequential cherry-pick with conflict resolution.
- Could be a sub-mode of /klever-mr rather than a standalone skill.
