# Revert a merged change and isolate the work for review

Use this when a change already merged to `dev` on a Klever app repo (Java, Node,
Python) turns out to be unsafe, and the work must come back later as a reviewed MR.
Example: the KTP-1289 media-api Boot 4 revert.

**Invocation: manual only.** Every step below mutates a shared branch or opens an MR.
Start only on an explicit user request ("revert that MR", "back this out"). Merge only
on explicit approval. For a DAC repo, the DAC page in the bibliothèque owns the
procedure: `stack/dac-cos-mig-deployment-conventions.md`, section "Revert an
Accidental DAC Merge".

## Rules that do not bend

- Never rewrite history. A revert is a new commit. No `reset --hard`, no force push.
- The version goes **forward**, never back. A lower version collides with the release
  tag that already exists.
- Version bump, CHANGELOG and MR gates belong to `/klever-mr`. Do not hand-roll them.
- Do not restore a whole tree (`git checkout <pre-merge> -- .`). It erases every
  unrelated commit merged after the bad change.

## 1. Revert on a fresh branch

```bash
git fetch origin
# worktree from origin/dev (using-git-worktrees), branch {TICKET}-revert-<what>
git rev-list --parents -n 1 <sha>     # 3 ids = merge commit, 2 ids = squash/single commit
git revert -m 1 --no-edit <merge-sha> # merge commit: -m 1 keeps the dev side
git revert --no-edit <squash-sha>     # squash or single commit: no -m
```

Several merges: revert newest first. Unpushed local revert commits may fold into one
`{TICKET}: revert <what>` commit. Never fold a pushed commit.

## 2. Metadata through klever-mr

Keep the CHANGELOG from `origin/dev` and add a "Reverted" entry. Bump the version
forward (patch). `/klever-mr` enforces both gates.

## 3. Prove the revert is change-specific

```bash
python3 ~/.claude-shared-config/skills/git/scripts/revert_check.py \
  --base origin/dev --reverted <sha> [--reverted <sha2>] \
  --allow pom.xml --allow CHANGELOG.md
```

| Exit | Meaning | Action |
|---|---|---|
| 0 | Reverted paths restored. Other work kept. | Continue. |
| 1 | A reverted path is not restored, or a path outside the change moved. | Fix before you push. |
| 2 | A later commit also changed a reverted path. | Decide each REVIEW line by hand, then tell the user. |

Do not use "`git diff <pre-merge> HEAD` is empty" as the check. A correct revert fails
it (the version moved forward), and a revert that drops unrelated work can pass it.

## 4. Ship the revert

Push without `[skip ci]`. Wait for the branch test job on the exact commit. Create the
MR through `/klever-mr`. Merge only on explicit approval.

## 5. Re-open the work as a Draft MR

Branch from the merged revert tip and **revert the revert**:

```bash
git revert --no-edit <revert-commit-sha>
```

Do not re-merge the old feature branch. Git treats its commits as already merged, so
the changes do not come back. Bump the minor version, keep the CHANGELOG, push, and
open the MR as `Draft:` with a regression checklist for the code owner.

## 6. Disarm deploy traps

- Close any open release MR (for example `dev` to `main`) that still carries the
  reverted code.
- A cancelled pipeline does not cancel its manual DAC apply jobs. Note any stale
  manual apply job in the MR, and let the next dev pipeline move the DAC version
  variable. Do not play an old apply job.
