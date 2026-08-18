---
name: pre-crawl-repo-prep
description: "Prepare repos for overnight crawl or autonomous agent session. Reads REPO_MAPPING.yaml, stashes dirty state, checks out dev/main, pulls origin. Trigger: 'prep repos for crawl', 'clean repos', 'get ready for overnight'. Klever org. Input: REPO_MAPPING.yaml path or repo list. Returns: status table per repo."
nav:
  bay: ops
  when: "Prepare repos for overnight crawl. Stash dirty state, checkout dev/main, pull."
  when_not: "Already on clean branches. Non-crawl work."
  org: [klever]
---

# Pre-Crawl Repo Prep

Ensures all target repos are clean, on the correct branch, and up to date before an autonomous session.

## Steps

### 1. Identify Target Repos

Read `REPO_MAPPING.yaml` from the current ticket folder. Expected format:

```yaml
repos:
  frontend:
    path: ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal
    branch: dev
  backend:
    path: ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-proximity-report
    branch: dev
```

If no REPO_MAPPING.yaml exists, accept repo paths as arguments.

### 2. Process Each Repo

For each repo, run these commands **sequentially** (never pipe git commands):

**a. Check status:**
```bash
cd <repo_path>
git status --porcelain
```

**b. If dirty (output is non-empty):**
```bash
git stash push -m "pre-crawl stash $(date +%Y%m%d-%H%M)"
```
Record the stash ref for the report.

**c. Determine default branch:**
- Use the `branch` field from REPO_MAPPING.yaml if present
- Otherwise: `git branch -r | grep HEAD` to detect
- DAC repos always use `dev`

**d. Switch to default branch:**
```bash
git checkout <default_branch>
```

**e. Pull latest:**
```bash
git fetch origin
```
Then:
```bash
git pull origin <default_branch>
```

**f. Verify clean:**
```bash
git status --porcelain
```
Must be empty. If not, something went wrong (merge conflict, etc.).

### 3. Report Status Table

Print a markdown table:

```
| Repo | Path | Branch | Was Dirty | Stash Ref | Final Status |
|------|------|--------|-----------|-----------|--------------|
| frontend | .../app-front-portal | dev | Yes | stash@{0} | CLEAN |
| backend | .../app-proximity-report | dev | No | - | CLEAN |
```

### 4. Fail Fast

If any repo:
- Has merge conflicts after pull: STOP. Report which repo and the conflict files. Do not continue to other repos.
- Cannot checkout the target branch: STOP. Report the error.

The user must resolve manually before proceeding with the crawl.

## Safety Rules

- Never rewrite git history
- Stash is reversible (user can `git stash pop` later)
- Never force-checkout (no `git checkout .` or `git checkout --force`)
- If a repo has staged changes (not just modified), warn the user before stashing
- Never pipe git commands. Run each sequentially.
