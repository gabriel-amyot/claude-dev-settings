# SBE Catalog — Unmapped Store Empty State
**Epic:** KTP-130 (Klever Measurement Map — Phase 2)
**Date:** 2026-05-04
**Status:** DRAFT — awaiting Step 4 confirmation
**Author:** Mary (Business Analyst lens via feedback-to-spec)

---

## Summary

Two SBEs extracted from one screenshot and one narration session.
Both target `components/map/components/store-detail-panel.tsx` lines 958-968.
FRONTEND_ONLY scope for both.

| SBE | Title | Category | Severity | Fix scope |
|-----|-------|----------|----------|-----------|
| SBE-1 | Plain-language empty state copy for unmapped stores | UX | P2_MEDIUM | FRONTEND_ONLY |
| SBE-2 | Conditional "Request data" CTA in unmapped store panel | MISSING_FEATURE | P1_HIGH | FRONTEND_ONLY |

---

## SBE-1: Plain-language empty state copy for unmapped stores

**Context:** Gabriel clicked on a Shrimp Basket location in the Measurement Map. The store detail panel opened. The store has no Placer.ai data. The panel displayed a two-line message using internal vendor and technical jargon ("Placer.ai", "POI", "onboarded via the Request POI process"). Gabriel's reaction: "technically correct but a dead end" and "a normal user doesn't know what POI means."

GIVEN the user is viewing the store detail panel
  AND the selected store has `storeMetrics.mapped === false`
  AND no error is present (`storeMetricsError` is null)

WHEN the panel renders the empty state for foot traffic data
THEN the panel displays a single, plain-language message: "No foot traffic data yet."
  AND no vendor names (Placer.ai) or technical terms (POI, onboarded) appear in the visible text

**Current behavior:** Two-line block at lines 961-965 of `store-detail-panel.tsx` renders:
- "This location is not yet mapped in Placer.ai."
- "Foot traffic data will appear once the location is onboarded via the 'Request POI' process."

**Root cause:** Hardcoded copy written from an engineering/internal perspective, not a user-facing perspective. No content design pass was done on this state.

**Fix scope:** FRONTEND_ONLY

**Files:** `components/map/components/store-detail-panel.tsx` lines 960-966

**Notes:** The second sentence can be removed entirely once SBE-2 introduces a "Request data" CTA (the CTA replaces the aspirational sentence about the process). If SBE-2 is deferred, the second sentence should be replaced with "Data can be requested by your Klever account team." until the CTA exists.

---

## SBE-2: Conditional "Request data" CTA in unmapped store panel

**Context:** Gabriel observed that the unmapped store state panel has no way for the user to act. The current message references a "Request POI" process but provides no mechanism. Gabriel explicitly said: "There's no button to actually request the POI" and proposed: "a small 'Request data' link if they have permission."

GIVEN the user is viewing the store detail panel
  AND the selected store has `storeMetrics.mapped === false`
  AND no error is present
  AND the current user has [CLARIFY: permission to request POI onboarding — see below]

WHEN the panel renders the unmapped empty state
THEN a "Request data" link is displayed below the "No foot traffic data yet." message
  AND clicking the link [CLARIFY: initiates the request flow — see below]

GIVEN the user is viewing the store detail panel
  AND the selected store has `storeMetrics.mapped === false`
  AND the current user does NOT have the required permission

WHEN the panel renders the unmapped empty state
THEN only the "No foot traffic data yet." message is shown
  AND no CTA is rendered

**Current behavior:** No interactive element in the unmapped state block. No permission check exists in this path.

**Root cause:** The unmapped state block (lines 958-968 of `store-detail-panel.tsx`) is a static text block with no action wiring and no permission check. The component does not import `useOrgBrandProvider` (permission context hook).

**Fix scope:** FRONTEND_ONLY

**Files:** `components/map/components/store-detail-panel.tsx` lines 958-968, plus `app/(frontend)/context/AppProvider.tsx` (read-only, existing hook)

---

### CLARIFY tags for SBE-2

**[CLARIFY-A] — What permission gates the "Request data" CTA?**

Mary's interpretation from Gabriel's words ("if they have permission"):
> The CTA should only be visible to Klever internal users or agency admins, not end-advertiser users.

Three options to confirm:
1. Gate on `permissionComponents.some(p => p.name === "ALL")` — Klever-internal only (simplest, no new component needed)
2. Gate on a new `PermissionComponent` named e.g. `"RequestPOI"` or `"POI Onboarding"` — explicit, requires a User Management backend entry
3. Gate on any user with Measurement Map access — broadest, least safe

Proposed default: **Option 1 (ALL)** until there is a defined POI request role.

---

**[CLARIFY-B] — What does clicking "Request data" do?**

No POI request flow exists in the codebase. Options:
1. Opens a mailto link: `mailto:support@beklever.com?subject=POI Request — {storeName}` (zero backend, ships fastest)
2. Opens a modal/drawer with a simple request form (requires new backend endpoint)
3. Links to an external Jira/Notion form (fragile, environment-specific)
4. Placeholder: shows a toast "Your account team has been notified" (deferred real action)

Proposed default: **Option 1 (mailto)** as Phase 2 MVP. A proper form workflow can follow as a separate ticket.

Gabriel said "small 'Request data' link" — this language supports option 1 (styled as an anchor link, not a primary button).

---

### Implementation sketch (not spec, for reference)

```tsx
// In the unmapped state block at lines 958-968:
{!storeMetricsLoading && !storeMetricsError && storeMetrics && !storeMetrics.mapped && (
  <UnmappedStoreState storeId={selectedLocationId} storeName={selectedLocationName} />
)}

// New sub-component:
const UnmappedStoreState = ({ storeId, storeName }) => {
  const { permissionComponents } = useOrgBrandProvider();
  const canRequestPOI = permissionComponents.some(p => p.name === "ALL");

  return (
    <div className="p-4">
      <p className="text-sm text-gray-500">No foot traffic data yet.</p>
      {canRequestPOI && (
        <a
          href={`mailto:support@beklever.com?subject=POI Request — ${encodeURIComponent(storeName)}`}
          className="text-xs text-blue-600 hover:underline mt-1 block"
        >
          Request data
        </a>
      )}
    </div>
  );
};
```

This sketch is illustrative only. It is not a confirmed implementation plan.
