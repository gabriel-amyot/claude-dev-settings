# Skill Proposal: spec-contradiction-sweep
Date: 2026-08-19
Source: KTP-1062/1065 Powers TTD write path (session lucid-crane)

## Trigger

Before implementing against a spec, plan, or ADR set that accumulated over more than two sessions — especially when several agents wrote parts of it independently. Also when a build "keeps getting snagged" on the same feature across sessions.

## The failure it prevents

A single bid write took roughly three weeks across eight sessions. At least four contradictions between the plan and the code were each discovered separately, hours apart, by hitting them at runtime:

- `WriteFeatureStartupGuard` required a loopback bind, while the install plan written the same week said the operator would apply "through the DEPLOYED gateway (no local media-api)."
- `CONFINED_CLIENT_ROUTES` admitted only the read route, so the credential could not reach a bid route through that gateway either.
- A handoff named an Auth0 grant as the blocker; the grant was already live.
- ADR-0008 asserted "the environment is derived from the seat"; `application-prod.properties` disproves it.

Every one was readable statically. Nobody had read the plan and the code side by side in a single pass.

## Scope

Global. The pattern is not Klever-specific — it applies wherever a multi-session spec meets an implementation.

## Draft Steps

1. **Collect the claim surface.** Take the plan/spec doc, the ADRs it references, and any handoffs for the same ticket. Extract every statement that asserts what the system *does* or *requires* — not what it should eventually do.
2. **Map each claim to its implementing code.** For each claim, find the file and line that would make it true. A claim with no implementing code is finding type A (aspirational, mislabelled as current).
3. **Read the code's own constraints back out.** For the code found in step 2, list what it *actually* enforces. A constraint the code enforces that no doc mentions is finding type B (undocumented gate).
4. **Diff the two lists.** Anything where doc and code disagree is finding type C (contradiction). Rank by whether it blocks the stated goal.
5. **Report before building.** Output the contradictions with file:line evidence and a verdict per item: doc wrong, code wrong, or genuine open decision. Do not fix anything in this pass.

## Why a skill rather than a CLAUDE.md rule

The value is in the mechanical completeness of steps 1–3. A prose rule ("check for contradictions") does not produce the claim inventory, and that inventory is the thing that makes contradictions visible in one pass instead of four runtime failures.

## Open question

Overlap with `agent-os:audit-docs`, which audits a repo's `agent-os/` tree for staleness. That one is repo-scoped and doc-vs-doc; this one is plan-vs-code and spans repos. They may want merging rather than coexisting — decide before building.
