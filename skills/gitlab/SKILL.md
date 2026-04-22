---
name: gitlab
description: "Access and query GitLab repositories (Klever, Supervisr.AI, Origin8). List groups, projects, clone repos, manage merge requests, read CI/CD pipelines and logs, manage pipeline variables. Klever CI/CD runs on GitLab CI exclusively. Supervisr app repos are on GitHub (use gh CLI for those). Input: --org <org> + command. Returns: repo lists, MR details, pipeline logs."
---

# GitLab Skill

## AGENT CONTRACT — READ THIS FIRST

**`--org` is optional.** The skill auto-detects your org from `$PWD` — same longest-prefix approach as the jira and gcloud skills. Working inside `~/Developer/grp-beklever-com/` resolves to `klever`. Working inside `~/Developer/supervisr-ai/` resolves to `supervisrai`. Falls back to `default_org` in config only when no path matches. Override explicitly with `--org <name>` when running from a neutral directory (e.g. project-management root).

| Ticket prefix | Org flag | GitLab instance |
|---|---|---|
| KTP, INS | `--org klever` | cicd.prod.datasophia.com (IAP-protected) |
| SPV, PER | `--org supervisrai` | gitlab.prod.origin8cares.com |
| Origin8 infra | `--org origin8` | gitlab.prod.origin8cares.com |

**IAP is self-healing.** If the Klever cookie expires, the skill auto-runs `git fetch` on the configured refresh repo before failing. No manual intervention needed.

**Natural name resolution.** For `pipeline`/`vars`/`pipelines`/`jobs` commands, project names resolve via a local index. If resolution fails, pass the numeric project ID instead (always reliable).

**Klever key project IDs** (use when natural names don't resolve yet):

| Project | ID |
|---|---|
| app-proximity-report | 577 |
| app-user-management | 569 |
| app-front-portal | see index |
| app-proximity-explorer | see index |

Run `--org klever index` once to build the full Klever index for name resolution.

---

## Commands

```
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org <ORG> <COMMAND> [args]
```

**Available commands**:
- `list-groups [--full]` — List all groups
- `list-repos [--group GROUP_ID] [--all] [--full]` — List projects in a group
- `get-repo ID_OR_PATH [--full]` — Get single repository details
- `clone [--group GROUP_ID] [--repos REPO1,REPO2] [--output DIR]` — Clone repositories
- `mr [--project PROJECT_ID] [--action create|list|approve] [--title TITLE] [--source SOURCE] [--target TARGET] [--mr-iid IID]` — Manage merge requests
- `search QUERY [--max N]` — Search repositories
- `pipelines PROJECT [--ref BRANCH] [--status STATUS] [--count N]` — List recent pipelines
- `jobs PROJECT --pipeline ID [--logs]` — Get jobs for a pipeline
- `trace PROJECT --job ID [--filter KEYWORD]` — Get raw job trace

> ⚠️ **CAUTION:** `pipeline` (singular) TRIGGERS a new pipeline. `pipelines` (plural) LISTS existing ones. To check status, use `pipelines` or `jobs --pipeline ID`. Never use `pipeline` to check status.

- `pipeline PROJECT [--ref BRANCH] [--var KEY=VALUE ...]` — Trigger CI/CD pipeline (dev by default, prod blocked)
- `vars PROJECT [--action list|get|set] [--key KEY] [--value VALUE] [--scope ENV]` — Manage CI/CD variables
- `deploy-watch PROJECT --pipeline ID [--interval SECONDS]` — Watch deployment pipeline (3-stage)
- `play-job PROJECT --job JOB_ID` — Trigger a manual/blocked job (requires user confirmation)
- `index [--group GROUP_ID]` — Build/rebuild the local project index

---

## Pipeline Log Analysis

**Two-step workflow — summary first, full log only if needed:**

1. **Download** full job trace:
```bash
python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_download.py <dac-name> --job <job-id> [--env dev]
```
Output: `{dac_repo}/gitlab-ci/{env}/execution_{image_tag}_{job_id}.log`

2. **Summarize**:
```bash
python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py <log-file-path>
```
Output: `_summary.yaml` next to the log. Read this first (~30 lines).

**Chained usage:**
```bash
python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_download.py lead-lifecycle --job 56102 | xargs python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py
```

**Known Error Patterns:**

| Pattern | Meaning | Action |
|---------|---------|--------|
| `Error: Error acquiring the state lock` | Stale tflock from timed-out job | Force-unlock or wait |
| `[ ERROR ] Run manual deploy` | Destroy detected, auto-deploy blocked | Use "apply manually" job |
| `Error 412: At least one of the pre-conditions` | State lock contention | Retry or force-unlock |
| `stuck_or_timeout_failure` | Job exceeded time limit | Re-trigger, check if lock left behind |

---

## Project Index

The skill maintains `dac_index.json` — a per-org cache of project names → IDs.

- **Auto-builds on first use** when `index_groups` is set in config
- **Per-org**: `--org klever index` builds Klever's index without touching Supervisr's
- **Rebuild on demand** when new projects are added
- **Gitignored** — local to each developer

---

## Supervisr Examples

```bash
# List recent pipelines for EQS DAC
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py pipelines eqs

# Watch a deployment
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py deploy-watch lead-lifecycle --pipeline 21872

# Update image tag and trigger deploy
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py vars "lead-lifecycle" --action set --key TF_VAR_image_tag --value 0.0.4-dev --scope dev
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py pipeline "lead-lifecycle" --ref dev
```

> **Safety:** Pipelines on `main`, `master`, `prod`, `production` are blocked.
> **Safety:** `play-job` always requires explicit user confirmation.

---

## Klever Examples

```bash
# List repos in backend microservices group
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever list-repos --group 154

# List recent pipelines for proximity-report
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever pipelines 577

# List open MRs on proximity-report
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr --project 577 --action list

# Create MR
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr --project 577 --action create --title "KTP-XXX: description" --source feature-branch --target dev

# Build name index (run once, then use natural names)
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever index
```

---

## Configuration Management

```bash
# View all configured orgs
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py list

# Configure token for an org
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure klever

# Add a new org
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py add ORGNAME URL LOCAL_PATH GITLAB_GROUP
```

Config file: `~/.claude-shared-config/skills/gitlab/gitlab_config.json`
Tokens: macOS Keychain under service `claude-gitlab`

**Per-org config keys:**
- `gitlab_url` — GitLab instance URL
- `local_path` — local root for cloning
- `gitlab_group` — top-level group path
- `index_groups` — group IDs to index for name resolution
- `iap_refresh_repo` — (Klever only) git repo path used for IAP cookie auto-refresh
