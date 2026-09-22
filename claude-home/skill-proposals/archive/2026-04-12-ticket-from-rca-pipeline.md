# Skill Proposal: ticket-from-rca-pipeline
Status: BUILT (2026-04-21 — functional test: PARTIAL)
Date: 2026-04-12
Source: SPV-141 → SPV-143/144/145 session

## Trigger
User has RCA incidental findings (parked issues from a tracer fire, incident investigation, or debugging session) and wants to spin them into tracked Jira tickets.

Trigger phrases: "create tickets from RCA", "file the incidental findings", "spin these into tickets", "ticket the parked findings"

## Scope
Global (any org). Consumes RCA markdown files, produces Jira tickets.

## Draft Steps
1. **Parse RCA findings.** Read the incidental-findings or RCA source file. Extract each finding: title, context, what was observed, suspected cause, related tickets.
2. **Draft tickets.** For each finding, draft a Jira ticket following the `jira-ticket-description.md` template. Include Intent, ACs (Given/When/Then), Blockers, References.
3. **Leo AC gate.** Run Leo-style AC quality review on each draft. Flag: vague outcomes, untestable conditionals, task-list ACs, missing decision gates.
4. **User confirmation gate.** Present all drafts. Wait for approval.
5. **Create in Jira.** Batch-create via `/jira` skill.
6. **Adversarial codebase verification.** Spawn parallel Explore agents (one per ticket) to verify every factual claim (entity names, schema fields, publisher behavior, config semantics) against local repos. Report CRITICAL/HIGH/MEDIUM/LOW findings.
7. **Rewrite with corrections.** Fix all findings, re-ground claims with file paths and line numbers.
8. **Update Jira.** Push corrected descriptions.
9. **Report keys.** Print SPV-### keys for the user to add to RCA notes.

## Why this should be a skill
The three-pass pipeline (draft → adversarial verify → rewrite) caught CRITICAL factual errors in all three tickets. Without the adversarial pass, three tickets with wrong subscription names, non-existent schema fields, and conflated metadata would have reached the team. The pipeline is repeatable for any RCA that parks incidental findings.

## Dependencies
- `/create-tickets` skill (steps 2-5)
- `/jira` skill (step 5, 8)
- Explore agents (step 6)
- Leo AC quality review (step 3)
