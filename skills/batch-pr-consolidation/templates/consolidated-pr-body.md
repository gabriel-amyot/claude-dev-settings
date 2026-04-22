# Why this is one PR, not {N}

{N} approved PRs on this repo are shipping together under {DEADLINE-OR-REASON}. Reviewer bandwidth is a bottleneck and the tag-based deploy requires a single clean branch on `main`. Consolidating reduces review overhead from {N} contexts to 1, eliminates rebase churn across stacked branches, and produces a single deployable artifact.

**Tickets in this batch:** {TICKET-IDS-COMMA-SEPARATED}
**Supersedes:** {PR-NUMBERS-COMMA-SEPARATED}

---

## Per-ticket summary

{For each ticket, one bullet. Keep to one sentence per ticket.}

- **{TICKET-ID-1}** — {one-sentence description of what this ticket fixes or adds}
- **{TICKET-ID-2}** — {one-sentence description of what this ticket fixes or adds}
- **{TICKET-ID-N}** — {one-sentence description of what this ticket fixes or adds}

---

## What each ticket does

### {TICKET-ID-1}: {ticket-title}

{2-4 sentences. What was broken or missing, what the fix does, why it matters at runtime. No implementation details — behavior only.}

**Original PR:** #{ORIGINAL-PR-NUMBER-1} (approved by {REVIEWER-1})

---

### {TICKET-ID-2}: {ticket-title}

{2-4 sentences. What was broken or missing, what the fix does, why it matters at runtime. No implementation details — behavior only.}

**Original PR:** #{ORIGINAL-PR-NUMBER-2} (approved by {REVIEWER-2})

---

### {TICKET-ID-N}: {ticket-title}

{2-4 sentences. What was broken or missing, what the fix does, why it matters at runtime. No implementation details — behavior only.}

**Original PR:** #{ORIGINAL-PR-NUMBER-N} (approved by {REVIEWER-N})

---

## Why consolidation is safe

The cross-PR surface area is low. File overlap between each pair of PRs:

| PR Pair | Overlapping Files | Risk | Notes |
|---------|------------------|------|-------|
| {TICKET-ID-1} × {TICKET-ID-2} | {files or "None"} | {Low/Medium/High} | {brief note or "—"} |
| {TICKET-ID-1} × {TICKET-ID-N} | {files or "None"} | {Low/Medium/High} | {brief note or "—"} |
| {TICKET-ID-2} × {TICKET-ID-N} | {files or "None"} | {Low/Medium/High} | {brief note or "—"} |

Medium-risk overlaps were resolved manually — see merge commit messages for conflict resolution rationale.

**Merge order used:** {ordered list, e.g. "SPV-100 → SPV-147 → SPV-155"}

Rationale for order: {one sentence explaining why this ordering was chosen — e.g., "SPV-100 is a pure refactor with no new dependencies; SPV-147 introduces the interface change that SPV-155 consumes."}

---

## Invariant assumptions

The following must hold for this consolidation to be safe to merge:

- [ ] All PRs in the batch target `main` as their base branch
- [ ] No PR in this batch contains an IAM or auth change that bypasses the human-gate protocol
- [ ] No PR in this batch has an outstanding BLOCKER-class review finding
- [ ] The consolidated branch has been built and all tests pass (see Verification below)
- [ ] Jib/Docker image tagging will happen after this PR merges, not before

---

## Verification

Build and test run against the consolidated branch `{CONSOLIDATED-BRANCH-NAME}`:

```
Tests run:    {N}
Failures:     {N}
Errors:       {N}
Skipped:      {N}
Build result: {SUCCESS / FAILURE}
```

{If any pre-existing failures were found: "Note: {N} pre-existing test failures exist on main prior to this batch. These are unrelated to the changes in this PR. See {link-or-description} for details."}

---

## Shipping plan (post-merge)

1. Merge this PR to `main`
2. Tag the resulting commit: `{SERVICE-NAME}-{VERSION}` (follow the service's existing tag convention)
3. The Jib build pipeline picks up the tag and pushes the image to the registry
4. Update `TF_VAR_image_tag` in the DAC repo's GitLab CI/CD variables to the new tag
5. Trigger the DAC pipeline targeting `dev`
6. Verify the service is healthy in dev before promoting to UAT

Note: DAC pipelines on `cicd.prod.datasophia.com` experience nightly downtime (~11 PM to 5 AM ET). Do not trigger DAC deploys during this window.

---

## Supersedes

The following PRs are superseded by this consolidation and have been closed:

| PR | Ticket | Branch | Approved by |
|----|--------|--------|-------------|
| #{ORIGINAL-PR-NUMBER-1} | {TICKET-ID-1} | {branch-name-1} | {reviewer-1} |
| #{ORIGINAL-PR-NUMBER-2} | {TICKET-ID-2} | {branch-name-2} | {reviewer-2} |
| #{ORIGINAL-PR-NUMBER-N} | {TICKET-ID-N} | {branch-name-N} | {reviewer-N} |

Each closed PR has a comment referencing this consolidated PR.

---

## Jira

| Ticket | Link |
|--------|------|
| {TICKET-ID-1} | {JIRA-URL-1} |
| {TICKET-ID-2} | {JIRA-URL-2} |
| {TICKET-ID-N} | {JIRA-URL-N} |
