# Skill Proposal: bmad-epic-lifecycle
Date: 2026-04-21
Source: KTP-525 feedback widget autonomous session

## Trigger
User says "conceptualize and implement this feature", "full lifecycle for this epic", "BMAD end-to-end", or describes a feature that needs concept → design → implement → review → ship.

## Scope
org-level (Klever and Supervisr)

## Draft Steps
1. BMAD roundtable with relevant personas (conceptualize the feature)
2. Crystallize decisions with user, create Jira epic + children
3. Leo AC quality gate on all tickets, persona resolution for flagged ACs
4. PO priority ordering
5. Parallel implementation agents (one per repo/service)
6. Adversarial review of each implementation
7. Fix CRITICAL/HIGH findings, commit
8. Write e2e tests (Playwright for frontend, unit for backend)
9. Push branches, provide MR creation links
10. Write SESSION_STATE.md for handoff

## Notes
Successfully ran end-to-end in ~4 hours for KTP-525. Key insight: the AC quality gate (step 3) with persona resolution prevents implementation rework. Without it, agents build against vague ACs.

Differs from sprint-crawl (which operates on a single ticket with existing AC). This skill covers the full lifecycle from concept to shipped branches across multiple tickets and repos.
