# Feedback Extraction — KTP-130 Unmapped Stores
<!-- Phase 1 / Step 1 output -->
<!-- Date: 2026-05-06 -->
<!-- Epic: KTP-130 (Klever Measurement Map — Phase 2, Store Detail Panel) -->

## Screenshot

`tickets/KTP/KTP-130/design/screenshots/ux-feedback-2026-05-04/sbe2-unmapped-locations.png`

**What the screenshot shows:**
The Store Detail Panel is open for "Shrimp Basket Gulf Breeze" (5 Via De Luna Dr). The panel body displays two lines of text in gray:
1. "This location is not yet mapped in Placer.ai."
2. "Foot traffic data will appear once the location is onboarded via the "Request POI" process."
There is no button, link, or any interactive element. The panel is otherwise empty — no metrics, no charts, no call to action.

---

## Raw Findings

```
FINDING-1:
  screenshot: sbe2-unmapped-locations.png
  quote: "That message is technically correct but it's a dead end for the user. There's no button to actually request the POI."
  observation: The unmapped-location state renders two lines of explanatory text with zero interactive elements. Users who want to trigger the onboarding process have no path forward from this panel.
  issue: The unmapped-store message provides no action — the user hits a dead end with no way to request POI onboarding.
  expected: A "Request data" link or button that lets the user initiate the POI onboarding request directly from the panel.
  category: MISSING_FEATURE
  severity: P1_HIGH

FINDING-2:
  screenshot: sbe2-unmapped-locations.png
  quote: "The message is way too long and technical. A normal user doesn't know what POI means. This should just say something like 'No foot traffic data yet'."
  observation: The copy uses "Placer.ai", "onboarded", and "POI" — internal/vendor terminology not meaningful to a store-level user.
  issue: The unmapped-store message uses jargon ("POI", "Placer.ai", "onboarded") that the target user (media buyer / store operator) does not understand.
  expected: Plain-language copy: "No foot traffic data yet" as the headline, with a short secondary line if needed.
  category: UX
  severity: P1_HIGH
```

---

## Mary's Discipline Audit

**Finding count check:** Gabriel described 2 distinct problems (dead end / no action, jargon-heavy copy). 2 findings extracted. Count matches. No collapse needed.

**Inferred vs stated:**
- FINDING-1: Stated explicitly ("no button to actually request the POI"). Passes.
- FINDING-2: Stated explicitly ("way too long and technical", "A normal user doesn't know what POI means"). Passes.

**Business intent check:**
- FINDING-1: A user who sees an unmapped store cannot take any action to get data for that store. The panel ends the conversation without enabling next steps.
- FINDING-2: A user reading the current message cannot parse its meaning. They don't know what they're being told or what they should do about it.

Both findings have clear business intent. No demotion needed.

**Note — permission qualifier:** Gabriel said "a small 'Request data' link if they have permission." This implies the CTA may be role-gated. Code trace (see below) confirms no role prop is passed to `StoreDetailPanel` today. This is a `[CLARIFY]` point, captured in SBE-1.

---

## Code Trace

### FINDING-1 — Missing CTA
```
file: components/map/components/store-detail-panel.tsx
lines: 958–968
component: StoreDetailPanel (anonymous JSX block, unmapped state)
fix_scope: FRONTEND_ONLY
notes:
  - The unmapped-state block is a hardcoded <div> with two <p> tags. No interactivity.
  - StoreDetailPanel takes no role/permission props (line 872). It pulls from useMapStore() only.
  - No Request-POI page, modal, API route, or mailto link exists anywhere in the repo.
  - A "Request data" CTA will need a target: either a modal, an email link, or a route. The destination is undefined and requires clarification from Gabriel before implementation can begin.
  - The permission system (lib/permissions/constants.ts, typedefs.ts) has a `role` field on UserPermissions, and the proximity-map page already receives permissions info server-side (proximity-map.tsx imports StoreDetailPanel at line 236). Role could be threaded through if needed.
  - [CLARIFY] What does "Request data" do? Options: mailto link, in-app form, Jira-style request flow. Gabriel's "if they have permission" implies only some users see the CTA — which role qualifies?
```

### FINDING-2 — Jargon copy
```
file: components/map/components/store-detail-panel.tsx
lines: 960–966
component: StoreDetailPanel (anonymous JSX block, unmapped state)
fix_scope: FRONTEND_ONLY
notes:
  - Line 961: "This location is not yet mapped in Placer.ai." — contains vendor name "Placer.ai" and implies a data vendor relationship the user is not expected to know.
  - Lines 963–965: "Foot traffic data will appear once the location is onboarded via the 'Request POI' process." — "onboarded", "POI", and "Request POI process" are all internal terms.
  - Fix is a pure copy change. No logic, no props, no backend involved.
  - Gabriel's suggested copy ("No foot traffic data yet") maps directly to a replacement for line 961. The secondary line can be simplified to something like "Data becomes available once this store is enrolled." or dropped entirely once a CTA is present.
```
