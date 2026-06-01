# Specifications: Unmapped Store State — Store Detail Panel

**Epic:** KTP-130 Phase 2
**Component:** `StoreDetailPanel` — unmapped location state
**Source feedback:** Gabriel, 2026-05-04
**File to modify:** `components/map/components/store-detail-panel.tsx` (lines 958–968)

---

## Overview

Replace the current two-sentence jargon-heavy dead-end message with a concise label and a permission-gated "Request data" action link.

---

## Spec 1: Rewrite the unmapped store copy

### Current

```
"This location is not yet mapped in Placer.ai."
"Foot traffic data will appear once the location is onboarded via the 'Request POI' process."
```

### Required

Primary label (replaces both sentences):

```
No foot traffic data yet.
```

Optional sub-label (only if NO action link is rendered — i.e., user lacks permission):

```
Contact your account manager to request store data.
```

### Rationale

- Removes "Placer.ai" and "POI" — vendor and internal jargon not meaningful to advertiser users.
- Removes the aspirational second sentence — it adds length without helping the user act.
- "No foot traffic data yet" follows the same pattern as other empty states in the panel (e.g., "No campaign data available for this store's trade area.").

---

## Spec 2: Add a permission-gated "Request data" link

### Behavior

When the store is unmapped (`storeMetrics.mapped === false`), render a small inline action link below the primary label. The link is only shown if the current user has a specific permission (see Permission Gate below).

### Rendered output (with permission)

```
No foot traffic data yet.   [Request data →]
```

Layout: primary label and link on the same line, or label on one line and link immediately below — either is acceptable. The link should be visually subtle (small, muted color, underlined on hover) — not a full button. It should not dominate the panel.

### Rendered output (without permission)

```
No foot traffic data yet.
Contact your account manager to request store data.
```

### Link destination

**Phase 2a (MVP):** The link opens a pre-filled `mailto:` — e.g.:

```
mailto:support@beklever.com?subject=Store data request&body=Store: {location.name}%0AAddress: {location.address}
```

The store name and address should be injected from `location.name` and `location.address` (already available in scope via `useMapStore()`).

**Phase 2b (future):** Replace the `mailto:` with a modal form or an in-app request flow. This is out of scope for the current ticket but the link should be designed so its `onClick` handler can be swapped without changing surrounding markup.

### Permission gate

Use an existing permission component or check from `lib/permissions/`. The gating condition should be:

- The user has the "Measurement" component permission (component name as defined in `COMPONENT_DISPLAY_ORDER` in `lib/permissions/constants.ts`)
- OR an `isAdmin` / `canManageLocations` flag if one is introduced

**Open question for implementation:** No user-role hook currently exists in `StoreDetailPanel` or `useMapStore`. The implementation will need to either:
1. Thread a `canRequestData: boolean` prop down from the parent (preferred — keeps the panel dumb), or
2. Pull user permissions from a session context hook (if one exists in the app's auth layer)

This decision should be resolved before implementation starts. Lean toward option 1 for testability.

---

## Spec 3: Visual design of the unmapped state block

### Container

Keep the existing `<div className="p-4">` wrapper. No visual change to the container.

### Primary label

```tsx
<p className="text-sm text-gray-500">No foot traffic data yet.</p>
```

Same style as the current primary text — no visual regression.

### Action link (with permission)

```tsx
<button
  className="text-xs text-blue-500 hover:text-blue-700 underline mt-1 block"
  onClick={onRequestData}
>
  Request data
</button>
```

Or an `<a>` tag if using `mailto:`. Use whichever matches the app's pattern for inline text actions.

### Fallback sub-label (without permission)

```tsx
<p className="text-xs text-gray-400 mt-1">
  Contact your account manager to request store data.
</p>
```

---

## Acceptance Criteria (draft — Leo-style)

**AC-1: Simplified copy**

Given a store with `storeMetrics.mapped === false`,
When the store detail panel is open,
Then the panel shows "No foot traffic data yet." and does NOT contain the words "Placer.ai", "POI", or "onboarded".

**AC-2: Action link shown with permission**

Given a store with `storeMetrics.mapped === false`,
And the current user has the required permission to request store data,
When the store detail panel is open,
Then a "Request data" link is visible below the primary label.

**AC-3: Action link hidden without permission**

Given a store with `storeMetrics.mapped === false`,
And the current user does NOT have the required permission,
When the store detail panel is open,
Then no "Request data" link is visible, and a soft fallback message appears instead.

**AC-4: Action link initiates a request**

Given the "Request data" link is visible and clicked,
Then the link opens a pre-filled email (or modal) referencing the store name and address,
And the user can complete or cancel the request without leaving the map view.

---

## Out of Scope

- Building a full POI request workflow (form, API, tracking) — that is KTP-608 (Amal: POI onboarding).
- Changing the backend `mapped` flag logic.
- Changing behavior for mapped stores or the error state (`storeMetricsError`).

---

## Files to Change

| File | Change |
|------|--------|
| `components/map/components/store-detail-panel.tsx` | Replace unmapped state block (lines 958–968) with new copy + conditional CTA |
| `components/map/store/map-store.ts` | No change needed — `storeMetrics.mapped` flag already exists |
| `lib/permissions/constants.ts` | Possibly add a permission name constant if new gate is introduced |

---

## Open Questions

1. **Permission hook:** What is the correct way to read the current user's component permissions inside a map component? Is there a session context, a hook, or should this be passed as a prop from the parent? Resolve before implementation.
2. **Link destination:** Is `mailto:` acceptable for MVP or should this go to an internal form (KTP-608 scope)? Gabriel to confirm.
3. **Whose email?** If using `mailto:`, who is the recipient — `support@beklever.com`, a CS team alias, or the advertiser's account manager? Needs a business decision.
