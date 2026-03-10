# Review Response Draft — Internal Review Template

This template defines the DRAFT format used for internal review before posting. It includes full context so the reviewer (Gab) can evaluate the response without switching to GitHub.

## Structure per comment

Each comment block contains everything needed to evaluate the response in one place:

```markdown
---
## [Review-ID] — [Short Title]
**Reply to:** [Reviewer Name] ([GitHub username])
**PR:** [repo-name PR #N](direct link to PR)
**Comment link:** [direct link to the specific comment on GitHub]
**File:** `path/to/file.java:LINE`
**Persona:** Winston (Architect) | Amelia (Developer)
**Ticket:** [SPV-XX](https://origin8cares.atlassian.net/browse/SPV-XX)
**Dan's comment ID:** NNNNNNN (for posting automation)

### Dan's comment:

> Full verbatim text of Dan's comment, quoted.

### Code context:

\```java
// file.java — lines NN-NN
[relevant code snippet where the comment was made]
\```

### Response:

**[Persona]:**

[Name of the person who write the comment], [response body following review-response-inline.md template]

---
**Proposed plan:**
- [action items]
Gab's will review those and move forward if he approves. Let us know if you have any reticence about my reasoning or my plan.
```

## Rules

1. **Commenter's test must be quoted in full verbatim.** No truncation, no summary.
2. **Code context is required for inline comments.** Show the diff hunk or source lines the comment refers to. For PR-level (non-inline) comments, code context can be omitted.
3. **The direct link to the comment must be a clickable GitHub URL** (e.g., `https://github.com/origin8-eng/repo/pull/N#discussion_rNNNNNN`).
4. **Comment ID is included** for the posting automation (`gh api` reply_to parameter).
5. **Persona is spelled out**, not abbreviated.
6. **Short replies** (e.g., "Same fix, tracking on SPV-XX") still need the full context block so Gab can review them in isolation.

## Purpose

This file is what Gab reads to approve or edit responses before they go to GitHub via `/post-comment`. Each block is self-contained: Gab should be able to evaluate any response without opening GitHub or reading other files.
