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

Ask user (multiSelect): "Which nuggets should we persist?"

---

### Phase 2: Route

**For each selected nugget — write a tribal knowledge entry:**

Resolve write target using the Knowledge Resolver. Load `context.local.md` if present, else detect org from cwd.

| Scope | Write Target | When |
|-------|-------------|------|
| Architectural decision | ADR via `/push-adr` | Pattern choice, fundamental decision |
| Cross-service contract | `documentation/architecture/contracts/` | Interface changes |
| Repo-local convention | `{repo}/agent-os/` or `{repo}/.claude/CLAUDE.md` | Repo-specific rule |
| Project context | `documentation/library/` or `tickets/{ID}/reports/` | Project-scoped knowledge |
| Personal/global | `~/.claude/library/context/` or MEMORY.md | User preference, cross-project |

Show proposed location + content. Write on approval. Update nearest INDEX.md.

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

Ask: "Run `/skill-creator:skill-creator` now, or accumulate for later?" Default: accumulate.
- **Now:** hand off to `/skill-creator:skill-creator` with the proposal file as input.
- **Accumulate:** save to backlog. Show count: "N proposals in `~/.claude/skill-proposals/`."

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
