# Skill Proposal: ticket-to-mr-agent
Date: 2026-05-01
Source: KTP-552 bug fix session

## Trigger
"pick up KTP-XXX", "fix this bug", "ship this ticket", or any scoped bug/feature ticket with clear AC.

## Scope
org (Klever)

## Draft Steps
1. **Pick up** — Fetch ticket from Jira, scaffold local folder, read AC
2. **Investigate** — Read code, identify root cause, draft plan
3. **Comment plan** — Post Amelia plan comment to Jira (investigation + TLDR plan + files)
4. **Implement** — Create worktree, fix, add tests, version bump, CHANGELOG
5. **Test** — `mvn clean test` (or `npm test`), capture results
6. **Push + MR** — Push branch, run `/klever-mr` gates, generate MR description
7. **Comment validation** — Post Amelia validation comment to Jira (test results + MR link + what/why)
8. **Dev validation** — After merge+deploy, `open` dev URL in browser, verify fix, screenshot
9. **Comment closing** — Post closing comment with dev validation evidence + recommendation to close

## Notes
Differs from `autonomous-ticket-ship` in that all comms go to the Jira ticket (not terminal). Designed for headless operation where Gabriel reviews only the ticket. Uses `/jira` skill for comments (wiki markup, not raw API). Uses `open` for dev validation behind IAP.
