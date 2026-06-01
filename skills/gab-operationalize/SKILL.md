---
name: operationalize
description: Extract repeatable procedures and tribal knowledge from conversation, then codify as skills or persistent knowledge at the correct scope level.
nav:
  bay: ops
  when: "Extract repeatable procedures and tribal knowledge from conversation into skills."
  when_not: "Reviewing existing proposals (use /operationalize-audit). Batch creating (use /batch-skill-pipeline)."
---

# Operationalize

Turn ad-hoc sessions into permanent knowledge. Every extracted nugget is **tribal knowledge**. Some nuggets also produce a skill proposal.

**Usage:**
```
/operationalize [hint]            # Mine conversation, propose what to codify
/operationalize "deploy flow"     # Focus on a topic
/operationalize --update <target> # Add new learnings to an existing skill or doc
```

**Local context:** If `context.local.md` exists beside this skill, load it for org-specific path resolution. Otherwise detect from environment (cwd git remote, CLAUDE.md org markers).

**Session manifest:** This skill may run several times in one session. Before mining and after routing, reconcile against the active session's `knowledge-manifest.yaml` so nuggets are never re-extracted and `/session:check` close has deterministic proof that capture ran. See "Session Manifest" below. If no active session folder exists, skip manifest handling (legacy mode) and proceed normally.

**Examples:**

*Simple:* After figuring out Cloud Run deploy requires `--no-traffic` first, `/operationalize "deploy flow"` extracts `[KNOWLEDGE]` "never direct-deploy Cloud Run" → writes to CLAUDE.md, and `[+SKILL]` "full deploy pipeline" → writes proposal to `~/.claude/skill-proposals/`.

*Update:* `/operationalize --update deploy-service` after learning rollback command → locates `~/.claude/skills/deploy-service/SKILL.md`, mines "rollback with `--to-revisions=PREV`", shows diff, applies on approval.

---

## Session Manifest

The manifest is the session's in-session memory of what has already been captured. It makes repeat runs cheap (no duplicate nuggets) and gives the close gate a deterministic signal.

**Locate it.** Find the active session folder under `{org-project-management}/sessions/active/`. If exactly one exists, use it. If several, pick the one whose `state.yaml` `last_activity` is newest. The manifest is `sessions/active/{slug}/knowledge-manifest.yaml`.
- If the folder exists but the manifest file does not (a session created before v2), **create it** now per schema `knowledge_manifest_format` (`last_run: null`, empty `nuggets`/`skills`/`runs`), then proceed.
- If no active session folder exists at all, you are in legacy mode — skip every manifest step below and run the skill normally.

**Read before mining (feeds Phase 1).** Load `nuggets[].subject` from the manifest. These subjects are already persisted to the inbox. They are still in your context, but **do not re-extract them.** Mine only for subjects that are NOT already on that list. Dedup is **by subject**, never by timestamp — you cannot filter your own context by "what arrived after the last run", so the manifest's subject list is the only reliable dedup key.

**Write after routing (follows Phase 2).** For each new nugget you persisted this run:
- Append `{subject, inbox_file, captured}` to `nuggets`.
For each new skill proposal: append `{name, proposal_file, captured}` to `skills`.
Then, **on every run without exception** — including runs that found zero new nuggets:
- Append a `runs` entry: `{at: <now>, mode: <checkpoint|close>, nuggets_added: [...], skills_added: [...]}`.
- Set `last_run` to now and increment `run_count`.

`mode` is `checkpoint` unless `/session:check --close` invoked you (it passes `--mode close`); default to `checkpoint`. **The `last_run` stamp is mandatory even on a zero-nugget run** — it is the proof-of-capture the close gate reads. A run that genuinely finds nothing new still stamps `last_run` and appends a `runs` entry with `nuggets_added: []`. This is what lets the "I already captured everything" case pass the gate instead of false-blocking.

---

## Standard Mode

### Phase 1: Mine

**First, read the session manifest (above) and load the already-captured subjects.** Skip anything on that list.

Review conversation (or hinted topic). Extract NEW nuggets only:
- **Procedures** — step-by-step sequences with a trigger
- **Rules/constraints** — guardrails ("never do X")
- **Decisions** — choices made and why
- **Gotchas** — things that broke, surprising behaviors

Present as a bulleted list. Tag skill candidates with `[+SKILL]`. All others are `[KNOWLEDGE]`.

> Every nugget = tribal knowledge. `[+SKILL]` nuggets ALSO produce a skill proposal.

**Do NOT ask the user which nuggets to persist. Persist ALL of them immediately.** Show the list for awareness, then proceed to Phase 2 without waiting.

---

### Phase 2: Route

**Default target: Bibliothèque inbox.** All tribal knowledge goes to the org's bibliothèque inbox first. A curator agent catalogs, indexes, and promotes entries later. This is progressive disclosure: raw captures land in one place, get sifted later.

**Write nuggets THROUGH to the inbox immediately** — the instant a nugget is extracted it is persisted, so it survives even if the session never closes cleanly. One inbox file per session (not per nugget):
```
{org-project-management}/documentation/bibliotheque/inbox/YYYY-MM-DD-{topic-slug}.md
```
On the first run this file is created; record its path in the manifest as the session's `inbox_file`. On later runs in the same session, **append** the new `## N. {subject}` sections to that same recorded file rather than creating a new one. After writing, update the manifest per "Session Manifest" above.

Format:
```markdown
# Tribal Knowledge: {topic}

**Source:** {session context} ({date})

---

## 1. {nugget title}
{content — the rule, gotcha, or procedure}

## 2. {next nugget}
...

---

**Curator notes:** {optional hints for classification — which section(s) this might belong to}
```

**Update `inbox/INDEX.md`** with a row per entry (file, date, source, status=pending).

**Exceptions (bypass inbox, write directly):**

| Scope | Write Target | When |
|-------|-------------|------|
| Architectural decision | ADR via `/push-adr` | Pattern choice, fundamental decision |
| Cross-service contract | `documentation/architecture/contracts/` | Interface changes |
| CLAUDE.md rule (safety, process) | Appropriate CLAUDE.md | Critical guardrail that must be active immediately |

**For `[+SKILL]` nuggets — also write a proposal file:**

Write to `~/.claude/skill-proposals/YYYY-MM-DD-{name}.md`:
```markdown
# Skill Proposal: {name}
Date: {date}
Source: {session topic}

## Trigger
{when should this skill be invoked?}

## Scope
{repo-local / org / global}

## Draft Steps
{2-5 step outline}
```

Accumulate to backlog by default. Show count: "N proposals in `~/.claude/skill-proposals/`."
If the user explicitly asks to create the skill now, hand off to `/skill-creator:skill-creator`.

---

## Update Mode (`--update <target>`)

1. **Locate** `<target>` — search `~/.claude/skills/`, `.claude/skills/` (repo), CLAUDE.md sections, knowledge docs. If not found, list similar names.
2. **Read** the existing artifact.
3. **Mine** new learnings from conversation relevant to `<target>`.
4. **Propose diff** — show additions/modifications as before/after.
5. **Apply** on approval. Update INDEX.md if structure changed.

---

> **Guidelines:** Simpler is better (CLAUDE.md rule > skill). Preserve the user's voice exactly.
> Prioritize error paths over happy paths. Reference existing skills, don't reimplement.
> Always update the nearest INDEX.md after any write.

> **Proactive:** After a session with significant problem-solving, suggest: "Want me to `/operationalize` this?"
