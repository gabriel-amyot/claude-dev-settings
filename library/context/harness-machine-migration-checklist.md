# Harness Machine Migration Checklist

Cross-org procedure to move the Claude Code harness to a new Mac. It was proposed as the skill
`harness-machine-migration` (2026-10-20) and kept as a library page in the 2026-11-06 triage. A
migration is rare, so a skill would go stale between uses. Run it only on an explicit request. It
touches credentials and the Keychain.

Org-specific steps (credential values, VPN or IAP access, repo hosting) live in each org's
bibliotheque, not here. Load the org module after step 3.

---

## 1. Audit before you change anything

Write the result to a plan file in `~/.claude/plans/` with resume steps. A migration spans
sessions and restarts.

- Username change: if the old and new home folders differ, add a `/Users/<old> -> /Users/<new>`
  symlink so that tracked configs with absolute paths still resolve.
- `~/.claude` symlinks and the state of `bootstrap.sh`.
- Plugins **enabled** in `settings.json` against plugins **installed** (`claude plugin list`).
- Tools on `PATH` that skills call.
- Keychain entries that skills read (for example `claude-jira`, `claude-gitlab`).
- Gitignored skill configs that `bootstrap.sh` does not restore (for example
  `skills/gitlab/gitlab_config.json`). A tracked config (for example `skills/jira/jira_config.json`)
  comes with the repo. Only its Keychain token is missing.
- The git helpers and the global git config.

## 2. Harness

1. Run `bootstrap.sh`.
2. Merge `settings.json`. A local `false` plugin value wins. Never enable a plugin again from the
   repo file without asking (see the plugin rule in the user memory).
3. `enabledPlugins` installs nothing. Run `claude plugin install <name>@<marketplace>` for each
   plugin that is enabled but missing. A plugin that is in no marketplace fails to install. Report
   it. Do not invent a marketplace entry.
4. Machine-local files such as `.claude/settings.local.json` stay uncommitted. If a `git stash pop`
   conflicts on that file, keep the union of both top-level keys and validate with `jq -e .`.

## 3. Credentials

Two paths:

- **The old machine is available:** move the credentials as one bundle without printing any
  value to a terminal or transcript. Copy, verify on the new machine, then delete the bundle on
  both machines.
- **The old machine is not available:** create new tokens. Store each one in the Keychain
  directly. Never paste a token into chat.

Then load the org module for the active org.

## 4. Repositories

Build a clone manifest from the workspace map (`~/.claude/library/context/workspace-map.yaml`).
Create the group folders and any compatibility symlinks. Clone each repo to its workspace-map path,
never to `/tmp`.

## 5. Project-management repos

Commit local work first. Merge, never rebase. Resolve conflicts with Read and Edit. Push only the
approved commit range when other sessions committed on top. Then run each org's ledger check (for
example `ledger --org <org> validate`).

## 6. Verify

- `claude plugin list` matches the enabled set, and `/reload-plugins` shows no new load error.
- Each skill that needs a credential answers one read-only call.
- Each repo fetches.
- The hooks in `settings.json` fire (run one prompt and check the hook output).
