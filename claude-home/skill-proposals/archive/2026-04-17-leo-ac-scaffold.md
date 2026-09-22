# Skill Proposal: leo-ac-scaffold
Date: 2026-04-17
Source: KTP-481, KTP-482, KTP-510 spec scaffolding session

## Trigger
When a ticket is in TO DO with no AC or a one-sentence description and needs to be picked up. Invoked as: "scaffold the AC for KTP-XXX" or "Leo, look at this ticket."

## Scope
Klever org (project-management). Could generalize to any org with a PO/spec gap.

## Problem it solves
Empty tickets block autonomous crawls. Leo can scaffold plausible ACs from epic context + code + stakeholder archives, post to Jira, and tag the PO for correction — without bottlenecking on Gabriel.

## Draft Steps

1. **Fetch ticket context** — get ticket + parent epic + sibling tickets (what's already scoped in the epic). Identify reporter and PO.
2. **Archaeology pass** — search stakeholder interview archives and BQ schema docs for domain context relevant to the ticket. For Klever: check `archive/KTP-115-proximity-map-shell/KTP-106/` and `KTP-115/KTP-287/reports/`.
3. **Code scan** — find the relevant frontend/backend component to ground the interpretation in what actually exists vs what needs building.
4. **Draft comment** — "From What I Know" interpretation + Assumed ACs (Given/When/Then) + UX-only questions for PO. Header: `[automated] — Message from Leo, Gab's Specification Specialist`. Mention PO with `[~accountid:...]`.
5. **Write draft to disk** — `tickets/{PREFIX}/{TICKET-ID}/reports/ship/posts/{date}-{ticket}-leo-ac-scaffold.md` with `scope-clarification` template frontmatter.
6. **Preview + approval gate** — show full rendered comment to Gabriel. Wait for explicit go/no-go.
7. **Post via jira skill** — `add-comment` on the ticket. Log to `post-log.yaml`.

## Key constraints
- Backend/data questions never go to PO — Gabriel owns those.
- Never ask questions without also proposing an answer (scaffold first, ask for correction).
- ACs must be observable outcomes (Given/When/Then), not task lists.
- One Leo comment per ticket — if context evolves, post a new clean comment, don't addendum.

## Related
- `scope-clarification` template in `~/.claude-shared-config/skills/templates/`
- `post-comment` skill for the posting pipeline
- `jira` skill for fetching ticket context
- Jaspreet interview archive: `archive/KTP-115-proximity-map-shell/KTP-106/jaspreetInterview/`
