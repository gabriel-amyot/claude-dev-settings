# Skill Proposal: pr-inventory-scan
Date: 2026-04-20
Source: Phase 1 coaching session — PR housekeeping across origin8-eng

## Trigger
"scan my PRs", "PR inventory", "what PRs are open", "PR dashboard", "what needs review", or at session start when context is PR management/shipping.

## Scope
org (Supervisr/Origin8 — origin8-eng GitHub org)

## Draft Steps
1. Scan all origin8-eng repos for open PRs (retell-service, lead-lifecycle-service, supervisor-query-service, compliance-ers, origin8-web)
2. For each PR: fetch author, assignees, review state, mergeable status, CI status, age
3. Categorize: (a) mine needing action, (b) mine waiting on reviewer, (c) reviewed by me, (d) needs my review (not mine, no review from me), (e) others
4. Check staleness: flag PRs > 4 weeks old with "STALE?" marker
5. Output: formatted table with links, ordered by priority

## Notes
- origin8-web uses `master`, all others use `main`
- Should detect if PR branch is behind main and flag it
- Could auto-merge main into branches if requested
