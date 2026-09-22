# Skill Proposal: initiative-scaffold
Date: 2026-05-01
Source: Data pipeline initiative session

## Trigger
"new initiative", "start an initiative", "personal project", "upsell proposal", "create initiative"

## Scope
org (Klever project-management)

## Draft Steps
1. Ask for initiative name and one-line description
2. Create `general/initiatives/{name}/` with INDEX.md (frontmatter: status, created, last_updated)
3. Create subfolders: research/, data/, experiments/, learnings/, best-practices/, references/ — each with INDEX.md
4. Copy `_templates/proposal.md` into the folder
5. Add entry to `general/initiatives/INDEX.md`
6. Add cross-reference in bibliothèque INDEX.md under "Side Projects"
7. Create memory entry for the initiative
