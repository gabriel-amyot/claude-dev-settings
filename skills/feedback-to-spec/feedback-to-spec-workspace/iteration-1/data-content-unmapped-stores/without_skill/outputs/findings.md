# Findings: Unmapped Store State — UX Feedback 2026-05-04

## Source
- Ticket: KTP-130 Phase 2 (Store Detail Panel)
- Screenshot: `tickets/KTP/KTP-130/design/screenshots/ux-feedback-2026-05-04/sbe2-unmapped-locations.png`
- Store triggering the issue: Shrimp Basket Gulf Breeze (5 Via De La Luna Dr, Gulf Breeze)

---

## What the Screenshot Shows

The store detail panel opens with the correct store name and address in the header. Below the header, two lines of gray text appear on an otherwise empty panel:

- Line 1 (medium gray, `text-sm`): "This location is not yet mapped in Placer.ai."
- Line 2 (light gray, `text-xs`): "Foot traffic data will appear once the location is onboarded via the 'Request POI' process."

No button, link, or action affordance is present. The panel is otherwise empty — no campaign data, no metrics, nothing.

---

## Findings

### F-1: Dead-end state — no actionable path forward

**Severity:** High

The message describes a solvable problem but provides no way to act on it. The user is told that onboarding is possible ("will appear once onboarded") but given no mechanism to initiate it. This is a dead end: the user reads the message, understands nothing can be done from here, and closes the panel.

**What the user would expect:** A button or link to request the data, or at minimum a clear indication of what to do next (e.g., "Contact your account manager").

---

### F-2: Jargon-heavy copy — "Placer.ai" and "POI" are internal terms

**Severity:** Medium

Two internal/technical terms appear in user-facing copy:

- **"Placer.ai"** — the data vendor. Not meaningful to most advertiser users; they don't care where the data comes from, only that it's missing.
- **"POI" (Point of Interest)** — industry jargon. A non-technical user reading "Request POI process" has no idea what this means or what they're requesting.
- **"onboarded via the Request POI process"** — the phrase reads like an internal ops ticket description, not a user-facing message. It implies a multi-step process the user doesn't control and doesn't explain.

---

### F-3: Message is two sentences when one word would suffice

**Severity:** Low-Medium

The current message is 30+ words across two lines to convey what amounts to: "No data yet." The second sentence ("Foot traffic data will appear once...") is aspirational filler — it doesn't help the user take action and adds cognitive load. In a narrow side panel, verbose empty states compete visually with legitimate content in adjacent stores.

---

### F-4: No permission-gated action hook

**Severity:** Medium (scoping/design concern)

Gabriel's feedback mentions showing a "Request data" link only if the user has permission. The current implementation has no hook for this. The `StoreDetailPanel` reads from `useMapStore()` but has no access to user role or permission context. There is no existing "request POI" flow anywhere in the frontend.

This means the CTA (when built) needs:
1. A permission check before rendering (likely tied to the "Measurement" or "Proximity" component permission from `lib/permissions/constants.ts`)
2. A destination (currently non-existent — either a modal, a mailto link, or a Jira-style form)

---

## Code Location

**File:** `components/map/components/store-detail-panel.tsx`

**Lines 958–968** — the unmapped state block inside the main `StoreDetailPanel` component:

```tsx
{!storeMetricsLoading && !storeMetricsError && storeMetrics && !storeMetrics.mapped && (
  <div className="p-4">
    <p className="text-sm text-gray-500">
      This location is not yet mapped in Placer.ai.
    </p>
    <p className="text-xs text-gray-400 mt-1">
      Foot traffic data will appear once the location is onboarded via the &ldquo;Request
      POI&rdquo; process.
    </p>
  </div>
)}
```

**Trigger condition:** `storeMetrics.mapped === false` — set by the backend when a store location has no Placer.ai POI match.

**No existing "Request POI" frontend flow** was found in the codebase. The term appears only in backend API routes (`/api/map/data/state/route.ts`, `/api/map/data/locations/route.ts`) in a different context (query parameters), not as a user-facing process.

---

## Summary Table

| # | Finding | Severity | Lines |
|---|---------|----------|-------|
| F-1 | Dead end: no actionable CTA | High | 958–968 |
| F-2 | Jargon: "Placer.ai", "POI", "onboarded" | Medium | 960–966 |
| F-3 | Overly verbose for an empty state | Low-Medium | 960–966 |
| F-4 | No permission hook for conditional CTA | Medium | N/A (missing) |
