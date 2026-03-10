---
name: pr-review
description: "Review a pull request following the established protocol: clone/fetch branch to clean location, read Jira AC, review source files. Never review from local working tree. Use when reviewing PRs or merge requests."
---

# PR Review

Reviews a pull request by cloning the branch to a clean location and reading actual source files.

**Usage:** `/pr-review <PR-URL> [JIRA-TICKET]`

**Examples:**
```
/pr-review https://github.com/org/repo/pull/123
/pr-review https://github.com/org/repo/pull/123 SPV-50
/pr-review 123                                          # If already in the repo
```

## Arguments

- `<PR-URL>`: Required. GitHub PR URL, or just the PR number if already in the repo.
- `[JIRA-TICKET]`: Optional. Jira ticket ID to fetch AC for context.

## Protocol

### 1. Fetch PR metadata

```bash
gh pr view {PR-NUMBER} --json title,body,headRefName,baseRefName,files,additions,deletions
```

Extract: title, branch name, base branch, changed files list, description.

### 2. Clone or fetch to clean location

```bash
# If repo not already cloned to /tmp/
gh repo clone {org}/{repo} /tmp/{repo}-review -- --depth=50

# If already cloned
cd /tmp/{repo}-review
git fetch origin pull/{N}/head:pr-{N}
git checkout pr-{N}
```

**CRITICAL: Never review from the local working tree.** Always work from `/tmp/{repo}-review/`.

### 3. Fetch Jira context (if ticket provided)

```bash
/jira get {JIRA-TICKET} --full
```

Extract acceptance criteria for cross-referencing against code changes.

### 4. Read source files

For each changed file from step 1:
- Read the full file from the PR branch (not just the diff)
- Understand the context around changes

### 5. Review

Evaluate against:
- **Acceptance criteria** (if Jira ticket provided): Is each criterion met?
- **Repo standards** (read CLAUDE.md in the repo): Does the code follow patterns?
- **Code quality**: Self-documenting names, small methods, no comment cruft
- **Security**: OWASP top 10 checks on changed code
- **Test coverage**: Are new behaviors tested?

### 6. Report

Write review report to `reports/reviews/pr-{N}-review-{date}.md` in the relevant ticket folder. If no ticket context, print the review inline.

Format:
```markdown
# PR #{N} Review: {title}

**Branch:** {head} → {base}
**Files changed:** {count}
**Jira:** {ticket or "none"}

## Findings

### Critical
{list or "None"}

### Warnings
{list}

### Positives
{good patterns noticed}

## AC Coverage
{checklist if Jira ticket provided}

## Verdict: {PASS|NEEDS CHANGES}
```
