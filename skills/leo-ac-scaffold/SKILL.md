---
name: leo-ac-scaffold
description: "Scaffold acceptance criteria for empty Jira tickets using Leo persona. Reads epic context, code, and stakeholder archives to draft Given/When/Then ACs, then posts to Jira via /post-comment. Trigger: 'scaffold AC for KTP-XXX', 'Leo look at this ticket', 'this ticket has no AC'. Klever org. Input: ticket key. Returns: Leo-quality AC comment posted to Jira."
nav:
  bay: plan
  when: "Scaffold Given/When/Then acceptance criteria for empty Jira tickets."
  when_not: "Tickets already have AC. Creating tickets from scratch (use /create-tickets)."
  personas: [leo]
---

# Leo AC Scaffold

Scaffolds plausible acceptance criteria for tickets that have no AC or only a one-sentence description.

## Prerequisites

- Load the Leo persona before starting: Read `~/Developer/supervisr-ai/project-management/_bmad/bmm/agents/spec-coach.md`
- Adopt Leo's voice and perspective throughout

## Steps

### 1. Fetch Ticket Context

Use `/jira` skill to get:
- The ticket itself (summary, description, type)
- Parent epic (context, scope, existing ACs)
- Sibling tickets (what's already scoped in the epic)
- Reporter and PO (to know who to mention)

### 2. Archaeology Pass

Search for domain context relevant to the ticket:
- Check `documentation/bibliotheque/` for domain terms and vendor context
- Check `archive/` for prior work on similar features
- Check ticket folder if it exists: `tickets/{PREFIX}/{TICKET-ID}/`
- Check epic-level reports and architecture docs

### 3. Code Scan

Find the relevant frontend/backend components to ground the interpretation:
- Use Grep to find references to the feature name in code
- Identify what exists vs what needs building
- Note any existing tests that reveal expected behavior

### 4. Draft ACs

Write Given/When/Then acceptance criteria:
- Each AC must be an observable outcome, not a task
- Each AC must be testable by QA
- Backend/data questions stay with Gabriel (never ask PO about those)
- Always propose an answer, never ask without scaffolding first
- ACs must cover: happy path, edge cases, error states

### 5. Draft Jira Comment

Format as a Leo comment:

```
[automated] -- Message from Leo, Gab's Specification Specialist

## From What I Know

{Brief interpretation of what this ticket is asking for, grounded in epic context and code scan findings}

## Assumed Acceptance Criteria

### AC-1: {title}
**Given** {precondition}
**When** {action}
**Then** {observable outcome}

### AC-2: {title}
...

## Questions for {PO name}

{UX-only questions. Max 3. Each question includes Leo's proposed answer.}

---
These ACs are scaffolded from epic context and codebase scan. Please correct, refine, or approve.
```

### 6. Post via /post-comment

Write the draft to: `tickets/{PREFIX}/{TICKET-ID}/reports/ship/posts/{date}-{ticket}-leo-ac-scaffold.md`

Then invoke `/post-comment` to post to Jira. The skill handles template rendering, preview, approval gate, and audit logging.

## Constraints

- One Leo comment per ticket. If context evolves later, post a new clean comment (don't addendum).
- Never add ACs to tickets already in progress (ticket AC immutability rule).
- Backend questions go to Gabriel, not PO.
- Use `[~accountid:...]` Jira mention syntax for the PO.
- Header must follow the convention: `[automated] -- Message from Leo, Gab's Specification Specialist`
