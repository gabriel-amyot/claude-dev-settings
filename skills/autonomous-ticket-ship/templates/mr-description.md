# MR Description Template

Use this structure for every MR description. Copy into GitLab web UI when creating the MR.

---

## Tickets

[TICKET_ID](https://beklever.atlassian.net/browse/[TICKET_ID])

## Commits

[COMMIT_LOG]
<!-- Paste output of: git log --reverse --format="### %s%n%n%b" origin/dev..HEAD -->

## Test plan

[TEST_PLAN]
<!-- Checklist of how this was verified. Example:
- [ ] Local backend compile (`mvn compile`)
- [ ] Unit tests pass (`mvn test`)
- [ ] Frontend builds (`npm run build`)
- [ ] Manual walkthrough of primary workflow
-->

---

## Defaults to validate

The following design decisions were made by the agent using safe defaults. Push back on any that don't match your intent:

[DEFAULTS_LIST]
<!-- Numbered list from ac-tracking.yaml → blockers_defaults_applied. Example:
1. Invite-email notice shown in New User modal
2. Gated by isAdmin() only, no component registry change
3. Zero scopes allowed with confirm prompt
-->
