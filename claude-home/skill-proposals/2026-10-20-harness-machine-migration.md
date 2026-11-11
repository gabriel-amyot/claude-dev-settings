# Skill Proposal: harness-machine-migration
Date: 2026-10-20
Source: new-Mac migration session (plan `~/.claude/plans/2026-09-23-machine-migration-plan.md`)

## Trigger
"new machine", "migrate my harness", "set up Claude on the new Mac", "I got a new laptop", "my old Mac is back, move my credentials".

## Scope
global (cross-org harness setup), with a Klever credential module.

## Draft Steps
1. Audit: username delta (add an `/Users/<old> -> /Users/<new>` symlink), `~/.claude` symlinks, `bootstrap.sh` state, plugins **enabled vs installed** (`claude plugin list`), tools on PATH, Keychain entries (`claude-jira`, `claude-gitlab`), gitignored configs (`gitlab_config.json`), IAP helper and git config. Write a plan file to `~/.claude/plans/` with resume steps.
2. Harness: run bootstrap, merge `settings.json` (local `false` plugin values win; never re-enable from the repo file), then `claude plugin install` every enabled-but-missing plugin.
3. Credentials: two paths. With the old Mac: generate the "bundle without printing secrets" prompt (inbox 2026-10-20 nugget #11). Without it: new Jira/GitLab tokens, plus IAP values from Datasophia and the adohkan helper (nugget #4).
4. Repos: build the clone manifest, create group folders and compat symlinks. If there is no IAP: run the zip-snapshot workflow with `.download-origin`, and relink later (nuggets #2, #3).
5. Sync project-management: commit local work, merge (never rebase), resolve with Read/Edit (nugget #1), push only the approved range (nugget #9), run `ledger validate`.
