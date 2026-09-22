# Skill Proposal: dispatch-readiness-gate
Date: 2026-05-17
Source: KTP-667 staff engineer adversarial review

## Trigger
Before dispatching any ticket to autonomous implementation (sprint-crawl, night-crawl, or manual agent dispatch). Trigger phrases: "dispatch this ticket", "start autonomous", "is this ticket ready", "dispatch readiness".

## Scope
Global (applies to all orgs)

## Draft Steps
1. Read ticket description and ACs
2. For each AC, check: does the agent have enough information to implement without asking questions?
3. Check for: missing file paths, unspecified download URLs, undecided format choices, cross-ticket integration seams, deployment order gaps, implicit knowledge not stated
4. Check CLAUDE.md for contradictions with code (aspirational vs current state)
5. Rate: READY / NEEDS WORK (list gaps) / NOT DISPATCHABLE (blocking gaps)
6. For each gap, propose a resolution (add to ticket comment)

## Why
The KTP-667 session revealed 19 gaps across 8 tickets after Leo wrote ACs and Winston wrote the ADR. The staff engineer review pattern caught what spec quality gates missed: implicit knowledge, integration seams, and deployment ordering. This should be a repeatable skill, not an ad-hoc review.
