# Morning Handoff Template

Append this as a section to `general/GABRIEL_INBOX.md` after the autonomous run completes.

---

## ✅ MORNING HANDOFF — [TICKET_ID] ([DATE])

**Status:** [EMOJI] **[STATUS_SUMMARY]**

### Per-AC Status

| AC | What | Status | Commit |
|----|------|--------|--------|
[AC_TABLE]
<!-- One row per AC. Example:
| AC-1 | GET /components endpoint | ✅ done (already on dev) | — |
| AC-2 | GET /roles endpoint | ✅ done | `69340eb` |
| AC-3 | Atomic PUT | ✅ done | `e25d517` |
-->

### Branches

[BRANCH_TABLE]
<!-- Per-repo: repo name, branch, head SHA, MR create URL. Example:
**Backend** — `app-user-management` / `KTP-XXX-description` / head `e25d517`
MR create URL: https://cicd.prod.datasophia.com/...

**Frontend** — `app-front-portal` worktree `app-front-portal-ktpXXX` / `KTP-XXX-description` / head `dd9692d`
MR create URL: https://cicd.prod.datasophia.com/...

**Ship [order] first, then [order].**
-->

### MR Description Drafts

[MR_DRAFTS]
<!-- Include the full MR description for each repo, ready for copy-paste.
Use the mr-description.md template structure: Tickets, Commits, Test plan, Defaults to validate.
-->

### Verification Gaps

[VERIFICATION_GAPS]
<!-- List items that could not be verified locally. Example:
1. Backend never locally compiled — CI will verify
2. Frontend typecheck deferred to CI
3. Manual walkthrough not captured — do locally before creating MRs
-->

### Defaults Applied (PO Review)

[DEFAULTS_APPLIED]
<!-- Copy from ac-tracking.yaml → blockers_defaults_applied. Example:
1. Q1: Invite-email notice shown in New User modal
2. Q2: isAdmin() gate only for v1
-->
