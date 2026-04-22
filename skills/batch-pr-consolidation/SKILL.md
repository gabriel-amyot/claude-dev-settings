---
name: batch-pr-consolidation
description: Consolidates multiple approved GitHub PRs into one branch. Trigger: "consolidate these PRs", "make one PR out of these", "batch PRs", "stacked PRs will cause too much rebase pain".
---

# Batch PR Consolidation

Merge multiple approved GitHub PRs on a single service repo into one consolidated PR. Use this when reviewer bandwidth is a bottleneck, when a tag-based deploy (Jib/Docker) requires a single branch to be clean, or when several tickets are shipping together under a deadline and rebase overhead across stacked branches is unacceptable.

**Scope:** Supervisr.AI microservices on GitHub only. Do NOT apply to GitLab repos (those follow the DAC merge-forward model with `dev` → `uat` → `main` promotion via MR).

**Do NOT use when:** the user has force-merge access and wants individual PR history preserved per ticket, or when the PRs touch unrelated services with no shared runtime dependency.

---

## Step 1 — Identify the Consolidation Set

Before touching any code, gather:

- The ticket IDs being consolidated (e.g., SPV-100, SPV-147, SPV-155)
- The corresponding PR numbers and branch names on the target GitHub repo
- The review state of each PR: approved / changes requested / draft
- The merge base for each branch (confirm they all branch from `main` or the shared base)

Ask the user if any of these are ambiguous. Do not proceed with a partial consolidation set.

Record the full list in this format before moving forward:

```
| Ticket   | PR   | Branch                              | State    |
|----------|------|-------------------------------------|----------|
| SPV-100  | #20  | SPV-100-gateway-rs-auth             | Approved |
| SPV-147  | #21  | SPV-147-reconciliation-fix          | Approved |
| SPV-155  | #22  | SPV-155-bodyvalue-serialization     | Approved |
```

---

## Step 2 — Verify Approval Gate

Each PR in the consolidation set must meet at least one of:

- GitHub "Approved" review from a human reviewer
- Adversarial review completed (findings logged in `tickets/{ID}/reports/reviews/`) with no BLOCKER-class findings outstanding

If any PR has an open BLOCKER finding or zero approvals, surface it to the user and ask whether to proceed or hold that PR out of the consolidation.

Do NOT silently exclude a PR. If you drop one from the set, tell the user exactly which one and why.

---

## Step 3 — Pre-flight: Repository State

Run the following in order. Do not use `&&` to chain git commands — run them sequentially and read the output before proceeding.

```bash
git fetch origin
```

Then:

```bash
git status
```

If the working tree is dirty:
- Stash changes with a descriptive message: `git stash push -m "batch-pr-consolidation pre-flight stash"`
- Note the stash ref so it can be popped after the consolidation branch is created

Confirm the local `main` is up to date with `origin/main`. If it is behind, pull.

---

## Step 4 — Determine Merge Order

This is the highest-risk step. Merge in this order:

1. **Pure refactors and renames first.** Changes that move code without altering behavior create the least conflict surface for subsequent merges.
2. **Interface or contract changes second.** Changes to GraphQL schemas, API response shapes, or shared data models must land before anything that consumes the new shape.
3. **Feature implementations third.** New behavior that depends on the interfaces or refactors from steps 1–2.
4. **Most dependency-heavy change last.** Any PR that imports or calls something introduced by an earlier PR in this set.

If two PRs are truly independent (no shared files, no shared runtime call graph), their order within the same tier does not matter. When in doubt, go alphabetical by branch name for determinism.

Document the chosen merge order before executing. Example:

```
Merge order:
1. SPV-100 (#20) — refactors Apollo Router header forwarding, no new deps
2. SPV-147 (#21) — fixes reconciliation field, depends on no other PR here
3. SPV-155 (#22) — serialization fix, lowest blast radius, no cross-PR deps
```

---

## Step 5 — Build the Cross-PR Safety Table

For each pair of PRs in the set, note whether they touch overlapping files. Use `git diff --name-only origin/main...{branch}` for each branch to produce the file list, then cross-reference.

```
| PR Pair         | Overlapping Files              | Risk   |
|-----------------|-------------------------------|--------|
| #20 × #21       | None                          | Low    |
| #20 × #22       | RetellServiceClient.java      | Medium |
| #21 × #22       | None                          | Low    |
```

**Medium risk** means you need to inspect the conflict resolution manually after merging. Do not auto-resolve with `git checkout --theirs` or `git checkout --ours` without reading both sides.

---

## Step 6 — Create the Consolidated Branch

```bash
git checkout main
git pull origin main
git checkout -b consolidated/{TICKET-IDS}-batch
```

Name the branch using all ticket IDs, hyphen-separated, followed by `-batch`. Example: `consolidated/SPV-100-SPV-147-SPV-155-batch`.

---

## Step 7 — Merge Each Branch in Order

For each branch in the determined merge order:

```bash
git merge origin/{branch-name} --no-ff -m "{TICKET-ID}: merge {branch-name} into consolidation batch"
```

Use `--no-ff` to preserve merge provenance. The commit message should reference the originating ticket.

If a merge conflict occurs:
1. Read both sides of the conflict before resolving
2. Resolve manually — never use automated conflict resolution strategies without reading the diff
3. Stage the resolved file and `git merge --continue`
4. If the conflict is in a file you did not create and do not fully understand, stop and surface it to the user before continuing

---

## Step 8 — Build and Test Verification

After all merges are complete, run the service's standard build and test suite. For Supervisr.AI Java services:

```bash
mvn clean verify
```

If the build fails:
- Read the error output
- If the failure is in code introduced by one of the PRs being consolidated, fix it on the consolidation branch and note it in the PR body
- If the failure is pre-existing (present on `main` before any of these PRs), document it separately and do not let it block consolidation — but flag it to the user

Record the final test result counts: tests run, failures, skipped.

---

## Step 9 — Push and Create the Consolidated PR

```bash
git push origin consolidated/{TICKET-IDS}-batch
```

Then create the PR using `gh pr create`. Use the template at `~/.claude/skills/batch-pr-consolidation/templates/consolidated-pr-body.md` to construct the body. Fill in all `{PLACEHOLDER}` values before posting.

```bash
gh pr create \
  --base main \
  --head consolidated/{TICKET-IDS}-batch \
  --title "{PRIMARY-TICKET}: consolidated batch — {ONE-LINE-SUMMARY}" \
  --body "$(cat /path/to/filled-template.md)"
```

The PR title should lead with the highest-priority ticket ID in the batch.

All external posts go through `/post-comment`. Do NOT post the PR body inline. Write the filled template to disk first, then invoke `/post-comment` for preview and explicit approval before posting.

---

## Step 10 — Close Superseded PRs

For each original PR being replaced, post a closing comment and then close the PR. The comment must follow the `/post-comment` protocol — draft to disk first, preview, wait for approval.

Comment template (fill in before posting):

```
This PR has been consolidated into #{CONSOLIDATED-PR-NUMBER} ({consolidated-branch-name}) along with {OTHER-TICKET-IDS}.
The consolidated PR covers the full changeset and is ready for review and merge.
Closing this PR to avoid double-review overhead.
```

Close the PR:

```bash
gh pr close {PR-NUMBER} --comment "Superseded by #{CONSOLIDATED-PR-NUMBER}"
```

Do this for every superseded PR. Do not leave any original PR open with "Superseded" in its title — close it properly.

---

## Step 11 — Post Jira Comments

For each ticket in the consolidation set, post a Jira comment via the `/jira` skill using `add-comment`. Use the `/post-comment` protocol.

Comment content (adapt per ticket):

```
[automated] Branch {original-branch} consolidated into #{CONSOLIDATED-PR-NUMBER} ({consolidated-branch-name}).
Original PR #{ORIGINAL-PR-NUMBER} closed. Consolidation includes: {TICKET-IDS-IN-BATCH}.
Awaiting review and merge on the consolidated PR.
```

Never mention autonomous tooling, agent sessions, or crawls in Jira comments. Present outcomes only.

---

## Step 12 — Report Back

When all steps are complete, provide a summary in this format:

```
Consolidated PR: {URL}
Branch: consolidated/{TICKET-IDS}-batch
Merge order: {ordered list}
Test result: {N tests, N failures, N skipped}
Superseded PRs closed: {list of PR numbers}
Jira comments posted: {list of ticket IDs}
```

If any step was skipped or a decision was deferred to the user, call it out explicitly.

---

## Invariant Assumptions

These must hold for consolidation to be safe. Verify each one before starting:

1. All PRs target the same base branch (`main` on the GitHub repo — not `dev`, not `uat`).
2. No PR in the set is in draft state unless the user explicitly authorizes including it.
3. No PR has an outstanding BLOCKER-class review finding unless the user explicitly overrides.
4. The consolidated branch will be reviewed before merge — consolidation does not bypass code review, it reduces the number of review contexts from N to 1.
5. Jib/Docker image tagging happens after the consolidated PR merges to `main`. Do not tag before merge.

---

## When NOT to Use This Skill

- GitLab repos (DAC/IAC). Use the `dev` → `uat` → `main` merge-forward model with individual MRs.
- When the user wants to preserve individual PR merge commits for auditability and has reviewer bandwidth.
- When PRs belong to different service repos. Consolidation is per-repo only.
- When any PR contains an IAM/auth change that requires the human-gate protocol (read `~/.claude/library/context/shipping-workflow.md` for the full gate procedure).

---

## Error Recovery

**Conflict mid-merge you cannot resolve:** Run `git merge --abort`, restore the original branch state, and report to the user with the exact file names in conflict. Do not leave the repo in a partial merge state.

**Build fails after all merges:** Do not push. Diagnose which PR introduced the failure using `git bisect` or by checking each PR's diff against the failing module. Report to the user before pushing.

**Wrong branch pushed:** Do not force-push. Create a new branch from the correct state, push that, and delete the wrong branch with `git push origin --delete {wrong-branch}`.
