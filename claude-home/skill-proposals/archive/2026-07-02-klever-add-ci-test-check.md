# Skill Proposal: klever-add-ci-test-check
Date: 2026-07-02
Source: KTP-688 — added a non-blocking pytest job to app-agent-hub CI

## Trigger
"add a CI test check", "run tests on the MR", "surface test results without blocking merges" on a Klever GitLab repo.

## Scope
org (Klever GitLab repos behind IAP)

## Draft Steps
1. Read the repo's `.gitlab-ci.yml` `workflow` rules FIRST. If `merge_request_event` is `when: never` (app-agent-hub does this), a MR-event job never runs — the check must run on the **branch pipeline** (push); GitLab surfaces it on the MR.
2. Add a `test` stage + a job that inherits the global `image:` from the shared select-executor template (no `extends` needed) and sets `tags: [faas]` for the runner.
3. Detect the dep manager: `uv`-locked repo → `pip install uv && uv sync --frozen && uv run pytest`; poetry → the poetry template. Match the repo's Dockerfile.
4. Make it non-blocking with `allow_failure: true`; confirm the project's "Pipelines must succeed" setting is OFF (that, not the job, is what gates merges).
5. Verify only the test job runs on a feature branch (build/deploy jobs stay gated), push, and confirm the branch pipeline picks up on a `faas` runner.

## Notes
Pairs with the fresh-clone IAP workaround (`git -c include.path=$HOME/.cicd.prod.datasophia.com.gitconfig clone ...`) when reading shared CI templates from other include repos.
