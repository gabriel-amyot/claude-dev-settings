# Skill Proposal: datasophia-rename-orphaning-recovery (likely an UPDATE to klever-repo-rename)

Date: 2026-07-08
Source: KTP-821 AI Insights DAC state recovery + workload rename

## Trigger
After renaming (or discovering a renamed) datasophia FaaS/DAC/app GitLab repo, or when a DAC
`apply` fails `409 Already Exists` or a CF deploy 404s on a source-zip object.

## Scope
org (Klever / datasophia). Best folded into the existing `klever-repo-rename` skill as a
"post-rename consequences + recovery" section, not a new standalone skill.

## Draft Steps
1. State orphaning: renaming a FaaS/DAC repo moves the tf backend to an empty `<new-name>/state`
   prefix (prefix = CI_PROJECT_NAME) → `apply` wants to create existing resources → 409. Recover by
   delete-and-recreate (no important data) or state migration; strip one-time `import{}` blocks.
2. Artifact orphaning: renaming an app repo moves its publish folder in `bkt-atfhst` to the new
   name; the zip filename keeps the old poetry package name. Repoint the DAC `storage_source.object`
   folder prefix (keep filename). Symptom: CF deploy 404 "No such object …/app-<old>/zip/…".
3. IAP git fix: if `git fetch/push` dies with `ConfigGetURLMatch … 'http.cookieFile'/'iap.helperID'`,
   the `includeIf` glob (`https://…`) missed the `https+iap://` remote →
   `git -C <repo> config --local include.path ~/.cicd.prod.datasophia.com.gitconfig`.
4. Verify the plan gate before human apply: `gitlab_skill.py trace <projID> --job <id> --filter "Plan:"`
   / `"will be destroyed"` (full-trace search; resolve by numeric ID until `index` rebuilt).
5. Consumer sweep before renaming workload resources: env-var-driven writers flow through the DAC
   rename automatically; hardcoded readers (Java @Value/String.format literals) + their tests must
   change in lockstep before that consumer deploys.

## Note
42+ proposals already in ~/.claude/skill-proposals/ (backlog). Accumulate; do not auto-create.
