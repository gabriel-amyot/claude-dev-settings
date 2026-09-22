# Deploy-Identity Registry

Maps a deployed artifact back to the **branch/commit that actually runs**, so the harness can
catch the failure mode behind KTP-688: reasoning about deployed code while reading the wrong branch.

**Why a harness-side registry instead of a committed `.deploy-identity.yaml` per repo?**
The original design (KTP-688 converged doc) put this file inside each code repo. Two reasons it
lives here instead:
1. The KTP-688 build was scope-guarded out of touching the `app-agent-hub` code repo.
2. A file committed *in* a repo can only be read once you have the right branch checked out — the
   exact thing that fails when you're sitting on the wrong branch. A harness-side fact is
   branch-independent, which is the whole point.

The probe (`~/.claude/skills/deploy-identity/probe.sh`) reads this registry FIRST, then falls back
to a repo-local `.deploy-identity.yaml` if one exists (so a repo can still self-describe later).

## File naming

One flat file per repo, keyed by the repo's directory basename:
`~/.claude/deploy-identity/<repo-basename>.yaml`

e.g. `app-agent-hub.yaml` for
`~/Developer/grp-beklever-com/grp-app/grp-backend/grp-gcp/grp-models/app-agent-hub`.

## Schema (flat key: value — no nesting, keep the parser trivial)

```yaml
repo_path: <absolute path to the repo, for disambiguation>
deploy_branch: <branch that deploys to the live env; space-separated if more than one>
default_branch: <repo default / origin/HEAD short name>   # the TRAP is default_branch != deploy_branch
owner: <CODEOWNERS-style owner; used by post-comment external-claim gate>
artifact_source: <live | cache>      # live = resolve the running artifact; cache = trust deployed_sha below
deployed_tag: <last-known deployed artifact string; a -SNAPSHOT- suffix is a WP-13 roll-lag cue>
deployed_sha: <last-known deployed commit SHA; used as fallback when live resolution is unreachable>
live_resolve_note: <free text: how to resolve the live artifact when infra is reachable>
ci_unconfirmed: <true | false>       # true => treat like a SNAPSHOT (provenance not CI-confirmed)
```

Only `deploy_branch` is strictly required. The richer the entry, the stronger the probe.

## How the probe uses it

```
read registry entry → deploy_branch, deployed_sha, deployed_tag, owner
resolve current HEAD branch of the repo
if artifact_source == live and reachable: resolve running artifact -> SHA
else: use deployed_sha (cache)
git branch -r --contains <SHA>                → which branch(es) actually contain deployed code
compare HEAD-branch vs deploy_branch:
   reading the deploy branch + sha contained   → status VERIFIED, confidence HIGH allowed
   reading a different branch                   → status MISMATCH, confidence capped to HYPOTHESIS
   sha unresolved and containment unknown       → status CANT_VERIFY, confidence CANT_VERIFY
```

Confidence is an **OUTPUT of the probe**, never a self-rating. See the `deploy-identity` skill.
