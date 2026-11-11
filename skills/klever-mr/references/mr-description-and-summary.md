# klever-mr MR description, creation calls and summary templates

## Step 2: Extract MR components

Five components. All five are mandatory regardless of repo type.

**Ticket ID:** from branch name (e.g., `KTP-499` from `KTP-499-atomic-permissions`).

**WHY:** read the commit messages to extract the problem or motivation:
```bash
git log --reverse --format="%B" origin/dev..HEAD
```
Synthesize a 1-2 sentence WHY from the commit bodies. The WHY answers: what problem existed, or what was asked for. If commit bodies are empty (subject-only commits), synthesize the WHY from the subjects and the changed files. Describe the problem, not the solution.

**WHAT:** a 1-2 sentence summary of the outcome. Describe the user/system impact, not a file list.

**Commits block:**
```bash
git log --reverse --format="### %s%n%n%b" origin/dev..HEAD
```

**Test plan:** infer from commits and changed files (e.g., "unit tests pass", "terraform plan reviewed", "manual testing via Postman"). If unsure, ask the user.

## Step 3: Project ID and manual URL

Repo name: last path segment of `git remote get-url origin`, before `.git`.

MR title: `{TICKET-ID}: {short what — imperative}`, from the first commit subject or synthesized.

Automatic mode: resolve the numeric GitLab project ID. If search returns several results, pick the one whose `path` matches exactly.
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever search "{repo-name}"
```

Manual mode URL:
```
https://cicd.prod.datasophia.com/{group}/{project}/-/merge_requests/new?merge_request[source_branch]={branch}&merge_request[target_branch]=dev
```

## Step 4: Description template

If the repo has `.gitlab/merge_request_templates/Default.md`, use its structure as the skeleton. Fill in each section. Strip HTML comments (`<!-- ... -->`) and replace them with actual content. If there is no template, use:

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

STE lint detail: score = violations per 100 words. Revise obvious hits in the Why/What prose: hedges, marketing adjectives, phrasal verbs, run-ons, nominalizations. Design: `docs/specs/2026-07-30-ste-anti-slop-design.md`.

## Step 5: GitLab calls

Create:
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr \
  --project {project_id} \
  --action create \
  --title "{MR title}" \
  --source {branch} \
  --target dev \
  --description-file {repo_root}/.mr-description.md
```

MR already exists: `--action list`, find the MR for the source branch, then `--action update --mr-iid {iid} --description-file .mr-description.md`. Do not create a duplicate.

Auto-merge (only if `/klever-mr --auto-merge` was invoked):
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr \
  --project {project_id} \
  --action auto-merge \
  --mr-iid {iid}
```
If auto-merge fails (pipeline not yet started, approvals required), report but do not block. The MR is still created.

Direct merge fallback (auto-merge not available, or the user requests immediate merge):
```bash
uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr \
  --project {project_id} --action merge --mr-iid {iid}
```
Report the merge state from the JSON output (`merged`, `state` fields).

## Summary templates

Automatic mode:
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

Manual mode:
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
