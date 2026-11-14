---
name: gitlab
description: "Access and query GitLab repositories (Klever, Supervisr.AI, Origin8). List groups, projects, clone repos, manage merge requests, read CI/CD pipelines and logs, manage pipeline variables. Klever CI/CD runs on GitLab CI exclusively. Supervisr app repos are on GitHub (use gh CLI for those). Input: --org <org> + command. Returns: repo lists, MR details, pipeline logs."
nav:
  bay: ops
  when: "Access GitLab repos. List groups, projects, MRs, CI/CD pipelines, logs."
  when_not: "Creating a Klever MR (use /klever-mr). Jira operations (use /jira)."
---

# GitLab Skill

## AGENT CONTRACT — READ THIS FIRST

**`--org` is optional.** The skill auto-detects your org from `$PWD` — same longest-prefix approach as the jira and gcloud skills. Working inside `~/Developer/grp-beklever-com/` resolves to `klever`. Working inside `~/Developer/supervisr-ai/` resolves to `supervisrai`. Falls back to `default_org` in config only when no path matches. Override explicitly with `--org <name>` when running from a neutral directory (e.g. project-management root).

| Ticket prefix | Org flag | GitLab instance |
|---|---|---|
| KTP, KTT, INS | `--org klever` | cicd.prod.datasophia.com (IAP-protected) |
| SPV, PER | `--org supervisrai` | gitlab.prod.origin8cares.com |
| Origin8 infra | `--org origin8` | gitlab.prod.origin8cares.com |

**IAP is self-healing.** If the Klever cookie expires, the skill auto-runs `git fetch` on the configured refresh repo before failing. No manual intervention needed.

**Natural name resolution.** ALL commands that take a project accept names or numeric IDs. Names resolve via a local index (`mr`, `get-repo`, `pipelines`, `jobs`, `trace`, `pipeline`, `vars`, `deploy-watch`, `play-job`). If resolution fails, pass the numeric project ID instead (always reliable).

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
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org <ORG> <COMMAND> [args]
```

Always use `uv run`, never plain `python3`. The script declares `requests` inline (PEP 723), and the default `python3` can lack it (`ModuleNotFoundError: No module named 'requests'`). Do not `import gitlab_skill` in a one-liner. Use `api` instead. `--help` (also `mr --help`) prints the real command list.

**Available commands**:
- `list-groups [--full]` — List all groups
- `list-repos [--group GROUP_ID] [--all] [--full]` — List projects in a group
- `get-repo ID_OR_PATH [--full]` — Get single repository details (`--full` includes `default_branch` and `empty_repo`; check `empty_repo` before you treat a no-files clone as a failure)
- `clone [--group GROUP_ID] [--repos REPO1,REPO2] [--output DIR]` — Clone repositories
- `mr --project P --action create|list|approve|merge|auto-merge|update [--title T] [--source S] [--target T] [--mr-iid IID] [--description D | --description-file F]` — Manage merge requests. For a Klever MR, create through `/klever-mr`. `merge`/`auto-merge` into `main`/`uat` on a `grp-dac` project is blocked (human-only `--allow-dac-promotion`).
- `mr-diff`, `mr-note`, `mr-note-edit`, `mr-note-reply`, `mr-note-delete` — MR review reads and comments (comments go through `/post-comment`)
- `search QUERY [--max N]` — Search repositories by name or alias (e.g. `biag`, `proexp`)
- `recent [--limit N] [--match SUBSTR]` — Newest projects first, with `created_at`, `default_branch`, `empty_repo`
- `api ENDPOINT [--param K=V ...] [--all-pages]` — Read-only GET to any `/api/v4` path (e.g. `api projects/577/merge_requests/12`). No write verb exists. Exits 1 on error.
- `pipelines PROJECT [--ref BRANCH] [--status STATUS] [--count N]` — List recent pipelines
- `jobs PROJECT --pipeline ID [--logs]` — Get jobs for a pipeline
- `trace PROJECT --job ID [--filter KEYWORD] [--full] [--tail N]` — Get raw job trace

> ⚠️ **Traces are capped by default.** `trace` shows the first 500 lines (100 for `--filter`). When it cuts, the output now ends with an explicit `... TRUNCATED: showing X of Y` marker — do not report on a trace whose output carries that line. A terraform plan is ~1000 lines and puts `Plan: N to add, M to change, D to destroy` near the **end**, so a default read can miss a destroy. Every trace read surfaces a `summary` field with those counts when the job is a plan. For the whole log use `--full` (writes a temp file, returns the path) or `--tail N`.

> ⚠️ **CAUTION:** `pipeline` (singular) TRIGGERS a new pipeline. `pipelines` (plural) LISTS existing ones. To check status, use `pipelines` or `jobs --pipeline ID`. Never use `pipeline` to check status.

- `pipeline PROJECT [--ref BRANCH] [--var KEY=VALUE ...]` — Trigger CI/CD pipeline (dev by default, prod blocked)
- `vars PROJECT [--action list|get|set] [--key KEY] [--value VALUE] [--scope ENV]` — Read CI/CD variables (secret values hidden). `set` is refused for Klever in every scope; elsewhere it only updates an existing key in a dev scope, never creates one. A CI/CD variable is not a value path: non-secret → DAC Terraform per-environment map, secret → GCP Secret Manager.
- `deploy-watch PROJECT --pipeline ID [--interval SECONDS]` — Watch deployment pipeline (3-stage)
- `play-job PROJECT --job JOB_ID` — Trigger a manual/blocked job (requires user confirmation)
- `index [--group GROUP_ID]` — Build/rebuild the local project index

---

## Pipeline Log Analysis

**Two-step workflow — summary first, full log only if needed:**

1. **Download** full job trace:
```bash
uv run ~/.claude-shared-config/skills/gitlab/pipeline_trace_download.py <dac-name> --job <job-id> [--env dev]
```
Output: `{dac_repo}/gitlab-ci/{env}/execution_{image_tag}_{job_id}.log`

2. **Summarize**:
```bash
uv run ~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py <log-file-path>
```
Output: `_summary.yaml` next to the log. Read this first (~30 lines).

**Chained usage:**
```bash
uv run ~/.claude-shared-config/skills/gitlab/pipeline_trace_download.py lead-lifecycle --job 56102 | xargs uv run ~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py
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
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py pipelines eqs

# Watch a deployment
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py deploy-watch lead-lifecycle --pipeline 21872

# Supervisr legacy only: update an EXISTING dev image-tag key, then trigger deploy (refused for Klever)
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py vars "lead-lifecycle" --action set --key TF_VAR_image_tag --value 0.0.4-dev --scope dev
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py pipeline "lead-lifecycle" --ref dev
```

> **Safety:** Pipelines on `main`, `master`, `prod`, `production`, `uat` are blocked.
> **Safety:** CI/CD variable writes: refused for Klever in every scope; elsewhere refused without `--scope`, on `*` and prod/uat/main/master scopes, and for a key that does not exist yet. Raw `api_request` POST/PUT/DELETE on any `/variables` endpoint is refused. `list`/`get` hide masked and secret-named values.
> **Safety:** API requests retry at most 2 times on server errors (5xx). Never retries on client errors (4xx) or auth redirects.
> **Safety:** `play-job` always requires explicit user confirmation.

---

## Klever Examples

```bash
# List repos in backend microservices group
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever list-repos --group 154

# List recent pipelines for proximity-report
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever pipelines 577

# List open MRs on proximity-report
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr --project 577 --action list

# Create MR
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr --project 577 --action create --title "KTP-XXX: description" --source feature-branch --target dev

# Build name index (run once, then use natural names)
uv run ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever index
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
- `iap_refresh_repo` — git repo path used for IAP cookie auto-refresh (configured for all orgs)
- `strip_prefixes` — list of prefixes to strip when building short aliases (e.g., `["app-", "dac-"]`)
