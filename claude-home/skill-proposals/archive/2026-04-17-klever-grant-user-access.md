# Skill Proposal: klever-grant-user-access
Date: 2026-04-17
Source: Session investigating how to give a new user deploy access to Klever GCP/GitLab

## Trigger
User needs to give a new developer access to Klever GCP projects or GitLab repos. Phrases like "add user to Klever", "give deploy access", "onboard new dev", "why can't X access the project".

## Scope
org (klever)

## Current State
Today we default to "ask Marc-André" because:
- `grp-org-developer@{domain}` membership is managed in Google Admin Console, not IAC
- GitLab membership is managed manually via web UI
- No self-serve path exists

## Draft Steps (if/when to build this skill)
1. Ask: what level of access? (GCP only, GitLab only, both)
2. Ask: which projects/repos specifically? (or all = `grp-org-developer`)
3. For GCP: draft a Jira task for Marc-André with exact group name and user email
4. For GitLab: draft a message (Slack) to Marc-André with repo path and desired role (Developer/Maintainer)
5. If a `cmm-hlpdsk` IAC PR path ever becomes available, wire into that instead

## Future hook
If `iac-gws-org-groups` ever gets user membership management (a `members` block in `group_cloud_identity_res.tf`), this skill should generate the terraform diff and create an MR.

## Related knowledge
~/.claude/library/context/klever-infra-access.md
