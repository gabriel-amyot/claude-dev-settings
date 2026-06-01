# [TICKET_ID] Session State — [DATE]

## Current Status
**IN PROGRESS.** Autonomous ticket ship initiated by Gabriel.

## Ground Rules

1. **No MR creation.** Push branches, capture MR URLs from `remote:` output, hand off to Gabriel.
2. **No Jira writes.** No comments, no status transitions, no AC updates on Jira.
3. **No deploys.** Commits push to feature branches. CI picks up on MR creation.
4. **No destructive git operations.** No `--force`, no `--amend` on pushed commits, no rebase on shared branches, no `--no-verify`.
5. **Commit per AC.** One atomic commit per acceptance criterion. Multi-AC commits allowed only when code is intrinsically coupled (e.g., handler + validator).
6. **Pre-AC dev check is mandatory.** Before writing code for each AC, check if it's already landed on `dev`. Do not re-implement existing work.
7. **Local verify blockage is a logged blocker, not a stop condition.** Commit the code, note the blocker, let CI verify.

## Escalation Paths

| Situation | Action |
|-----------|--------|
| Unexpected architecture question | Spawn Winston (architect) subagent for analysis |
| Runtime bug during local testing | Spawn Dexter (debugger) subagent for diagnosis |
| Spec ambiguity or AC conflict | Spawn Leo (spec coach) for clarification, record in blockers_hit_during_run |
| Code in unfamiliar area | Read first, grep for patterns, do NOT modify without understanding |

## Working Locations

| Repo | Path | Branch | Worktree |
|------|------|--------|----------|
| [REPO_1_NAME] | [REPO_1_PATH] | [BRANCH_1] | [YES/NO] |
| [REPO_2_NAME] | [REPO_2_PATH] | [BRANCH_2] | [YES/NO] |

## Agent Checklist

- [ ] Scaffolding files written (SESSION_STATE.md, ac-tracking.yaml, STATUS_SNAPSHOT.yaml, repo-mapping.yaml)
- [ ] Clean repo gate passed on every touched repo
- [ ] Pre-AC dev check run for every AC before writing code
- [ ] Blocker defaults documented in ac-tracking.yaml
- [ ] Commit per AC with SHA tracked in ac-tracking.yaml
- [ ] Local verify blockage documented in blockers_hit_during_run
- [ ] All branches pushed, MR URLs captured
- [ ] Morning handoff written to GABRIEL_INBOX.md with drafted MR descriptions
- [ ] No MRs created, no Jira writes, no deploys

## Completed This Session

*(Updated as ACs are completed)*

## Next Steps

*(Updated at end of session)*
