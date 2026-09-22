# Skill Proposal: spec-drift-check
Date: 2026-09-14
Source: KTP-571 Planning Map — three spikes drifted past the decisions that reshaped them

## Trigger
Sprint boundary, or any decision round that demotes/changes a spec section. Also on "are these tickets still valid", "did anything change under this ticket".

## Scope
org (Klever first; the pattern is general)

## Draft Steps
1. List in-flight tickets (not Done) under the epic or sprint.
2. For each, extract the spec/PRD sections and decision IDs its description cites as authority.
3. Diff against the decision record's change log: has any cited section been demoted, corrected or superseded since the ticket's `created` date?
4. Report per ticket: CLEAN / DRIFTED (with the specific decision that moved under it) / DEAD ROLL-UP (a child it promises is Won't Do).
5. Never mutate tickets. Output a comment draft per drifted ticket; the human posts.

## Why it is not just a lint
The failure is silent and directional: the deferred-AC SOP catches "a decision that never reached a ticket." This catches the reverse, "a ticket that never heard about a decision." Three spikes sat In Progress for four weeks against a half-removed geography ladder and a spec section that had been declared non-binding.
