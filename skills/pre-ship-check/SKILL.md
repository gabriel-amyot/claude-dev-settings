---
name: pre-ship-check
description: "Pre-shipping readiness check across all services in an epic. Reads REPO_MAPPING.yaml and runs git status on each mapped repo. Reports unpushed commits, dirty files, branch state, and tag history. Use before shipping or deploying."
---

# Pre-Ship Check

Checks shipping readiness across all services mapped in an epic's REPO_MAPPING.yaml.

**Usage:** `/pre-ship-check [EPIC-ID]`

**Examples:**
```
/pre-ship-check SPV-3
/pre-ship-check                # Auto-detect from $PWD
```

## Arguments

- `[EPIC-ID]`: Optional. If not provided, detect from current directory.

## Steps

### 1. Locate REPO_MAPPING.yaml

```
If EPIC-ID provided:
  path = project-management/tickets/{EPIC-ID}/REPO_MAPPING.yaml
Else:
  Walk up from $PWD looking for REPO_MAPPING.yaml
```

Parse the YAML to extract all repositories with their paths and main branches.

### 2. Check each repo

For each repository in the mapping, run these checks sequentially:

```bash
cd {repo_path}

# Branch state
git branch --show-current
git fetch origin
git status --short

# Unpushed commits
git log origin/{main_branch}..HEAD --oneline

# Latest tag
git describe --tags --abbrev=0 2>/dev/null || echo "no tags"

# Uncommitted changes
git diff --stat
```

### 3. Produce report

Print a summary table:

```
Pre-Ship Check: {EPIC-ID}
Date: YYYY-MM-DD

| Service | Branch | Clean | Pushed | Latest Tag | Status |
|---------|--------|-------|--------|------------|--------|
| lead-lifecycle | SPV-8-fix | ✓ | ✓ | 0.0.9-dev | Ready |
| retell-service | main | ✓ | ✓ | 0.0.12-dev | Already shipped |
| eqs | SPV-23-schema | ✗ (2 files) | ✗ (3 commits) | 0.0.14-dev | Not ready |

Issues:
- eqs: 2 uncommitted files (schema.graphqls, EqsConfig.java)
- eqs: 3 unpushed commits on SPV-23-schema

Recommendation:
- Commit and push eqs changes before shipping
- lead-lifecycle and retell-service are ready
```

### 4. Warnings

Flag these conditions:
- **Dirty working tree**: Uncommitted changes in any mapped repo
- **Unpushed commits**: Local commits not on remote
- **Detached HEAD**: Not on a named branch
- **Main branch divergence**: Main has advanced since the feature branch was created
- **No tags**: Repo has never been tagged (first release?)
