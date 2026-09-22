# Skill Proposal: layered-domain-review
Date: 2026-08-25
Source: session steady-crane — 97-ticket sprint review at three abstraction layers

## Trigger
A sprint or epic needs review at more than one altitude: per-ticket rigor for correctness,
plus a domain-owner view and an architect/team-lead synthesis. Triggers on "review the whole
sprint", "I need the architect view", "what's the state of my domains".

## Scope
Org (Klever first; the domain registry is org-specific, the method is not).

## Why it is not just a prompt
The value is not summarization, it is a **frame change**. Layer 2 must consult a source layer 1
did not. Proven this run: 3 of 7 domain owners caught layer-1 errors, including one that had
survived five same-frame adversarial passes. A summarizing layer 2 would have repeated the
error more fluently. That property has to be enforced by protocol, not hoped for.

## Draft Steps
1. Resolve domains from `documentation/bibliotheque/surfaces/domains.yaml`; fail closed if a
   ticket maps to no domain rather than silently dropping it.
2. L1: per-ticket adversarial review against AC, with fixed verdict enums and mandatory
   VERIFIED/UNVERIFIED evidence labels.
3. L2: one owner agent per domain. Mandatory `## Layer-1 delta` section; at least one re-check
   must name an instrument L1 did not use.
4. L3: two readers, not one — architect (structural findings, cross-domain patterns) and team
   lead (who is blocked on whom, delivery risk). Must read every L2 delta block first; a claim
   marked CORRECTED may not reappear.
5. Score the frame-change claim with `tools/l2-frame-change-eval` rather than asserting it.

## Existing assets
- `reports/close-out-2026-08-07/sprint-attack-2026-08-09/L2-PROTOCOL.md` (the L2 contract)
- `.../REVIEWER-PROTOCOL.md` (the L1 contract)
- `tools/l2-frame-change-eval/` (13-point eval; selftest passes a correct agent and fails both
  a lazy and a trigger-happy one)
- `documentation/bibliotheque/surfaces/domains.yaml` (8 domains, provisional-in-use)
