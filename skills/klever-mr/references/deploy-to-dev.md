# klever-mr Deploy to Dev, Steps 6 to 10 (detail)

Runs only with `--auto-merge`, automatic mode, app repos. Dev only, never demo.dev, uat or prod. All `gitlab` skill calls run under `uv run --quiet`.

## Step 6: Wait for MR to merge

Poll until merged (max 10 minutes, 30s interval):
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr \
  --project {app_project_id} --action list
```
The MR iid gone from the open list means merged or closed. With auto-merge enabled, it merges when the source branch pipeline succeeds. Without auto-merge, merge directly (direct merge fallback in `mr-description-and-summary.md`).

## Step 7: Wait for dev branch app pipeline

Poll until terminal (max 15 minutes, 30s interval):
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever pipelines \
  {app_project_id} --ref dev --count 1
```

- **`"success"`:** all jobs completed. Proceed.
- **`"manual"`:** all automatic jobs completed, and a downstream bridge job (`bd-configure-dac`) waits for a manual trigger or already fired. **Treat as build complete.** The `bd-configure-dac` bridge auto-triggers the DAC pipeline. Proceed to Step 8.
- **`"failed"`:** STOP and report. Do not proceed to DAC.

Report: "App pipeline {status} ({pipeline_url})"

## Step 8: Find and trigger the deploy-in-dev bridge job

Bridge jobs are invisible in the regular `/jobs` endpoint. Use `bridges`:
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever bridges \
  {app_project_id} --pipeline {app_pipeline_id}
```

Find the bridge named `deploy-in-dev` or `bd-configure-dac`:
- **`"manual"`:** trigger it:
  ```bash
  uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever play-job \
    {app_project_id} --job {bridge_job_id}
  ```
- **`"success"`** or **`"running"`:** already fired. Read `downstream_pipeline` for the DAC pipeline ID.
- **`"failed"`:** STOP and report the bridge failure.

If no `downstream_pipeline` ID, check the DAC project's recent pipelines and pick the one with source `"pipeline"` (bridge-triggered) created within the last few minutes:
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever pipelines \
  {dac_project_name} --ref dev --count 3
```

No DAC pipeline within 5 minutes after the app pipeline completes: report "No DAC pipeline auto-triggered. Check bridge job status in the app pipeline." and STOP.

## Step 9: Monitor DAC pipeline manual gates

DAC pipelines have two manual gate jobs: **plan** and **apply**.
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever jobs \
  {dac_project_name} --pipeline {dac_pipeline_id}
```

**Plan job (agents MAY trigger):** usually `deploy-in-dev` or similar, stage `deploy`. If `"manual"`:
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever play-job \
  {dac_project_name} --job {plan_job_id}
```
Wait for it (max 10 minutes). Then download and summarize the trace:
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/pipeline_trace_download.py {dac_project_name} \
  --job {plan_job_id} --env dev
uv run --quiet ~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py {log_file_path}
```
From the summary YAML, count resources to create, to modify/update and to destroy.

**Apply job (agents MUST NEVER trigger):** human-only, regardless of the plan contents.

DAC plan fails: report the error from the trace summary. Do not retry automatically (state lock or registry outage).

## Step 10: Report template

```
---
DEPLOY TO DEV

App pipeline: {status} ({app_pipeline_url})
DAC pipeline: {dac_pipeline_url} (auto-triggered by bd-configure-dac)

Terraform Plan:
  + {N} to create
  ~ {M} to modify
  - {D} to destroy

{If D == 0:}
No destroys. Safe to apply.

{If D > 0:}
TERRAFORM DESTROY DETECTED
{D} resource(s) will be DESTROYED. Review the plan carefully before applying.
Resources to be destroyed:
{list each destroyed resource name from the plan}

Apply job: {apply_job_id} (HUMAN ONLY — agent must not trigger)
To apply: run manually in GitLab or confirm and Gabriel will trigger it.
```

Nightly shutdown (after 20:00 EDT): dev goes down nightly. The deploy succeeds but the service does not serve traffic until morning. Note this in the report if the current time is after 20:00 EDT.
