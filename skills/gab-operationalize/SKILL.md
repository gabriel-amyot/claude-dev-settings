---
name: operationalize
description: Extract repeatable procedures and tribal knowledge from conversation, then codify as skills or persistent knowledge at the correct scope level.
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

**Examples:**

*Simple:* After figuring out Cloud Run deploy requires `--no-traffic` first, `/operationalize "deploy flow"` extracts `[KNOWLEDGE]` "never direct-deploy Cloud Run" → writes to CLAUDE.md, and `[+SKILL]` "full deploy pipeline" → writes proposal to `~/.claude/skill-proposals/`.

*Update:* `/operationalize --update deploy-service` after learning rollback command → locates `~/.claude/skills/deploy-service/SKILL.md`, mines "rollback with `--to-revisions=PREV`", shows diff, applies on approval.

---

## Standard Mode

### Phase 1: Mine

Review conversation (or hinted topic). Extract:
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

**Write a single inbox entry per session** (not per nugget) to:
```
{org-project-management}/documentation/bibliotheque/inbox/YYYY-MM-DD-{topic-slug}.md
```

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
