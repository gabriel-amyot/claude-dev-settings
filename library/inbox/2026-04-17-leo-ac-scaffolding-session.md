# Inbox Entry — Leo AC Scaffolding Session
**Date:** 2026-04-17
**Source:** KTP-481, KTP-482, KTP-510 spec scaffolding session
**Status:** Unindexed — promote to context/ or update existing files when ready

---

## Nugget 1 — Jira mention format in post-comment drafts

**Rule:** Never use `mention:` frontmatter in scope-clarification template for Jira posts. The template renders it as `@accountid:...` which Jira does not recognize. Always put the mention directly in the body as `[~accountid:XXXX]`.

**Candidate home:** Append to `context/jira-skill-gotchas.md` under a "post-comment + Jira" section.

---

## Nugget 2 — scope-clarification.md template fix (already applied)

**What changed:** Removed the `{{mention}}` opening block and the "I'm going to start implementing shortly" footer. Template is now `{{body}}` + "Scaffolded from context. Correct me if my assumptions are off."

**Why:** Opening emitted wrong Jira mention format. Footer implied the commenter was the implementer — wrong for Leo (spec role).

**Candidate home:** Document in a future `post-comment-gotchas.md` or as a note in CATALOG.md under post-comment template usage.

---

## Nugget 3 — Amal question scope rule (Klever-specific)

**Rule:** When posting Leo spec comments on Klever tickets, backend/data questions do not go to Amal. Only UX questions (layout, interaction, defaults, visual hierarchy) go to Amal. Backend scope belongs to Gabriel.

**Candidate home:** `project-management/CLAUDE.md` under a "Spec Comments" or "Leo workflow" section, OR MEMORY.md feedback entry.

---

## Nugget 4 — Stakeholder interview archaeology (Klever-specific)

**Rule:** Before posting spec on any KTP-453 or KTP-115 ticket that references a domain expert (Jaspreet, Sisi, Marc-André), search `archive/KTP-115-proximity-map-shell/KTP-106/` for historical interview transcripts. Jaspreet's Jan 2026 interview (`jaspreetInterview/`) contains CPA/conversion goal definitions that directly changed the KTP-482 interpretation.

**What's in KTP-106/jaspreetInterview:** Jaspreet defined that advertisers track multiple named conversion goals (CONVERSION_NAME), one being the primary CPA target. Online/Offline is a technical source split, not a client-meaningful axis. This drove the KTP-482 filter intent.

**Candidate home:** MEMORY.md reference entry pointing to this archive path, or a Klever-specific note in `project-management/documentation/bibliotheque/`.

---

## Nugget 5 — CONVERSION_NAME vs CONVERSION_TYPE (Klever domain knowledge)

**Decision:** The KTP-482 filter replaces Online/Offline (CONVERSION_TYPE) with named conversion goals (CONVERSION_NAME). CONVERSION_TYPE is a technical BQ field — "online" (pixel-based) vs "offline" (foot traffic). CONVERSION_NAME is the client-meaningful axis — the actual named goal an advertiser tracks ("Store Visit", "Order Confirmation").

**Additional nuance:** Advertisers have a primary CPA conversion goal + secondary ones. Filter UX should consider surfacing this hierarchy. Open question to Amal pending.

**Candidate home:** `project-management/documentation/bibliotheque/` under conversions domain knowledge, or append to existing BQ schema snapshot docs in KTP-115.

---

## Skill Proposal Reference

`~/.claude/skill-proposals/2026-04-17-leo-ac-scaffold.md` — Leo AC scaffolding workflow. See that file for full proposal.
