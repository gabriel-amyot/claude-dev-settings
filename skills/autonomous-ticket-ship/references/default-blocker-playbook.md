# Default Blocker Playbook

Safe defaults for common PO/design questions that would normally block implementation. Each default is **reversible** and documented in `ac-tracking.yaml → blockers_defaults_applied` so the PO can push back per-default on the MR.

## Principles

1. **Pick the option that is easiest to change later.** Separate > combined. New > modified. Gated > open.
2. **Never default on security posture.** Auth, permissions, and data access always require explicit user decision.
3. **Record every default with a short rationale.** The PO reviews these on the MR. No silent decisions.

## Common Blocker Defaults

### API Design

| Blocker | Safe Default | Rationale |
|---------|-------------|-----------|
| Combined vs separate endpoint? | **Separate endpoints** | Easier to merge later than to split. Avoids coupling unrelated concerns. |
| Request/response shape undecided? | **Follow existing DTO pattern in repo** | Consistency with codebase. Grep for similar endpoints, mirror the shape. |
| PUT vs PATCH for updates? | **PUT (full replace)** | Simpler contract. PATCH requires merge semantics. Replace-all with `@Transactional` is atomic. |
| Pagination on list endpoint? | **No pagination for v1** | Ship the feature. Add pagination when data volume requires it. |
| Batch vs single-item endpoint? | **Single-item first** | Simpler contract, easier to test. Batch is additive later. |

### Frontend UX

| Blocker | Safe Default | Rationale |
|---------|-------------|-----------|
| Loading spinner design? | **Defer to demo review** | Ship without spinner. Loading state variable wired in store. Visual indicator added post-review. |
| Error display format? | **Parse backend JSON, show message + trace ID** | No raw JSON dumps. Structured error with trace ID for debugging. |
| Empty state copy? | **"No [items] found" with context** | Generic but functional. PO can refine copy on MR review. |
| Confirmation prompt for destructive action? | **`window.confirm()` with clear message** | Simple, built-in, works everywhere. Custom modal is additive later. |
| Component display order? | **Match navigation order** | Users expect consistency between nav and content. |

### Scope & Feature Cuts

| Blocker | Safe Default | Rationale |
|---------|-------------|-----------|
| Mockup includes features beyond AC? | **Cut to AC scope, document cuts** | Record in `ac-tracking.yaml → scope_cuts`. PO sees what was excluded. |
| Audit log for admin actions? | **Defer (separate ticket)** | Audit logging is cross-cutting. Not blocking for v1 ship. |
| Bulk operations? | **Defer (separate ticket)** | Single-item workflow first. Bulk is additive. |
| Role-based access beyond isAdmin? | **Gate by `isAdmin()` only for v1** | Simplest gate that prevents unauthorized access. Component-level gating is additive. |

### Data & Integration

| Blocker | Safe Default | Rationale |
|---------|-------------|-----------|
| Which existing component to extend? | **Create new, don't modify existing** | Avoids regression in working code. New component is isolated. |
| Cache TTL? | **12 hours** | Safe middle ground. Short enough to reflect changes, long enough to avoid unnecessary load. |
| Partial failure handling (multi-step create)? | **Two-call with recovery UI** | Option B pattern: first call creates, second call configures. Recovery component handles partial state. |
| Zero-state allowed? | **Yes, with confirmation prompt** | "Revoke all access?" confirm prevents accidental deletion. Functional, simple. |

## Seeded From

- **KTP-499 (2026-04-10):** 8 blocker defaults applied during overnight ship:
  - Q1: Invite-email notice in New User modal
  - Q2: `isAdmin()` gate only for v1
  - Q3: Deferred partial-state cleanup
  - Q4: Cut bulk invite, templates, audit log, agency CRUD
  - Q5: Component seed resolved via migration
  - Q6: Option B (two-call + recovery modal)
  - Q7: Scope count dropped from list view
  - Q8: Zero scopes allowed with confirm prompt

## Updating This Playbook

After each successful autonomous ship, review `ac-tracking.yaml → blockers_defaults_applied` for new patterns. If a default was accepted by the PO without pushback, it validates the pattern. If pushed back, record the correction as a counter-example.
