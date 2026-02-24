---
name: gitlab
description: Access and query GitLab repositories. List groups, projects, clone repos, and manage merge requests across your GitLab instance. Supports multiple organizations with secure token storage.
---

# GitLab Skill

## Overview

Multi-organization GitLab management with secure macOS Keychain token storage. Configure credentials for multiple organizations (klever, origin8, supervisrai) and work seamlessly across them.

## Initial Setup

### 1. Configure Your Organizations

First-time setup of GitLab credentials for your organizations:

```bash
# Configure token for each organization (you'll be prompted for your token)
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure klever
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure origin8
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure supervisrai

# Set default organization (optional)
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py default supervisrai

# List all configured organizations
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py list
```

### 2. Token Storage

Tokens are stored securely in **macOS Keychain** under the service `claude-gitlab`. You can safely forget about them after initial configuration.

## Usage

### Skill Commands

**Progressive data discovery**: Use the `--full` flag when you need complete details to avoid wasting tokens.

**Available commands**:
- `list-groups [--full]` - List all groups and subgroups
- `list-repos [--group GROUP_ID] [--all] [--full]` - List projects in a group
- `get-repo ID_OR_PATH [--full]` - Get single repository details
- `clone [--group GROUP_ID] [--repos REPO1,REPO2] [--output DIR]` - Clone repositories with intelligent path structure
- `mr [--project PROJECT_ID] [--action create|list|approve] [--title TITLE] [--source SOURCE] [--target TARGET]` - Manage merge requests
- `search QUERY [--max N]` - Search repositories by name or description
- `pipeline DAC_NAME [--ref BRANCH] [--var KEY=VALUE ...]` - Trigger CI/CD pipeline (dev by default, prod blocked)
- `vars DAC_NAME [--action list|get|set] [--key KEY] [--value VALUE] [--scope ENV]` - Manage CI/CD variables
- `index [--group GROUP_ID]` - Build/rebuild the local project index from GitLab API

### Pipeline Log Analysis

**Two-step workflow — summary first, full log only if needed:**

1. **Download** full job trace to a local file:
```bash
python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_download.py <dac-name> --job <job-id> [--env dev]
```
Output: saves cleaned trace to `{dac_repo}/gitlab-ci/{env}/execution_{image_tag}_{job_id}.log` and prints the path.

2. **Summarize** the downloaded trace:
```bash
python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py <log-file-path>
```
Output: writes `_summary.yaml` next to the log file and prints the path.

3. **Read the `_summary.yaml` first** (~30 lines). Only drill into the full `.log` if the summary doesn't explain the failure.

**Chained usage:**
```bash
python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_download.py lead-lifecycle --job 56102 | xargs python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py
```

**Error pattern mapping is INCOMPLETE.** When encountering a new failure mode:
1. Diagnose from full log
2. Add pattern to `ERROR_PATTERNS` in `pipeline_trace_summarize.py`
3. Update the Known Error Patterns table in this skill doc

**Known Error Patterns:**

| Pattern | Meaning | Action |
|---------|---------|--------|
| `Error: Error acquiring the state lock` | Stale tflock from timed-out job | Force-unlock or wait |
| `[ ERROR ] Run manual deploy` | Destroy detected, auto-deploy blocked | Use "apply manually" job |
| `Error 412: At least one of the pre-conditions` | State lock contention | Retry or force-unlock |
| `stuck_or_timeout_failure` | Job exceeded time limit | Re-trigger, check if lock left behind |

**Note:** The `trace` command on `gitlab_skill.py` remains available for quick interactive inspection. These scripts are the durable, file-based workflow for deeper analysis.

**Project Index & Auto-Resolution**: The skill maintains a cached index (`dac_index.json`) that maps natural names to GitLab project IDs. This index:
- **Auto-builds on first use** — if no index exists, it fetches all projects from the configured `index_groups` in `gitlab_config.json`
- **Persists across sessions** — no re-indexing needed, just a JSON file read
- **Rebuilds on demand** — run `index` command when you add new projects
- **Gitignored** — each user builds their own index; the skill is shareable

For `pipeline` and `vars` commands, use natural names:
- `eqs` → dac-sprvsr-core-eqs (ID: 224)
- `lead-lifecycle` or `lead lifecycle` → dac-sprvsr-core-lead-lifecycle (ID: 235)
- `retell-service` or `retell service` → dac-sprvsr-core-retell-service (ID: 227)
- `compliance-engine` → dac-sprvsr-core-compliance-engine (ID: 226)
- And all other projects in indexed groups

**Organization Selection**:
- Default: Uses the `default_org` setting from configuration
- Explicit: Use `--org ORGNAME` flag with any command

### Configuration Management

```bash
# Manage credentials
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py configure ORGNAME

# View all configurations
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py list

# Set default organization
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py default ORGNAME

# Add new organization
python3 ~/.claude-shared-config/skills/gitlab/gitlab_config_setup.py add ORGNAME URL LOCAL_PATH GITLAB_GROUP
```

## Examples

### Working with Default Organization

List all groups (uses default organization):
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-groups
```

List all repos under f-r-r-s group:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py list-repos --group f-r-r-s --full
```

Clone all repos from f-r-r-s group (uses organization's configured local path):
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s
```

Clone selected repos only:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py clone --group f-r-r-s --repos repo1,repo2,repo3
```

### Working with Specific Organization

Clone repos from Klever organization:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever clone --group klever-group
```

List repos in Origin8 organization:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org origin8 list-repos --group origin8-group --full
```

Get repository details from Supervisr organization:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org supervisrai get-repo project-path/repo-name --full
```

### Merge Request Management

Create a merge request:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py mr --project 123 --action create --title "Fix bug" --source feature-branch --target main
```

List merge requests for a project:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py mr --project 123 --action list
```

Approve a merge request:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py mr --project 123 --action approve --mr-iid 45
```

### Search

Search for repositories:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py search "api" --max 20
```

### Pipeline Trigger

Trigger a pipeline on dev (default) using natural DAC names:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py pipeline eqs
```

Trigger on a specific branch:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py pipeline "lead-lifecycle" --ref feature-branch
```

Trigger with CI/CD variables:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py pipeline "retell service" --var TF_VAR_image_tag=v1.2.3 --var DEPLOY_ENV=staging
```

> **Safety:** Pipelines on `main`, `master`, `prod`, and `production` are blocked. Use the GitLab UI for production deployments.

### CI/CD Variables

List all variables for a DAC:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py vars eqs --action list
```

Get a specific variable (optionally scoped):
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py vars "lead-lifecycle" --action get --key TF_VAR_image_tag --scope dev
```

Set/update a variable (creates if missing, updates if exists):
```bash
# Update image tag for lead-lifecycle to 0.0.4-dev
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py vars "lead-lifecycle" --action set --key TF_VAR_image_tag --value 0.0.4-dev --scope dev
```

**Workflow Example - Deploy lead-lifecycle 0.0.4-dev:**
```bash
# 1. Update the image tag variable
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py vars "lead-lifecycle" --action set --key TF_VAR_image_tag --value 0.0.4-dev --scope dev

# 2. Trigger the dev pipeline
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py pipeline "lead-lifecycle" --ref dev
```
