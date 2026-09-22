# Skill Proposal: sprint-close-batch
Date: 2026-05-28
Source: Sprint 4 Canada Map close session

## Trigger
"close these tickets", "batch close", "sprint close for feature X", or when multiple related tickets need closing with a shared validation ticket.

## Scope
org (Klever, potentially Supervisr)

## Draft Steps
1. Accept ticket list (or epic/feature scope)
2. Sweep each ticket: verify git merge status (fetch, not state files), check BQ if applicable
3. Create shared validation ticket with ACs extracted from source tickets
4. Draft closing comments (AC table + deliverables + rationale) per ticket
5. Post comments and transition to Done in batch

## Relationship to existing
- Extends `/sprint-close` (which does adversarial review per ticket). This is lighter: batch close for tickets already reviewed.
- Uses `/jira` for comments and transitions
- Uses `/gitlab` for MR merge status
- Could wrap `/post-comment` for the comment posting step
