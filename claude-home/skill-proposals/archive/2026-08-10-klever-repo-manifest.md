# Skill Proposal: klever-repo-manifest
Date: 2026-08-10
Source: session crisp-mole — app-dev-setup harness integration analysis

## Status

Drafted in full during the session, deliberately NOT written to `~/.claude/skills/`.
Gabriel parked the whole app-dev-setup thread. The complete SKILL.md draft is in §6 of
`project-management/reports/harness/app-dev-setup-integration-analysis.md`.

That report was never crit-approved (the crit daemon was killed before producing a review),
so this proposal is unvalidated.

## Trigger

"where is repo X", "what Klever repos exist", "am I missing repos", "clone repo X",
"is my checkout stale", "repo inventory", "find the DAC for Y".

## Scope

Org (Klever). Bay: `ops`.

## Why it is not a clone wrapper

`app-dev-setup/scripts/clone-all.sh` declares ~150 repos in MA's flat `~/repos/app/backend/ms/X`
layout. Gabriel's machine uses the `grp-` mirrored tree. The script's `[ -d "$dest/.git" ]`
idempotency guard is path-based and does not fire across that boundary, so running it against
the local root builds a second full checkout rather than skipping the ~88 existing clones.

The value is the manifest as **inventory and drift detection**, not as a cloner.

## Draft Steps

1. Refresh a shallow copy of `app-dev-setup`, parse `clone_repo` lines into (path, url) pairs.
2. **audit** — translate manifest paths to local `grp-` paths, compare against
   `find ~/Developer/grp-beklever-com -maxdepth 5 -name .git -type d`, report four buckets:
   missing, renamed (from the script's `renamed_repos` tail), untracked, stale (behind origin).
   Write the report to disk; never paste ~150 rows into the conversation.
3. **locate** — grep the manifest, return GitLab URL plus manifest path plus translated local path.
4. **clone** — one repo or a named few, never all. Build the local `grp-` path, skip when
   `.git` exists, then confirm the deploy branch via `/deploy-identity`.
5. Gotchas to encode: stale IAP cookie (refresh via `git -C grp-cfg/cfg-app fetch`), registry
   downtime 23:00 to 05:00 ET (do not retry in a loop), `app-make` missing its `.git` suffix
   at line 117 of the manifest.

## Open question

Two of the three audit buckets overlap with existing skills (`worktree-prune`,
`validate-repo-links`). Confirm this is not a fourth overlapping inventory tool before building it.
