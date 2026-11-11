# Skill Proposal: proposal-factcheck (pre-meeting stakeholder-proposal → code fact-check)
Date: 2026-07-07
Source: Session quiet-badger — fact-checking Rajan's (PO) Proximity 3-mode design proposal before a brainstorm

## Trigger
A PO/stakeholder (especially new or non-technical) hands a design/build proposal — a "design implementation", PRD-ish checklist, or feature list — often tagged with effort (S/M/L) and Reuse-vs-New, and there's a meeting to review it. User says things like "review this before the meeting", "is this feasible", "he sized these — are the estimates real", "map this to our code".

## Scope
org (Klever-first; generalizable). Read-only. Produces a scoping artifact, never code or tickets.

## Draft Steps
1. Ingest the proposal; extract its concept taxonomy (sections/items). Treat every Reuse/New + effort tag as a **claim to verify**, not a fact.
2. Fan out parallel **read-only** exploration agents, one per concern area (e.g. shell/nav, map, insights, permissions, BI). Give each the relevant items verbatim + a fixed output format.
3. Each agent maps every assigned item to: VERDICT (EXISTS / PARTIAL / ABSENT) · code anchors (path:line) · "reality vs the stakeholder's tag" · effort agree/disagree · unknowns for the stakeholder.
4. Assemble a concept→code index on disk (`general/scoping/{topic}/`), with a ★ headline section surfacing the inversions (items tagged "New" already built; "Reuse/small" items hiding backend/data work) and the load-bearing unknowns.
5. Optionally convene PM/Architect(/PO-function) persona pass to resolve the index into a meeting topic/question list.
6. Fold as a pending initiative (README + handoff) if it parks awaiting stakeholder input.

## Notes
- Verify against `origin/<deploy-branch>`, not a stale local — and re-read actual files when a claim is challenged (a broad subagent summary missed `middleware.ts` + the route-gate split this session).
- Keep it read-only; no tickets, no code. The output gives engineering the New/Reuse call back.
