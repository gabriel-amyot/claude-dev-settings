# Skill Proposal: klever-cfg-app-onboard-repo
Date: 2026-07-03
Source: steady-jackal — KTP-735 app-media-plan cfg-app onboarding

## Trigger
A Klever app repo's pipeline fails at `bc-release-version` with "HTTP Basic: Access denied", or a new/ad-hoc GitLab repo needs CI/CD tokens and a DAC deployment link. Phrases: "onboard repo to cfg-app", "PROJECT_ACCESS_TOKEN missing", "wire app X to its DAC".

## Scope
Org (Klever).

## Draft Steps
1. Verify current state: is the project already in `grp_backend_gcp_models.tf` (or sibling group file)? `git log -S` cfg-app origin/main; check project created_at vs commit date to distinguish terraform-created from ad-hoc.
2. Backup: snapshot project settings via GitLab API to `tickets/{ID}/data/backups/` (vars need Maintainer; record 403s explicitly).
3. Worktree off cfg-app origin/main; add the missing entries among the 4 touchpoints (models map / access-token map / multi-project-pipeline map / import.tf downstream map). Sync token expirations with a sibling repo so they rotate together.
4. `terraform fmt -check`, commit (why+what), push, MR via /klever-mr (infra repo, target main).
5. Verify via CI: read the MR pipeline's `init-validate-plan` trace; require create-only plan (N add / 0 change / 0 destroy) before telling Gabriel it's mergeable. Apply (`apply in noe`) is human-only.
