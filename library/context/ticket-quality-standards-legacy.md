# Ticket Quality Standards

Single source of truth for ticket structure, acceptance criteria quality, and story format.

## Philosophy: Ticket = Contract

A ticket is a contract between the **reporter** (the ask) and the **assignee** (the do). The reporter defines WHAT success looks like. The assignee decides HOW to get there. If the contract is vague, the deliverable will be wrong.

## User Story Format

Every ticket should state intent using:

> As a [role], I want [action], so that [benefit]

The "so that" clause is mandatory. It encodes the WHY. Without it, the assignee cannot make tradeoffs.

## Acceptance Criteria Rules

### The Litmus Test

**If it tells you HOW, it's a task. If it tells you WHAT the result looks like, it's an AC.**

ACs define observable outcomes that can be verified by someone who didn't write the code. They should be format-agnostic (not tied to a specific implementation approach).

### Format

Use BDD (Given/When/Then) or outcome-based format:

**BDD:**
> Given [precondition], When [action], Then [expected result]

**Outcome-based:**
> The system [does X] when [condition Y] is met.

### Minimum Bar

- Every ticket must have at least **2 testable ACs**
- Each AC must be independently verifiable
- Each AC must have a clear pass/fail condition

### Ordering

1. **Intent** (user story) first
2. **Acceptance criteria** second
3. **Tasks/subtasks** last (optional, and always subordinate to AC)

## Anti-Patterns

| Bad (Task-Based) | Good (Spec-Based) | Why |
|---|---|---|
| "Add a loading spinner to the search page" | "The user sees a loading indicator within 200ms of initiating a search" | Spec says WHAT the user experiences, not HOW to build it |
| "Create a new API endpoint for user preferences" | "User preferences are retrievable and persistable via a documented API" | Doesn't prescribe endpoint structure |
| "Write unit tests for the payment module" | "Payment calculations are correct for all currency types supported by the system" | Tests are an implementation detail, correctness is the outcome |
| "Refactor the auth middleware" | "Authentication failures return appropriate HTTP status codes and do not leak internal error details" | Focuses on observable behavior |
| "Update the database schema to add a status column" | "Orders have a trackable status that transitions through: created → confirmed → shipped → delivered" | Describes the domain model, not the storage layer |
| "Fix the bug where users can't log in" | "Given valid credentials, when a user submits the login form, then they are authenticated and redirected to the dashboard within 2 seconds" | Defines the expected behavior precisely |

## Spikes

Spikes are time-boxed research tickets. Their deliverable is **knowledge**, not code.

- AC for spikes define what questions must be answered
- Output is a written summary (decision doc, ADR, or ticket comment)
- Always include a time-box (e.g., "2 days max")

## Canonical Template

The BMAD story template is the canonical ticket structure. For full template details, reference the BMAD Phase 3-4 workflow artifacts.
