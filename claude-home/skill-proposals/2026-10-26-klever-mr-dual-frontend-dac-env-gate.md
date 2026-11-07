# Skill Proposal: klever-mr dual frontend DAC env gate
Date: 2026-10-26
Source: session clear-tern, legacy portal vs klv1ai DAC parity

## Trigger
An MR on dac-gcp-front-klv1ai (804) or dac-gcp-front-portal (514) adds, removes or renames a container env var.

## Scope
org (Klever), extension of the klever-mr skill DAC gate

## Draft Steps
1. Diff the container env name list between the MR branch and the sibling DAC's default branch.
2. If a name exists only in one DAC, ask: does the app treat it as optional (safe default) or required?
3. If required, block until the sibling DAC MR exists or the author records why it is not needed.
4. Remind that a prod image tag bump must be done in both projects' TF_VAR_build_docker_tag_version.

## Addendum 2026-10-27 (portal DAC sync session)
Extend the trigger to the app side. When an `app-front-portal` MR removes a `process.env.X` read, the gate must list every DAC that still sets `X` (804, 514, `dac-gcp-front-demo`) and ask for a removal MR in each one.
Why: the portal stopped reading `MEDIA_PLAN_ATTACH_EXCEL` and `MEDIA_PLAN_SAVE_EVERY_PLAN` in 2.0.96, but klv1ai kept `"false"` in prod for 8 more days. That dead value made the Salesforce feature look off in prod. It was removed in klv1ai !11 on 2026-10-27.
5. Dead-var check: for each env name in either DAC, `git grep` `app-front-portal` `origin/main` and `origin/dev` for a reader. Positive control: grep a var known to be read. Report vars with zero readers as cleanup candidates.
