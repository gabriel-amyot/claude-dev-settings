---
name: post-crawl-review
description: Guided human-in-the-loop review of overnight crawl or autonomous work. Use whenever the user wants to review crawl results, validate deployed changes, go through tickets after an autonomous session, or says "review the crawl", "feedback investigation", "dose review", "check overnight work", "let's go through the tickets", "review what was done last night", "post-crawl review". Also use when the user has a list of tickets to triage with disposition decisions. Walks through each ticket interactively, then batch-executes all actions in parallel.
nav:
  bay: review
  when: "Guided human-in-the-loop review of overnight crawl or autonomous work."
  when_not: "Adversarial code review (use /adversarial-cascade). Pre-ship check (use /pre-ship-check)."
---

# Post-Crawl Review

Interactive feedback investigation for reviewing work from overnight crawls, autonomous sessions, or any batch of ticket work. The user makes every decision; you present context and execute.

## Why this exists

After autonomous work, the human needs to validate before anything ships. Checking deployed UX, reading Jira state, making disposition decisions ticket by ticket. Without structure, items get missed and the review takes twice as long. This skill turns it into a guided checklist with batched parallel execution.

## Phase 1: Gather the ticket list

The user may provide:
- An explicit list (table, bullets, verbal)
- A crawl report or session transcript reference
- A sprint or epic to scan

If no list provided, look for:
1. Recent crawl reports in `tickets/` subfolders (modified last 24h)
2. Ralph-loop state files (`.claude/ralph-loop.local.md` in active repos)
3. Morning primer output (`brief/`)

Build a summary table: ticket key, type/category, what to check. Present for confirmation.

## Phase 2: Ticket-by-ticket review

Process one ticket at a time. For each:

### Present a context card

1. **Jira state**: `python3 ~/.claude/skills/jira/jira_skill.py get {KEY} --org {org}`
   Show: status, assignee, last comment summary, AC completion state
2. **Local artifacts**: Check `tickets/{PREFIX}/{TICKET-ID}/` for ac.yaml, reports, STATUS_SNAPSHOT
3. **Deployed state**: If frontend ticket, offer to check via browser. Otherwise note what user observes.
4. **Git state**: Latest commits on related branches if relevant

Keep the card concise (under 15 lines). Then ask: "Disposition?"

### Disposition types

| Code | Meaning | Generated action |
|------|---------|-----------------|
| `close` | Work verified, AC met | Closing comment + transition |
| `ready-for-prod` | Merged to dev, not yet deployed | Status update only |
| `park` | Blocked on someone else | Draft comment tagging the blocker |
| `rewrite` | ACs stale or wrong | Leo drafts new ACs |
| `investigate` | Something's broken | Dexter diagnosis |
| `approve-ac` | Specific AC verified | Update ac.yaml |
| `amend` | Description/scope mismatch | Draft description update |
| `reorganize` | Wrong epic, needs splitting | Flag for brainstorm |
| `skip` | Not reviewing now | No action |

The user won't always use these exact words. Interpret naturally. If the user says "this is done but the description is wrong," that's `amend` + `ready-for-prod`. Capture their raw words alongside the mapped disposition.

### Recording

For each ticket, record in the task list:
- Ticket key and disposition type
- User's verbatim feedback (their words carry nuance that matters downstream)
- Specific instructions (who to tag, which AC, what to change)
- Whether it requires a Jira post, a code change, or a manual Gabriel action

**Do NOT execute during Phase 2.** The user reviews everything first. Actions batch later.

### User is the authority

The user may:
- Do Jira actions themselves while talking ("I just moved it", "I renamed the title")
- Change a previous disposition mid-stream
- Give rich verbal descriptions that must be captured precisely for downstream agents
- Combine multiple dispositions on one ticket

Roll with it. Update the record. Don't ask them to slow down or formalize.

## Phase 3: Confirm and execute

After all tickets reviewed, present:

```
| Ticket  | Disposition    | Action                              | Agent   |
|---------|---------------|--------------------------------------|---------|
| KTP-609 | investigate   | Dexter diagnosis of Placer null      | Opus BG |
| KTP-579 | park          | Comment to Amal re: color specs      | Sonnet BG |
| KTP-628 | rewrite       | Leo AC draft for circle label bug    | Sonnet BG |
| KTP-124 | amend         | Rephrase description (no "city")     | Sonnet BG |
| KTP-130 | approve-ac    | Update ac.yaml AC-4                  | Inline  |
```

Get confirmation, then dispatch.

### Dispatch rules

| Disposition | Approach | Model |
|-------------|----------|-------|
| `investigate` | Dexter agent (background) | Opus |
| `rewrite` | General agent, Leo persona (background) | Sonnet |
| `park` | General agent, draft comment (background) | Sonnet |
| `amend` | General agent, draft update (background) | Sonnet |
| `close` | Post-comment pipeline (sequential) | -- |
| `approve-ac` | Direct ac.yaml edit | Inline |
| `ready-for-prod` | Jira transition | Inline |
| `reorganize` | Note for later brainstorm | None |

**Parallelization**: All background agents dispatch in a single message. Inline actions execute immediately.

### Agent briefing rules

- **Dexter for investigations.** Real forensic analysis (IS/IS NOT, evidence, hypotheses). Not a surface-level guess.
- **Leo persona for AC rewrites.** Read the persona file first. Given/When/Then. Include the user's verbatim bug description in the brief.
- **All Jira content drafts go to disk first.** Write to `tickets/{PREFIX}/{TICKET-ID}/jira/`. Never post without user review.
- **Sonnet for mechanical work, Opus for diagnosis.** Token discipline.
- **`[automated]` tags include persona + model.** Per post-comment learned rules.
- **Jira posts use the jira skill** (`~/.claude/skills/jira/jira_skill.py`), not raw curl.

### As agents complete

For each returning agent:
1. Read the output (draft file, diagnosis report)
2. Preview to the user (concise summary, not raw dump)
3. Apply fixes if needed (wiki markup, content tweaks)
4. Post with user approval via jira skill
5. Mark the task complete

If an agent fails (connection error, timeout), redispatch with a leaner approach (code-only, no cloud calls). If it fails twice, surface as a manual action for the user.

## Phase 4: Wrap-up

1. **Final status board**: All tickets, final state, any remaining manual actions
2. **Manual action callouts**: Deploys, GitLab CI/CD variable updates, things only the user can do
3. **Follow-ups**: New tickets to create, brainstorm sessions to schedule
4. **Commit local changes**: ac.yaml updates, draft files, diagnosis reports

## Common patterns from real sessions

**"This can't be closed"**: The user checked deployed UX and it doesn't work. Always investigate before reporting the ticket as resolved. Use Dexter.

**"I need to tag X"**: Park disposition. Draft a comment that asks the specific question, tags the person, and is concise. Not a wall of text.

**"The description is wrong"**: Amend disposition. Read current Jira description, draft replacement preserving good parts, removing stale references.

**"This AC is approved"**: Find the ac.yaml, update the specific AC status to DONE with the user's name and today's date as evidence.

**"This ticket is blowing up"**: Reorganize. Flag it, don't try to fix it inline. These need a dedicated brainstorm session.

**"Skip"**: Move on. No ceremony needed.
