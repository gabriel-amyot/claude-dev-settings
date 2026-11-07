---
name: pr-review
description: "Comprehensive PR review with isolation and context. Clones to /tmp for clean review, fetches Jira AC if ticket provided, runs security checks (OWASP), then delegates to pr-review-toolkit agents (code-reviewer, test-analyzer, silent-failure-hunter, type-design-analyzer, comment-analyzer, code-simplifier). Use for reviewing your own PRs/MRs before shipping. Triggers on: 'review my PR', 'check my changes', 'before I push', 'look at my code', 'am I good to merge'. For teammates' PRs, use colleague-review agent instead. Input: PR URL or branch + optional ticket key. Returns: multi-agent review report."
user_invocable: true
nav:
  bay: review
  when: "Comprehensive PR review with isolation, Jira AC fetch, OWASP security checks."
  when_not: "Reviewing teammates' PRs (use colleague-review agent). Light code check (use /adversarial-cascade)."
---

# PR Review

## Host compatibility

Read [the shared host mapping](../../docs/skill-host-compatibility.md) before execution. Use native tools and the existing shared agent instructions. Required executors and companion skills remain real dependencies.


## Shared maintenance note (2026-10-26)

Keep. Gabriel uses or wants this documentation/review workflow available in both agents. See [the shared selection record](../../docs/harness-skill-selection.md).


Comprehensive PR review with isolation, Jira AC cross-reference, OWASP security scan, and multi-agent analysis.

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

---

## Step 1: Parse Input

Choose the forge before running Steps 2 and 3. The gh commands below are GitHub examples. For GitLab, load the shared gitlab skill, fetch the real head/base refs and existing discussions, and use Git for the isolated clone. Do not send a GitLab URL to gh.

Extract from the provided argument:
- PR URL or PR number
- Optional Jira ticket key (e.g., `SPV-50`, `KTP-123`)

If a full URL is provided, parse `{owner}`, `{repo}`, and `{PR_NUMBER}` from it.

---

## Step 2: Fetch PR Metadata

```bash
gh pr view {PR_NUMBER} --repo {OWNER}/{REPO} --json title,body,headRefName,baseRefName,files,additions,deletions
```

Extract: title, branch name, base branch, changed file list, description.

---

## Step 3: Clone to /tmp for Isolation

**CRITICAL: Never review from the local working tree.** Always clone to `/tmp/{repo}-review/`.

```bash
# If not already cloned
gh repo clone {OWNER}/{REPO} /tmp/{REPO}-review -- --depth=50

# If already cloned, fetch the PR branch
cd /tmp/{REPO}-review
git fetch origin pull/{PR_NUMBER}/head:pr-{PR_NUMBER}
git checkout pr-{PR_NUMBER}
```

---

## Step 4: Fetch Jira AC (if ticket provided)

If a Jira ticket key was provided:

```bash
/jira get {JIRA-TICKET} --full
```

Extract acceptance criteria. These will be used to cross-reference code changes in the final report.

If no ticket was provided, skip this step.

---

## Step 5: OWASP Security Scan

Fetch the PR diff and scan for common OWASP Top 10 issues:

```bash
gh pr diff {PR_NUMBER} --repo {OWNER}/{REPO}
```

Check for the following in the diff:

| Category | What to look for |
|----------|-----------------|
| **Injection** | Raw string interpolation into SQL, shell commands, or LDAP queries. Missing parameterized queries or prepared statements. |
| **XSS** | User input rendered without escaping in HTML/JS contexts. Missing output encoding. |
| **Auth bypass** | `permitAll()`, `allUsers`, missing auth annotations, security filter bypasses, public endpoints that should be protected. |
| **Broken access control** | Missing ownership checks, role checks, or scoping on queries. |
| **Sensitive data exposure** | Credentials, tokens, PII logged or returned in API responses. Hard-coded secrets. |
| **Insecure deserialization** | Untrusted data deserialized without validation. |
| **Missing error handling** | Catch blocks that swallow exceptions and hide security-relevant failures. |

Record any findings as Critical or Warning for the final report.

---

## Step 6: Delegate the Review

When Claude's pr-review-toolkit is available, use it as below. Otherwise use native independent reviewers for correctness, test validity, silent failures, type/contracts, comments and unnecessary complexity. Pass the pinned head/base, changed files, actual acceptance source (AC-LOCAL.md when present), org and isolated clone path. Require evidence for findings. Do not claim the toolkit ran when using native reviewers.

Read existing MR/PR comments before preparing external feedback. Do not repeat an issue already covered. Refine an existing thread when clarification is needed. Gabriel prefers collaborative, guiding, encouraging comments that explain the issue and its impact, with implementation detail only where needed to understand the issue.

For a GitLab MR, use the shared gitlab skill and the forge's real head/base refs for metadata, existing discussions and diff. Clone/fetch those refs with Git rather than running the GitHub-only examples. Empty API diff metadata is not proof of no changes. Pin the reviewed commit and report any evidence limitations.

Tell the user to run the multi-agent toolkit review from the cloned directory:

> The isolated clone is ready at `/tmp/{REPO}-review` on branch `pr-{PR_NUMBER}`.
> Run `/pr-review-toolkit:review-pr` from that directory for the full multi-agent analysis (code-reviewer, test-analyzer, silent-failure-hunter, type-design-analyzer, comment-analyzer, code-simplifier).

If you are operating in an autonomous or agent context where you can spawn subagents, invoke `/pr-review-toolkit:review-pr` directly and collect the output for aggregation in Step 7.

---

## Step 7: Compile Final Report

Aggregate all findings into a single report.

If a Jira ticket was provided, write the report to `reports/reviews/pr-{N}-review-{date}.md` in the relevant ticket folder. Otherwise, print inline.

```markdown
# PR #{N} Review: {title}

**Branch:** {head} → {base}
**Files changed:** {count}
**Jira:** {ticket or "none"}
**Reviewed from:** /tmp/{repo}-review (isolated clone)

---

## Security Scan (OWASP)

### Critical
{list or "None"}

### Warnings
{list or "None"}

---

## Multi-Agent Analysis

{paste or summarize output from pr-review-toolkit:review-pr}

---

## AC Coverage

{checklist against Jira AC — only if ticket was provided}

| AC | Met? | Notes |
|----|------|-------|
| {criterion} | ✓ / ✗ | {notes} |

---

## Verdict: {PASS | NEEDS CHANGES}

{1-2 sentence summary of key blockers or confirmation the PR is shippable}
```
