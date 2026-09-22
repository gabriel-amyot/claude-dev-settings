# Skill Proposal: ticket-cross-linker
Date: 2026-05-07
Source: Measurement Map epic cross-linking session

## Trigger
"cross-link tickets", "add wikilinks to epic", "refresh ticket links", "link the tickets", or after any epic reorganization (e.g., `/epic-reorganization` completion).

## Scope
org (Klever project-management)

## Draft Steps
1. Accept epic key(s) as input. Fetch children from Jira, read on-disk INDEX.md and folder structure.
2. Map feature-area groupings (auto-detect from ticket summaries or accept manual overrides).
3. Identify cross-epic movements (Jira epic vs folder location mismatches, "moved from/to" history).
4. Dispatch parallel Sonnet agents (one per epic) to update INDEX.md and ticket README.md files with standardized `## Linked Items` sections using the link type taxonomy.
5. Verification pass: grep for orphan tickets (on disk but not linked), verify bidirectional link integrity.

## Notes
- Builds on the link type taxonomy captured in today's inbox entry
- Should integrate with `/epic-reorganization` as a post-step
- Could also be triggered by `/wiki-lint` when it detects missing cross-references
