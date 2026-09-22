# Skill Proposal: batch-pr-consolidation
Status: BUILT (2026-04-21 — functional test: PASS)

Date: 2026-04-13
Source: SPV-92 shipping session — 3 approved retell-service PRs needed to ship together, each required a separate approval, and the local Jib tag build required a single branch with all changes merged together. Stacked PRs would have caused rebase cascades if any PR needed revision. Solution: consolidate into a single PR from a new branch off main.

## Trigger

Invoke when ALL of the following are true:
- Multiple approved (or approved-and-adversarially-reviewed) PRs exist on the same service repo
- Each PR requires a separate reviewer approval (bottleneck)
- The shipping workflow requires a single local branch with all changes (e.g. Jib tag build, local image push)
- The user doesn't have force-merge access on the target repo
- The PRs are logically related OR the user is under deadline pressure

Common trigger phrases: "consolidate these PRs", "make one PR out of these", "I can't force-merge but I need to build the tag locally", "stacked PRs will cause too much rebase pain"

## Scope

Supervisr.AI microservices on GitHub (retell-service, lead-lifecycle-service, supervisor-query-service, compliance-ers, ers, etc.). Also applicable to any GitHub repo where:
- Reviewer approval is a hard gate per PR
- The local shipping workflow needs a single branch (Jib/Docker/tag-based deploy)

NOT applicable to:
- GitLab (Klever CI/CD) — protected branch MR workflow is different
- Repos where the user has force-merge access AND wants individual PR history preserved

## Draft Steps

### Preconditions
1. Identify all PRs to consolidate — collect ticket IDs, PR numbers, branch names, and adversarial review state
2. Verify each PR is approved or adversarially reviewed
3. Verify target repo's `main` branch state — note latest commit hash and tag
4. Pick the consolidated branch name: `{PARENT-TICKET}-batch-consolidated` or `{TICKET}-batch-{scope}` if multi-scope

### Pre-flight
1. Check current working directory in the target repo:
   - `git fetch origin`
   - `git status --short`
   - If dirty: `git stash push -u -m "WIP: {context} before {TICKET} consolidation {YYYY-MM-DD}"` — descriptive label so user can recover later
2. Confirm no existing branch with the consolidated name: `git branch -a | grep {TICKET}-batch-consolidated`

### Branch creation
1. `git checkout main`
2. `git pull origin main` — ensure up to date
3. `git checkout -b {TICKET}-batch-consolidated`

### Merge ordering
**Rule:** merge in order of safest-refactor-first, feature work next, most-dependent last. Reduces conflict cascade risk.

- **Safest-first:** mechanical refactors, interface extractions, profile splits, rename-only PRs. These rarely conflict and fail fast if they do.
- **Feature work:** new functionality that adds files or touches isolated modules.
- **Most-dependent last:** PRs that consume types, fields, or methods added by earlier PRs in the batch.

For each PR in order:
```bash
git merge --no-ff origin/{BRANCH} -m "Merge {TICKET}: {one-line summary}

Part of {PARENT-TICKET} consolidated batch."
```

If a conflict occurs: STOP, report to user, offer options (resolve manually, abort batch, or restructure).

### Build verification
After all merges, run clean build + full test suite to catch any cross-PR integration issues:
```bash
./mvnw clean compile test 2>&1 | grep -E "Tests run:|BUILD SUCCESS|BUILD FAILURE"
```
(Maven-specific — see `java-standards.md` for the full test summary extraction rule.)

**Critical:** if build/test fails, do NOT push. Report the failure with the failing test names and stack trace excerpt, let the user decide next step.

### Push + PR
1. `git push -u origin {TICKET}-batch-consolidated`
2. Open PR via `gh pr create --base main --head {TICKET}-batch-consolidated --title "{PARENT-TICKET} batch: {per-ticket summary joined}" --body "$(cat <<'EOF' ...`

### Consolidation PR body template
Use this structure:

```markdown
## Why this is one PR, not {N}

Consolidates {N} approved and adversarially reviewed PRs into a single reviewable unit:
- **{TICKET-1}** (was #X) — {one-line purpose}
- **{TICKET-2}** (was #Y) — {one-line purpose}
...

{Explain why consolidation beats individual PRs: approval bottleneck, local build workflow, rebase cascade risk, deadline pressure.}

## What each ticket does

### {TICKET-1} — {title}
{2-4 sentence description of the change, including key files touched and rationale.}

**Behavior:** {identical to main / new functionality / correctness upgrade — be explicit.}
{N} lines of new test coverage.

### {TICKET-2} — {title}
...

## Why consolidation is safe (cross-PR safety table)

| Cross-PR concern | Resolution |
|------------------|------------|
| {concern 1, e.g. "{TICKET-2} reads fields from InteractionReport"} | {evidence: "All three fields already exist in main — populated at line 212+"} |
| {concern 2, e.g. "{TICKET-1} orgId validation affects webhook path"} | {evidence: "Webhook entry sets orgId post-SPV-85"} |
| {concern 3, e.g. "{TICKET-3} profile split touches same config"} | {evidence: "No overlap with {TICKET-1}/{TICKET-2} files"} |

## Invariant assumptions

{Any prior-ticket guarantees this batch relies on, flagged for the reviewer's attention.}

## Verification

- `./mvnw clean compile test` — **N tests, 0 failures, 0 errors** on the consolidated branch.
- Notable passing suites:
  - {TestClass1} (N) — {ticket}
  - {TestClass2} (N) — {ticket}

## Shipping plan (post-merge)

1. `git checkout main && git pull origin main`
2. `git tag {next-version} && git push origin {next-version}`
3. `./mvnw compile jib:build -Djib.to.tags={next-version}`
4. `rover subgraph check SupervisrAI@{env} --schema {path} --name {subgraph}` (if schema changed)
5. If clean: `rover subgraph publish ...`
6. Update GitLab DAC variable `TF_VAR_image_tag` via `gitlab_skill.py vars ... --action set`
7. Trigger dev pipeline
8. Manual apply click (HAQ-11 standing blocker on Supervisr)

## Supersedes
- Closes #{X} ({TICKET-1})
- Closes #{Y} ({TICKET-2})
...

## Jira
- {PARENT-TICKET} (parent)
- {TICKET-1}
- {TICKET-2}
...
```

### Close superseded PRs
For each original PR:
```bash
gh pr close {N} --comment "Superseded by #{CONSOLIDATED} — consolidated into the {PARENT-TICKET} batch PR so a single review/approval/merge covers {all tickets} together. Branch preserved on origin for reference."
```

### Post Jira comments
For each ticket (parent + children):
```bash
python3 ~/.claude/skills/jira/jira_skill.py add-comment {TICKET} --org {slug} --comment "[automated]

{status summary with PR link}"
```
(See `CLAUDE.md` Jira Skill Gotchas section for org slug + command name rules.)

### Report back
- Return consolidated PR URL to user
- Summarize merge order, test count, files affected
- Flag any invariant assumptions
- Remind user of next post-merge steps (tag, Jib, rover, DAC var, manual apply click)

## Exceptions / Gotchas

- **If the user HAS force-merge access AND wants individual PR history preserved:** use stacked PRs instead (PR A rebased on main, PR B rebased on A, PR C rebased on B). Not this skill's scope.
- **If ANY PR has pre-existing contamination concerns** (e.g. harness code): investigate via `pr-panic-protocol.md` first. Don't blindly merge PRs that carry contamination, even if they're "approved."
- **If the target repo uses GitLab MR workflow with protected branches:** consolidation doesn't apply the same way. GitLab MR rebase + merge train handles this differently. Defer to Klever deploy workflow in that case.
