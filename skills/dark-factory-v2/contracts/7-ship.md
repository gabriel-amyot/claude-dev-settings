# Contract 7 — Ship-prep (code only)

**Code preparation only.** Version bump, CHANGELOG, commit, push. You do **NOT** create the MR, post
to Jira, or transition the ticket — those use skills (`/klever-mr`, `/post-comment`) that are not
reliably callable from inside a workflow agent, so the **main loop** does them after this workflow
returns. (Verified constraint, see docs/review-findings-v0.1.0.md V2.)

The orchestrator already ran the pre-ship gate before calling you (execution verified, zero open
CRITICAL, QA green) — do not re-litigate it.

## Get the code (your worktree)

The Workflow runtime gave you your own worktree. Fetch + check out the pushed feature branch (name in
your prompt): `git fetch origin <branch> && git checkout <branch>`.

## Steps

1. **Version bump + CHANGELOG.** Bump the version file for the repo type (e.g. `pom.xml` for
   Java/Maven) and add a CHANGELOG entry with the why/what. CI fails on tag collision, so check the
   current dev version first and bump above it.
2. **Commit:** `<TICKET>: version bump + changelog`.
3. **Push:** `git push origin <branch>`. Set `pushed: true`. (Feature branch only — never dev/main.
   DAC repos: dev only.)

## Do NOT

- Do NOT run `/klever-mr`, `/post-comment`, or `jira_skill.py transition`.
- Do NOT push to `dev`, `main`, or `uat`.
- Do NOT merge.

## Return

- `status`: pass | partial | stuck
- `branch`: the branch you pushed
- `version`: the new version string
- `pushed`: boolean
- `summary`: 1-2 sentences (include the version)

The main loop will: create the MR via `/klever-mr` (no auto-merge), post the Jira comment via
`/post-comment` (MR link + AC summary + QA evidence), transition the ticket to In Review/Testing, and
run the post-merge validate (contract 8) once the human merges.
