# Skill Proposal: brownfield-sbe-audit
Date: 2026-04-24
Source: KTP-115 Proximity Map SBE audit session

## Trigger
"audit specs for [feature]", "SBE audit", "what behaviors are undocumented", "brownfield spec pass", "specification audit"

## Scope
global (works for any repo with agent-os/)

## Draft Steps
1. **Inventory** — Read frontend/backend source for the feature area. Build component tree.
2. **Extract** — Write Given/When/Then SBEs for every user-visible behavior found in code.
3. **Classify** — Cross-reference each SBE against agent-os specs and Jira ACs. Tag as CONFIRMED, UNDOCUMENTED, or CONTRADICTED.
4. **Write specs** — Create/update agent-os spec files for all UNDOCUMENTED SBEs. Fix CONTRADICTED specs.
5. **Report** — Write audit summary to tickets/ with classification counts, reviewer notes, and recommended actions.

## Notes
BMAD party format works well: Leo leads, Winston reviews architecture coherence, Quinn validates testability. Two-phase execution (extract+classify, then cross-ref+write) prevents context explosion.
