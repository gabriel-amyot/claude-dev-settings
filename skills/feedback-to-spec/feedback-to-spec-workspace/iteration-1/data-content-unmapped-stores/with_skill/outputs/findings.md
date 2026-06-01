# Feedback Extraction — Unmapped Store State
**Epic:** KTP-130 (Klever Measurement Map — Phase 2)
**Date:** 2026-05-04
**Extracted by:** feedback-to-spec skill, Phase 1 Steps 1-2

---

## Step 1: Ingest

### Screenshot Observation

**File:** `tickets/KTP/KTP-130/design/screenshots/ux-feedback-2026-05-04/sbe2-unmapped-locations.png`

The panel shows the store "Shrimp Basket Gulf Breeze" at "5 Via De Luna Dr, Gulf Breeze". Below the store header, the panel displays two lines of text:

- Primary (gray, medium): "This location is not yet mapped in Placer.ai."
- Secondary (gray, small): "Foot traffic data will appear once the location is onboarded via the 'Request POI' process."

There is no interactive element. No button, no link, no call to action. The panel is a dead end.

---

### Raw Findings

```
FINDING-1:
  screenshot: sbe2-unmapped-locations.png
  quote: "the message is way too long and technical. A normal user doesn't know what POI means."
  observation: Two-line message uses internal terminology: "Placer.ai", "POI", "onboarded", "Request POI process"
  issue: The empty state copy exposes vendor names and internal jargon that end-users have no context for.
  expected: Plain-language copy — something like "No foot traffic data yet" — that communicates the state without vendor/technical terms.
  category: UX
  severity: P2_MEDIUM

FINDING-2:
  screenshot: sbe2-unmapped-locations.png
  quote: "it's a dead end for the user. There's no button to actually request the POI."
  observation: The unmapped state renders a text block with no interactive element. The message references a "Request POI process" but provides no mechanism to initiate it.
  issue: Users with permission to request data onboarding have no way to act from this panel.
  expected: A "Request data" link or button that initiates the POI request flow, visible only to users with the appropriate permission.
  category: MISSING_FEATURE
  severity: P1_HIGH

FINDING-3:
  screenshot: sbe2-unmapped-locations.png
  quote: "if they have permission" (implicit scope constraint from Gabriel's narration)
  observation: No permission check present in the unmapped state block at all.
  issue: The CTA should only appear for users who have permission to request POI onboarding. No permission-gating exists for this state.
  expected: "Request data" CTA is conditionally rendered based on user role or permission component.
  category: UX
  severity: P2_MEDIUM
```

---

## Step 2: Code Trace

### Search terms used
- `not yet mapped`, `Placer.ai`, `Request POI`, `onboarded`, `mapped`, `placerId`, `placer_id`
- `requestPOI`, `request.*poi`, `REQUEST_POI`
- `useOrgBrandProvider`, `permissionComponents`, `usePermissions`, `hasPermission`, `isAdmin`

### Trace: FINDING-1 — Jargon-heavy copy

```
code_trace:
  file: components/map/components/store-detail-panel.tsx
  lines: 958-968
  component: StoreDetailPanel (main panel render, inline conditional block)
  fix_scope: FRONTEND_ONLY
  notes: |
    The unmapped state is rendered at lines 958-968:
      {!storeMetricsLoading && !storeMetricsError && storeMetrics && !storeMetrics.mapped && (
        <div className="p-4">
          <p className="text-sm text-gray-500">
            This location is not yet mapped in Placer.ai.
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Foot traffic data will appear once the location is onboarded via the "Request POI" process.
          </p>
        </div>
      )}
    Fix: replace both <p> strings with user-facing copy. No logic change needed.
```

### Trace: FINDING-2 — Missing CTA

```
code_trace:
  file: components/map/components/store-detail-panel.tsx
  lines: 958-968
  component: StoreDetailPanel (same unmapped block as FINDING-1)
  fix_scope: FRONTEND_ONLY
  notes: |
    There is no button, link, or onClick handler in this block.
    The "Request POI" process is referenced in copy only — no route, modal, or action exists.
    A "Request data" link/button needs to be added to this block.
    No backend endpoint for this action was found in the frontend repo. The action target
    (mailto, modal, external form, or internal route) is UNKNOWN — marked CLARIFY below.
    Permission infrastructure IS available: useOrgBrandProvider() exposes permissionComponents
    from AppProvider (app/(frontend)/context/AppProvider.tsx lines 228-236).
    The component does NOT currently import useOrgBrandProvider. It would need to be added.
```

### Trace: FINDING-3 — Permission gate missing

```
code_trace:
  file: components/map/components/store-detail-panel.tsx + app/(frontend)/context/AppProvider.tsx
  lines: 958-968 (panel) + 228-236, 258-268 (AppProvider)
  component: StoreDetailPanel + AppProvider
  fix_scope: FRONTEND_ONLY
  notes: |
    The permission system is fully operational: useOrgBrandProvider() returns permissionComponents[]
    from the AppContext (AppProvider.tsx line 300-319). The isAllowed() pattern (line 258) checks
    permissionComponents.some(p => p.name === name).
    store-detail-panel.tsx does NOT import useOrgBrandProvider. No permission check exists
    for the unmapped state CTA.
    The specific permission component name for "Request POI" does NOT exist yet — this is a
    new permission or it maps to an existing admin-level component (e.g. "ALL").
    [CLARIFY] — What permission component should gate the "Request data" CTA?
    Options: (a) "ALL" (Klever internal only), (b) a new "RequestPOI" component,
    (c) any user with Measurement access can see it.
```

### Trace: No existing Request POI flow found

Searched across the entire frontend repo for `requestPOI`, `request_poi`, `REQUEST_POI`, `request.*poi` — no matches. The POI request flow does not exist in this codebase. The copy in the current unmapped state is aspirational text pointing to a process that is not yet implemented in the UI.

This means FINDING-2 and FINDING-3 are dependent on a design decision about what the "Request data" action does. See CLARIFY tags in the SBE catalog.
