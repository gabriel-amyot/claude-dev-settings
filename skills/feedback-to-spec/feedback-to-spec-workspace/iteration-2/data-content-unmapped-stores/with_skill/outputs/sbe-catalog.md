# SBE Catalog — KTP-130 Unmapped Store Message
<!-- Phase 1 / Step 3 output — DRAFT, pending confirmation -->
<!-- Date: 2026-05-06 -->
<!-- Epic: KTP-130 (Klever Measurement Map — Phase 2, Store Detail Panel) -->
<!-- Source screenshot: sbe2-unmapped-locations.png -->

---

### SBE-1: Unmapped store panel shows a "Request data" CTA

**Context:** Gabriel is clicking through stores on the Measurement Map. He opens "Shrimp Basket Gulf Breeze" and sees the unmapped-location state — no metrics, just a dead-end message. He expects users to be able to request that foot traffic data gets set up for that store.

GIVEN the user is viewing the Store Detail Panel for a location
  AND the location is not yet onboarded in the data pipeline (`storeMetrics.mapped === false`)

WHEN the unmapped-location state renders
THEN a "Request data" link or button is visible in the panel body
  AND [CLARIFY] the CTA is either always visible or gated behind a role check (Gabriel said "if they have permission" — confirm which roles see it and which do not)
  AND clicking the CTA initiates the POI onboarding request (mechanism TBD — mailto, modal, or form)

**Current behavior:** The panel renders two lines of explanatory text only. No CTA, no link, no button. Users have no action to take.

**Root cause:** `components/map/components/store-detail-panel.tsx` lines 958–968 — the unmapped-state block is a hardcoded `<div>` with two `<p>` elements and no interactive elements. No Request-POI flow exists anywhere in the repo.

**Fix scope:** FRONTEND_ONLY (frontend CTA wiring; backend POI-request endpoint is out of scope for this SBE unless Gabriel specifies otherwise)

**Open questions:**
- `[CLARIFY]` What is the action target? Options: `mailto:` link pre-filled with store name, in-app modal, or a dedicated request form.
- `[CLARIFY]` Which users see the CTA? Gabriel said "if they have permission." Does this map to a specific role (e.g. Klever admin / agency admin only)?

---

### SBE-2: Unmapped store panel displays plain-language copy instead of jargon

**Context:** Same panel state as SBE-1. Gabriel reads the current message and finds it too technical for the intended audience (media buyers, store-level users who do not know what "POI" or "Placer.ai" means).

GIVEN the user is viewing the Store Detail Panel for a location
  AND the location is not yet onboarded in the data pipeline (`storeMetrics.mapped === false`)

WHEN the unmapped-location state renders
THEN the primary message reads: "No foot traffic data yet" (or equivalent plain-language phrasing Gabriel approves)
  AND the message contains no vendor names ("Placer.ai"), no internal terms ("POI", "onboarded"), and no reference to process names ("Request POI process")
  AND any secondary line is either removed or rewritten in plain language (e.g. "Data will appear once this store is enrolled.")

**Current behavior:**
- Line 1: "This location is not yet mapped in Placer.ai." — contains vendor brand and implies a data mapping concept the user is not expected to know.
- Line 2: "Foot traffic data will appear once the location is onboarded via the 'Request POI' process." — contains three jargon terms.

**Root cause:** `components/map/components/store-detail-panel.tsx` lines 960–966 — hardcoded strings with internal/vendor terminology.

**Fix scope:** FRONTEND_ONLY (pure copy change, no logic or props required)

**Note:** If SBE-1 is implemented, the secondary line in SBE-2 may be replaced entirely by the CTA. These two SBEs are related but independent — SBE-2 can ship without SBE-1 (better message, still no action), and SBE-1 can ship without SBE-2 (action present, jargon still there). Ship together for full fix.

---

## Summary Table

| SBE | Title | Category | Severity | Fix scope | Blocker? |
|-----|-------|----------|----------|-----------|----------|
| SBE-1 | Unmapped store panel shows a "Request data" CTA | MISSING_FEATURE | P1_HIGH | FRONTEND_ONLY | Needs clarification on CTA target + role gate before implementation |
| SBE-2 | Unmapped store panel displays plain-language copy | UX | P1_HIGH | FRONTEND_ONLY | No — can implement immediately |

---

## Disposition

- SBE-2 is ready to implement: file, lines, and replacement copy are all known.
- SBE-1 needs two clarifications before coding can start: what does "Request data" do, and which roles see it. These are blocking design questions, not engineering questions.
