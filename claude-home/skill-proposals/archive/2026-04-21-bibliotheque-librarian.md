# Skill Proposal: bibliotheque-librarian
Status: BUILT (2026-04-21 — functional test: PASS, gated)
Date: 2026-04-21
Source: SPV-165 knowledge curation session

## Trigger
After `/operationalize` writes to inbox. Or on demand: `/bibliotheque-refresh`, "curate the inbox", "process inbox entries."

## Scope
org (Supervisr.AI project-management)

## Draft Steps
1. Read `bibliotheque/inbox/INDEX.md`, identify entries with status=pending
2. For each pending entry, read content and classify: which section(s) does each nugget belong to?
3. Write each nugget to proper section file (new file or append to existing)
4. Update section INDEX.md with new/modified entries
5. Update root INDEX.md catalog tables (add rows to "Understand" / "Blocked" / "Do Something" as appropriate)
6. Mark inbox entry as `promoted` in inbox/INDEX.md
7. Report: what was promoted, where it landed, any entries that need human judgment

## Notes
- Should enforce three-lane catalog pattern when updating root INDEX
- Should clean bootstrapped placeholder text on first real entry to a section
- Should add "Go here when..." triggers to section descriptions
- Existing `/bibliotheque-refresh` skill handles Notion exports, this is different: it processes the tribal knowledge inbox
