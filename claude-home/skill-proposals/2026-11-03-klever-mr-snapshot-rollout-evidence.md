# Skill Proposal: Extend klever-mr snapshot rollout evidence
Date: 2026-11-03
Source: KTP-1216 Taco Chain pilot DEV snapshot execution; this Codex conversation
Status: proposed; not installed

## Trigger
A user requests a Klever feature snapshot in DEV, particularly under a demo deadline, and the reviewed branch, built image and deployed artifact can differ.

## Scope
Klever org; extend the existing `~/.claude-shared-config/skills/klever-mr/SKILL.md` and its deployment-identity companion. Do not create a competing deployment orchestrator or change production/live-write authority.

## Draft Steps
1. Reconcile the current app/DAC CI route, environment, exact reviewed source, explicit deployment authority and existing reservations. Persist reservations through an absolute path and abort on any reservation failure before mutation. Reuse the installed GitLab/IAP tooling. Keep current DEV routing distinct from legacy PROD routing.
2. Before another build, inspect runner contention along the ready deployment path. If reprioritizing, reserve and cancel only the coordinator's identified lower-priority work; separately reconcile any detached Cloud Build.
3. Record distinct source-review, build/scan/release, DAC plan/review and apply results. Require nonempty configuration identity/cwd for validation; do not promote an empty-directory or formatting success into a Terraform validation PASS.
4. Use the owning startup implementation to check the exact actual container image, whitelisted nonsecret configuration/secret presence, listening port, new backend health and stable/reached MIG target. Restore only owned tunnels whose VM hop was replaced.
5. Emit a timestamped receipt linking expected source/image to actual runtime and deployment jobs. List newer reviewed-but-undeployed fixes separately; report browser/vendor/Slack acceptance as unrun until its own evidence passes. Preserve false-default sends and all operation budgets.

## Evidence
Library capture: `documentation/bibliotheque/inbox/2026-11-03-taco-pilot-dev-snapshot-execution.md` in Klever project-management. Exact runtime and independent review receipts are linked there. This proposal contains no credentials and does not authorize deployment or live sends.
