# Contract 7 — Ship-prep (code only)

**Code preparation only.** Version bump, CHANGELOG, commit, push. You do **NOT** create the MR, post
to the tracker, or transition/resolve the ticket — those use skills (`/klever-mr`, `/post-comment`,
`/wayfinder-report-back`) that are not reliably callable from inside a workflow agent, so the **main
loop** does them after this workflow returns. (Verified constraint, see docs/review-findings-v0.1.0.md V2.)

The orchestrator already ran the pre-ship gate before calling you (execution verified, zero open
CRITICAL, QA green) — do not re-litigate it.

## Get the code (your worktree)

The Workflow runtime gave you your own worktree. Fetch + check out the pushed feature branch (name in
your prompt): `git fetch origin <branch> && git checkout <branch>`.

## Steps

1. **Version bump + CHANGELOG.** Check your tool belt's `has_version_file`. If yes, bump the version
   file the belt names, above dev's current version (CI fails on tag collision), and add a
   CHANGELOG entry with the why/what. **If `has_version_file: no`** (many scripting repos), SKIP the
   version bump — `/klever-mr` skips that gate for repos without a version file — but still add a
   CHANGELOG entry if the repo keeps one.
2. **Commit:** `<TICKET>: version bump + changelog`.
3. **Push:** `git push origin <branch>`. Set `pushed: true`. (Feature branch only — never dev/main.
   DAC repos: dev only.)

## Do NOT

- Do NOT run `/klever-mr`, `gh pr create`, `/post-comment`, `/wayfinder-report-back`, `gh issue
  comment`, `gh issue close`, or `jira_skill.py transition`.
- Do NOT push to `dev`, `main`, or `uat`.
- Do NOT merge.

## Return

- `status`: pass | partial | stuck
- `branch`: the branch you pushed
- `version`: the new version string
- `pushed`: boolean
- `summary`: 1-2 sentences (include the version)

The main loop will: open the merge/pull request with no auto-merge, using the forge of the **code
repo** (a Klever GitLab repo uses `/klever-mr`; a GitHub repo uses `gh pr create`) — the ticket source
does not decide this; post the status comment via `/post-comment` (MR link + AC summary + QA
evidence); close out on the tracker (Jira: transition to In Review/Testing; a wayfinder GitHub issue:
`/wayfinder-report-back`, leaving closure to the wayfinder resolve path); and run the post-merge
validate (contract 8) once the human merges.
