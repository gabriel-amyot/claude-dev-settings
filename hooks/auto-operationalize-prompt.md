AUTO-OPERATIONALIZE: CAPTURE TRIBAL KNOWLEDGE NOW

You are about to lose context (session ending or compaction). Scan this conversation and extract tribal knowledge before it is lost. This is non-interactive. Do NOT use AskUserQuestion. Just write files.

## What to extract

Scan for:
- **Procedures**: step-by-step workflows the user established or taught
- **Rules/constraints**: guardrails ("never do X", "always Y before Z")
- **Decisions**: architectural or process choices with rationale
- **Gotchas**: things that broke, surprised, or wasted time
- **Corrections**: wrong assumptions that were fixed

Skip: routine tool usage, trivial file reads, anything already documented in CLAUDE.md.
Write NOTHING if the session was trivial (just questions, no real work done).

## How to write — Bibliotheque Inbox format

Write a SINGLE file to `{INBOX_DIR}/` covering ALL nuggets from this session:

Filename: `YYYY-MM-DD-{topic-slug}.md` (today's date, slug from dominant topic)

Content:
```markdown
# Tribal Knowledge: {topic}

**Source:** {session context — ticket ID + what was being worked on} ({date})

---

## 1. {nugget title}
{content — the rule, gotcha, or procedure. 2-4 sentences. Preserve the user's voice.}

## 2. {next nugget}
...

---

**Curator notes:** {hints for classification — which bibliotheque section this belongs to, e.g. stack/, ops/, adtech/}
```

Then update `{INBOX_DIR}/INDEX.md` — add a row: `| file.md | {date} | {session context} | pending |`

## Skill proposals

If a nugget describes a repeatable multi-step procedure (3+ steps with a clear trigger), ALSO write a proposal to `{PROPOSALS_DIR}/`:

Filename: `YYYY-MM-DD-{skill-name}.md`

Content:
```markdown
# Skill Proposal: {name}
Date: {date}
Source: {session topic summary}
Usefulness: {why this would save time, how often it would trigger}
Create vs Update: {create new skill, or update existing {name}}

## Trigger
{When should this skill be invoked?}

## Scope
{repo-local / org / global}

## Draft Steps
{2-5 step outline of the procedure}
```

## Rules

- One inbox file per session, not one per nugget.
- Do not duplicate. If a nugget is already in a recent inbox file, skip it.
- After writing all files, proceed normally (allow stop/compaction).
