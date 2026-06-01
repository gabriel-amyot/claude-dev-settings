---
name: klever-mr
description: Create Klever GitLab merge requests with mandatory pre-flight gates. Handles all Klever repo types: Java backend (pom.xml), Node frontend (package.json), and infrastructure/terraform/DAC repos (no version file). Enforces version bump + CHANGELOG for app repos, skips those gates for infra repos. Always produces WHY + WHAT sections in the MR description. Use this skill whenever the user wants to create an MR, merge request, or PR on any Klever repo. Also use when the user says "push to dev", "ready to merge", "create MR", "open merge request", "ship this branch", "merge this to dev", or finishes a feature branch. Klever repos only (GitLab behind IAP).
nav:
  bay: ship
  when: "Create Klever GitLab MRs. Enforces version bump, changelog, dev sync."
  when_not: "GitHub PRs (use gh CLI). Supervisr shipping (use supervisr-ship agent)."
  org: [klever]
---

# Klever Merge Request Skill

Create merge requests on Klever GitLab repos with enforced quality gates. App repos get version bump and changelog enforcement. Infra/DAC repos skip those gates. Every MR gets a WHY, a WHAT, and a sync check.

## Why This Exists

Two problems this skill prevents:

1. **Tag collision on app repos.** CI tags Docker images from the version in code. Two branches merging with the same version = second pipeline fails. Forgetting the version bump or changelog has happened repeatedly.
2. **Empty MR descriptions on any repo.** MR descriptions without WHY and WHAT are useless for reviewers. The skill synthesizes both from commit history so every MR ships with context.

## Repo Types

Klever has three repo types. The skill detects which one it's in and adjusts gate behavior accordingly.

| Type | Detection | Version gate | Changelog gate |
|------|-----------|-------------|----------------|
| **Java backend** | `pom.xml` at repo root | Required | Required |
| **Node frontend** | `package.json` at repo root | Required | Required |
| **Infra/DAC/terraform** | Neither file exists | Skipped | Skipped |

Infra repos (paths containing `grp-dac`, `grp-cfg`, or repos with `.tf` files) have no versioned artifacts. Their pipelines run terraform, not Docker builds. Version bump and changelog gates do not apply.

## Pre-Flight Gates

Run these gates in order. Gates are **check-and-fix**, not blockers.

**Self-resolving failures** (behind dev, uncommitted changes, missing version bump, missing changelog entry): fix them automatically, report what you did, continue. Never ask "should I fix this?" The answer is always yes.

**Structural failures** (wrong branch type, no repo detected): report and stop. These indicate work started wrong.

### Gate 1: Repo Detection and Type Classification

```bash
git rev-parse --show-toplevel
```

Must be a git repo under `~/Developer/grp-beklever-com/`.

Classify the repo type by checking for version files:
- `pom.xml` exists → **Java backend**
- `package.json` exists → **Node frontend**
- Neither exists → **Infra/DAC**

Store the repo type. Gates 4 and 5 use it to decide whether to run or skip.

### Gate 2: Branch Check

```bash
git branch --show-current
```

Must be on a feature branch (not `dev`, `main`, or `master`). Extract ticket ID from branch name (pattern: `KTP-XXX-*` or `INS-XXX-*`).

If on dev/main/master, FAIL: "You're on a protected branch. Create a feature branch first."

### Gate 3: Sync with origin/dev

```bash
git fetch origin
git log HEAD..origin/dev --oneline
```

If there are commits on origin/dev not in the local branch:
- **Auto-resolve:** Run `git merge origin/dev`. Report: "Merged N commits from origin/dev."
- If merge conflicts arise, STOP and let the user resolve them.

Also check for uncommitted changes:
```bash
git status --porcelain
```
If dirty:
- **Auto-resolve:** Stage and commit with message `{TICKET-ID}: uncommitted work before MR`. Report what was committed.
- Exception: if dirty files look unrelated to the ticket, STOP and ask.

### Gate 4: Version Bump (app repos only)

**Skip condition:** If repo type is **Infra/DAC**, skip this gate entirely. Report: "Gate skipped: version bump (infra/terraform repo, no versioned artifact)."

For app repos, read the version from the local branch's version file, then from origin/dev:

```bash
# pom.xml:
git show origin/dev:pom.xml | grep -m1 '<version>' | sed 's/.*<version>\(.*\)<\/version>.*/\1/'

# package.json:
git show origin/dev:package.json | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])"
```

Local version MUST be strictly greater than origin/dev's version (patch increment minimum).

Also check for tag collision:
```bash
git tag --list "v*" | grep -F "<local-version>"
git tag --list | grep -F "<local-version>"
```

If versions are equal:
- **Auto-resolve:** Increment patch (X.Y.Z → X.Y.Z+1). For package.json, also run `npm install --package-lock-only`. Report: "Bumped version X.Y.Z → X.Y.Z+1."

If tag already exists:
- **Auto-resolve:** Find next available patch version, bump to that. Report: "Tag X.Y.Z exists, bumped to X.Y.N."

### Gate 5: CHANGELOG.md (app repos only)

**Skip condition:** If repo type is **Infra/DAC**, skip this gate entirely. Report: "Gate skipped: CHANGELOG (infra/terraform repo)."

For app repos, read `CHANGELOG.md` at repo root. Verify it contains an entry matching the local version:

```
## [X.Y.Z] - YYYY-MM-DD
```

The date should be today or recent (within 7 days). The entry must have content (at least one bullet under a category like Added/Changed/Fixed).

If no CHANGELOG.md exists, STOP: "No CHANGELOG.md found at repo root."

If no entry for current version:
- **Auto-resolve:** Add a `## [X.Y.Z] - YYYY-MM-DD` section with entries from `git log --reverse --format="- %s" origin/dev..HEAD`. Report: "Added CHANGELOG entry for X.Y.Z."

If entry is empty:
- **Auto-resolve:** Populate from commit subjects. Report what was added.

## Modes

`/klever-mr` supports two modes:

| Invocation | Mode | Behavior |
|---|---|---|
| `/klever-mr` | **Automatic** (default) | Creates MR via GitLab API, posts description. No merge action. Pass `--auto-merge` to enable merge-when-pipeline-succeeds. |
| `/klever-mr manual` | **Manual** (legacy) | Generates URL + description file for copy-paste into the GitLab web UI |

Both modes run identical pre-flight gates and generate the same MR description. They differ only in Steps 3 and 5.

## Multi-Branch Consolidation (pre-MR mode)

Invoke with `/klever-mr consolidate` when several finished feature branches need to ship as one MR. Common cause: multiple branches each bumped the version independently, so merging them sequentially causes tag collisions. Consolidating onto one branch with a single version bump avoids that.

This mode runs BEFORE the normal MR flow. It produces one consolidated branch, then falls through to the standard gates and MR creation.

1. **Identify branches** to consolidate. Verify the feature files are disjoint (no two branches touch the same file). Map any overlaps.
2. **Create the consolidated branch** from `origin/dev`: `git checkout origin/dev -b {TICKET-ID}-consolidated` (or a descriptive name covering the set).
3. **Pull each branch's feature files** with `git checkout origin/{branch} -- {files}`. For directory renames, `git rm` the old path and check out the new one.
4. **Single version bump + CHANGELOG** covering all consolidated work. Find the next available tag (see Gate 4) — bump once, not once per branch.
5. **Build + type-check** to verify the combined set compiles.
6. **Commit**, then fall through to the standard MR Creation flow below.

**Disjoint-files only.** The `git checkout origin/{branch} -- {files}` method works only when feature files don't overlap. If files overlap, fall back to sequential `git cherry-pick` with conflict resolution. This mode differs from the GitHub-oriented `/batch-pr-consolidation`; this is for GitLab feature branches pre-MR.

## MR Creation

All applicable gates passed. Now generate the MR.

### Step 1: Push the branch

```bash
git push -u origin HEAD
```

If push fails, report the error and stop.

### Step 2: Extract MR components

This step produces five components. All five are mandatory regardless of repo type.

**Ticket ID**: from branch name (e.g., `KTP-499` from `KTP-499-atomic-permissions`)

**WHY**: Read the commit messages to extract the problem/motivation:
```bash
git log --reverse --format="%B" origin/dev..HEAD
```
Synthesize a 1-2 sentence WHY from the commit bodies. The WHY answers: what problem existed, or what was asked for. If commit bodies are empty (subject-only commits), synthesize the WHY from the subjects and the changed files. Describe the problem, not the solution.

**WHAT**: Synthesize a 1-2 sentence summary of the outcome. Describe the user/system impact, not a file list.

**Commits block**: Generate the formatted commit log:
```bash
git log --reverse --format="### %s%n%n%b" origin/dev..HEAD
```

**Test plan**: Infer from commits and changed files (e.g., "unit tests pass", "terraform plan reviewed", "manual testing via Postman"). If unsure, ask the user.

### Step 3: Resolve project and construct MR title

Extract repo name from git remote:
```bash
git remote get-url origin
```
Parse the repo name (last path segment before `.git`).

Construct the MR title: `{TICKET-ID}: {short what — imperative}` (from the first commit subject, or synthesized).

**Automatic mode only:** Resolve the GitLab project ID:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever search "{repo-name}"
```
Extract the numeric `id` from the result. If search returns multiple results, pick the one whose `path` matches exactly.

**Manual mode only:** Construct the MR URL:
```
https://cicd.prod.datasophia.com/{group}/{project}/-/merge_requests/new?merge_request[source_branch]={branch}&merge_request[target_branch]=dev
```

Target branch is always `dev` unless the user says otherwise.

### Step 4: Render the MR description

The MR description always contains these five sections in this order: **Why**, **What**, **Tickets**, **Commits**, **Test plan**. This is true whether the repo has a template or not.

**If the repo has `.gitlab/merge_request_templates/Default.md`:** Read it, use its structure as the skeleton. Fill in each section with the extracted components. Strip HTML comments (`<!-- ... -->`), replace with actual content.

**If the repo has no template**, use this structure:

```
## Why

{synthesized WHY — 1-2 sentences: what problem existed, what was asked}

## What

{synthesized WHAT — 1-2 sentences: outcome for user/system}

## Tickets

- [TICKET-ID](https://beklever.atlassian.net/browse/TICKET-ID)

## Commits

{git log --reverse --format="### %s%n%n%b" output}

## Test plan

- [ ] {verification items}
```

### Step 5: Create MR and present summary

Write the full MR description to `.mr-description.md` in the repo root. This file is ephemeral, not committed. If `.gitignore` doesn't already contain `.mr-description.md`, add it.

#### Automatic mode (default)

Create the MR via the GitLab API:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr \
  --project {project_id} \
  --action create \
  --title "{MR title}" \
  --source {branch} \
  --target dev \
  --description-file {repo_root}/.mr-description.md
```

If creation fails (e.g., MR already exists), try updating the existing MR's description instead:
1. List open MRs: `--action list`, find the one matching the source branch
2. Update it: `--action update --mr-iid {iid} --description-file .mr-description.md`

**Auto-merge (opt-in, requires `--auto-merge` flag):**

Only if `/klever-mr --auto-merge` was invoked:
1. Enable merge-when-pipeline-succeeds:
   ```bash
   python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr \
     --project {project_id} \
     --action auto-merge \
     --mr-iid {iid}
   ```
   If auto-merge fails (e.g., pipeline not yet started, approvals required), report but do not block. The MR is still created.

2. **Direct merge fallback:** If auto-merge is not available (feature disabled, no approvals configured, or user requests immediate merge), merge the MR directly:
   ```bash
   python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr \
     --project {project_id} --action merge --mr-iid {iid}
   ```
   Report the merge state from the JSON output (`merged`, `state` fields).

**Default behavior (no `--auto-merge`):**
MR is created and reported. No merge action taken. Human reviews and merges via GitLab UI.

Present this summary:

```
---
KLEVER MR CREATED

MR: !{iid}
{bare web_url on its own line}

{For app repos only:}
Version: {old} -> {new}

{For infra repos only:}
Gates skipped: Version bump (N/A, infra repo), CHANGELOG (N/A, infra repo)

Why: {one-line preview}
What: {one-line preview}
Auto-merge: {enabled | not set (reason)}

Description posted. Nothing to copy-paste.
```

#### Manual mode (legacy fallback)

Present this summary:

```
---
KLEVER MR READY (manual)

URL:
{bare URL on its own line — no markdown, no brackets, no backticks}

{For app repos only:}
Version: {old} -> {new}

{For infra repos only:}
Gates skipped: Version bump (N/A, infra repo), CHANGELOG (N/A, infra repo)

Why: {one-line preview}
What: {one-line preview}

MR description written to: {absolute path to .mr-description.md}

Open the URL above, then copy-paste the file contents into the MR description field.
```

The URL MUST be a bare string on its own line so the terminal auto-links it. Never wrap it in backticks, markdown link syntax, angle brackets, or code blocks.

## Deploy to Dev (automatic mode with `--auto-merge` only, app repos only)

This section only runs when `--auto-merge` was passed. Without it, the MR is created but not merged, so deploy steps are skipped.

After setting auto-merge, the skill continues with deployment to dev. This is **dev only**, never demo.dev, uat, or prod. Infra/DAC repos and manual mode skip this section entirely.

### DAC Routing Table

| App repo | DAC repo | Version variable | DAC scope |
|---|---|---|---|
| `app-front-portal` | `dac-gcp-front-portal` | `build_docker_tag_version` | `dev` |
| `app-proximity-report` | `dac-gcp-back-proxrp` | `cpe_cos_version` | `dev` |
| `app-user-management` | `dac-gcp-back-usrmgt` | `cpe_cos_version` | `dev` |
| `app-proximity-explorer` | `dac-gcp-back-proexp` | `cpe_cos_version` | `dev` |

If the app repo is not in this table, skip deploy. Report: "No DAC mapping for this repo. Deploy manually."

### Step 6: Wait for MR to merge

Poll the MR status until merged (max 10 minutes, 30s interval):
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr \
  --project {app_project_id} --action list
```
Check if the MR iid is no longer in the open list (means merged or closed). If the MR has auto-merge enabled, it will merge when the source branch pipeline succeeds. If no auto-merge, merge directly (see "Direct merge fallback" in Step 5).

### Step 7: Wait for dev branch app pipeline

Poll the dev branch pipeline until it reaches a terminal state (max 15 minutes, 30s interval):
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever pipelines \
  {app_project_id} --ref dev --count 1
```

Terminal states for app pipelines:
- **`"success"`**: all jobs completed. Proceed.
- **`"manual"`**: all automatic jobs completed, but the pipeline has a downstream bridge job (`bd-configure-dac`) awaiting manual trigger or already triggered. **Treat as build complete.** The `bd-configure-dac` bridge job auto-triggers the DAC pipeline. Proceed to Step 8.
- **`"failed"`**: STOP and report the failure. Do not proceed to DAC.

Report: "App pipeline {status} ({pipeline_url})"

### Step 8: Find and trigger the deploy-in-dev bridge job

The app pipeline contains bridge/trigger jobs that are invisible in the regular `/jobs` endpoint. Use the `bridges` command to find them:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever bridges \
  {app_project_id} --pipeline {app_pipeline_id}
```

Parse the JSON output. Look for a bridge named `deploy-in-dev` or `bd-configure-dac`. Check its status:
- **`"manual"`**: the bridge needs to be triggered. Use `play-job`:
  ```bash
  python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever play-job \
    {app_project_id} --job {bridge_job_id}
  ```
- **`"success"`** or **`"running"`**: the bridge already fired. Read the `downstream_pipeline` field from the bridge output to get the DAC pipeline ID directly.
- **`"failed"`**: STOP and report the bridge failure.

If the bridge output includes a `downstream_pipeline` ID, use it directly instead of searching DAC pipelines by timestamp. If not available, fall back to checking the DAC project's recent pipelines:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever pipelines \
  {dac_project_name} --ref dev --count 3
```
Look for a pipeline with source `"pipeline"` (bridge-triggered) created within the last few minutes.

If no DAC pipeline appears within 5 minutes after the app pipeline completes, report: "No DAC pipeline auto-triggered. Check bridge job status in the app pipeline." and STOP.

### Step 9: Monitor DAC pipeline manual gates

DAC pipelines have **two manual gate jobs**: a **plan** job and an **apply** job.

Poll the DAC pipeline jobs:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever jobs \
  {dac_project_name} --pipeline {dac_pipeline_id}
```

**Plan job (agents MAY trigger):** Find the plan job (usually named `deploy-in-dev` or similar with stage `deploy`). If it is in `"manual"` status, trigger it:
```bash
python3 ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever play-job \
  {dac_project_name} --job {plan_job_id}
```

Wait for the plan job to complete (max 10 minutes). Once it finishes, download and summarize the trace:
```bash
python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_download.py {dac_project_name} \
  --job {plan_job_id} --env dev
```
Then summarize:
```bash
python3 ~/.claude-shared-config/skills/gitlab/pipeline_trace_summarize.py {log_file_path}
```

Read the summary YAML. Parse the terraform plan output looking for:
- **Resources to create** (count)
- **Resources to modify/update** (count)
- **Resources to destroy** (count)

**Apply job (agents MUST NEVER trigger):** The apply job is human-only. Agents must never trigger it, regardless of the plan contents. Present the plan summary and let the human decide.

### Step 10: Report and hand off to human

Present the terraform plan report:

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

**Agents never trigger the apply job.** Report the plan summary and stop. The human reviews the plan and triggers apply manually in GitLab.

## Edge Cases

- **Multiple version files**: If both pom.xml and package.json exist, bump both. Verify both match.
- **Frontend package-lock.json**: After bumping package.json, run `npm install --package-lock-only` and include the lockfile change in the commit.
- **Auto-resolved fixes need committing**: If any gate auto-resolved, commit fixes with `{TICKET-ID}: pre-MR housekeeping (version bump, changelog)` before pushing.
- **Branch has no ticket ID**: Use the branch name as-is. Warn the user that external posts should reference a Jira key.
- **Stale branch (already merged)**: STOP. Create a fresh branch from dev.
- **API MR creation fails**: Fall back to manual mode automatically. Report: "API creation failed ({reason}), falling back to manual mode."
- **MR already exists for branch**: Find the existing MR by listing open MRs, update its description via `--action update`. Do not create a duplicate.
- **DAC pipeline fails on plan**: Report the error from the trace summary. Do not retry automatically (could be a state lock or registry outage).
- **Nightly shutdown (after 20:00 EDT)**: Dev environment goes down nightly. If deploy happens during this window, the deploy will succeed but the service won't serve traffic until morning. Note this in the report if the current time is after 20:00 EDT.

## What This Skill Does NOT Do

- Does not deploy to demo.dev, uat, or prod (dev only)
- Does not trigger the DAC apply job (human-only gate)
- Does not manually update DAC version variables (handled by `bd-configure-dac` bridge)
- Does not manually trigger DAC pipelines (auto-triggered by app pipeline bridge)
- Does not push to dev/main directly
- Does not retry failed DAC pipelines (report and stop)
