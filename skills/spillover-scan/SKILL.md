---
name: spillover-scan
description: "Aggregate accepted adversarial findings, warnings, and test gaps from closed tickets into a tracking ticket. Classifies by severity, recommends priority order, and posts to Jira."
user_invocable: true
---

# Spillover Scan

Collect and track all accepted risks, warnings, and test gaps from recently closed tickets.

**Usage:**
```
/spillover-scan KTP-430                      # Aggregate into specific tracking ticket
/spillover-scan KTP-430 --from KTP-328,337   # Only scan specific source tickets
/spillover-scan --dry-run                    # Show findings without posting
```

## When to Use

- After `/sprint-close` to capture all accepted adversarial findings
- After any ticket closure where findings were documented but deferred
- Before sprint planning to surface deferred quality debt

## Workflow

### Phase 1: Collect Findings

Scan these sources for each closed ticket:
1. `tickets/{TICKET}/reports/status/closing-comment-draft-*.md` — adversarial findings noted in closing comments
2. `tickets/{TICKET}/reports/reviews/adversarial-review-*.md` — full adversarial review reports
3. Adversarial agent output from the current session (if available)

Extract every finding that was:
- Accepted (not fixed before closure)
- Classified as WARNING, MEDIUM, or higher
- Noted as "deferred" or "out of scope" or "accepted risk"

### Phase 2: Classify and Deduplicate

For each finding, record:
- **Source ticket** (where it was found)
- **Severity** (HIGH / MEDIUM / LOW / INFO)
- **Category** (dead code, test gap, E2E no-op, deployment verification, schema risk, etc.)
- **Action needed** (specific, actionable description)
- **Dedup key** (prevent the same finding from appearing twice if it was flagged in multiple tickets)

### Phase 3: Write Report

Write to `tickets/{TRACKING-TICKET}/spillover-findings-{date}.md`:

```markdown
# Spillover Findings from [context] ({date})

Aggregated from adversarial reviews of {ticket list}.

## From {SOURCE-TICKET} — {summary}

| # | Severity | Finding | Action Needed |
|---|----------|---------|---------------|

## Summary by Severity

| Severity | Count | Key Themes |
|----------|-------|------------|

## Recommended Priority
1. Quick wins first
2. Prerequisites for upcoming work
3. Deployment-blocked items
4. Housekeeping
```

### Phase 4: Post to Jira

Draft a Jira comment summarizing the findings (grouped by severity). Post via `/post-comment` with user approval.

The Jira comment should NOT include local file paths. Reference the spillover findings document generically.

### Phase 5: Update Bug Tracker

If the tracking ticket has an existing `bug-tracker-*.md`, append the new findings to it. Do not duplicate entries that are already tracked.

## Severity Guidelines

| Severity | Criteria |
|----------|----------|
| HIGH | Test that cannot fail (no-op assertion), missing deployment verification, silent data loss |
| MEDIUM | Dead code, untested code path, API surface gap, stale documentation |
| LOW | Code hygiene (dead files), minor E2E gaps covered by other evidence |
| INFO | Intentional trade-offs, future considerations, out-of-scope observations |

## Anti-patterns

- Do not silently drop any finding. If it was flagged, it gets tracked.
- Do not inflate findings. An INFO is an INFO, not a MEDIUM.
- Do not post local file paths to Jira.
- Do not close the tracking ticket. It stays open until all findings are addressed.
