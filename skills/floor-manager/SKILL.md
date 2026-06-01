---
name: floor-manager
description: "Harness navigator. Recommends the right skill, agent, or workflow for any situation. Interactive menu with 7 bays (build, fix, review, ship, plan, know, ops). Triggers on: '/floor-manager', 'what skill should I use', 'which tool', 'how do I', 'where do I start', 'what's the right workflow', 'help me find', 'I need to', 'recommend a skill'. Global scope."
user_invocable: true
nav:
  bay: ops
  when: "Don't know which skill or agent to use. Need routing guidance."
  when_not: "You already know the exact skill. Just invoke it directly."
---

# Floor Manager

The person who knows every bay on the factory floor and directs you to the right department.

**Usage:**
```
/floor-manager                          # Recommender mode (auto-detect intent)
/floor-manager something is broken      # Recommender with intent hint
/floor-manager I need to ship KTP-499   # Recommender with ticket context
/floor-manager --browse                 # Bay overview table
/floor-manager --bay fix                # All tools in Mechanics Garage
/floor-manager --persona quinn          # All skills involving Quinn
/floor-manager --all                    # Full flat list grouped by bay
```

---

## Bay Definitions

7 bays. Each has a code, a name, a purpose, and default personas.

| Bay | Code | Purpose | Default Personas |
|-----|------|---------|-----------------|
| Assembly Line | `build` | Autonomous pipelines, ticket-to-dev, epic lifecycle | Amelia, Bob |
| Mechanics Garage | `fix` | Debug, investigate, root cause, diagnostics | Dexter, Quinn |
| Inspection Station | `review` | Code review, adversarial, quality gates, testing | Quinn, Winston |
| Shipping Dock | `ship` | MR creation, deploy, sprint close, external posts | Amelia, Bob |
| War Room | `plan` | Estimation, planning, tickets, PRD, sprint mgmt | John, Mary, Leo |
| Library | `know` | Knowledge retrieval, wiki, context, briefings | Paige, Atlas |
| Control Tower | `ops` | Harness meta, session health, operationalize, cost | (none) |

---

## How It Works: Three-Layer Catalog

The floor-manager reads tools from three sources at invocation time. No static catalog file to maintain.

### Layer 1: Self-Declaring Skills (Primary)

Read every `~/.claude/skills/*/SKILL.md`. Parse YAML frontmatter for the `nav:` block:

```yaml
nav:
  bay: fix
  when: "Something isn't working. Need root cause before fixing."
  when_not: "You already know the exact fix. For test validity, use /test-adversarial."
  personas: [dexter, quinn]
  org: [klever]  # optional, omit for global
```

Skills with a `nav:` block are first-class entries. Display their `when` and `when_not` to help the user choose.

### Layer 2: Override File (Agents, Commands, Edge Cases)

Read `~/.claude/library/context/harness-overrides.yaml`. This covers:
- Agent definitions (`~/.claude/agents/*.md`) that have no SKILL.md
- BMAD plugin commands (bmad-help, bmad-review-adversarial-general, etc.)
- Plugin skills (superpowers:*, caveman:*, agent-browser:*, etc.)
- Any routing override where a skill's raw description needs better disambiguation

Each entry has: id, type, invoke, bay, when, when_not, personas, org.

### Layer 3: Fallback (Zero-Maintenance)

Any skill visible in the system-reminder skill list that has NO `nav:` frontmatter AND no override entry still appears. Read the skill's `description` field from the system-reminder listing. Use keyword matching against bay definitions:

| Keywords | Bay |
|----------|-----|
| pipeline, ticket-to-dev, autonomous, lifecycle, ship ticket | build |
| debug, investigate, broken, root cause, diagnostic, probe | fix |
| review, adversarial, test, quality, validate, audit code | review |
| MR, merge request, deploy, ship, sprint close, post comment | ship |
| plan, estimate, create ticket, PRD, sprint, scaffold AC | plan |
| knowledge, wiki, library, context, brief, sitrep, tribal | know |
| harness, session, operationalize, cost, skill creator, meta | ops |

Present Layer 3 matches as "uncategorized" with lower confidence. Suggest the user add `nav:` frontmatter.

---

## Mode 1: Recommender (Default)

Triggered by `/floor-manager` with optional free-text intent.

### Step 1: Detect Context

1. **Org**: Detect from cwd. `/grp-beklever-com/` = klever, `/supervisr-ai/` = supervisr, else = global.
2. **Ticket**: Extract from args if present (pattern: `[A-Z]+-\d+`), or from cwd path (`tickets/KTP/...`).
3. **Intent keywords**: Parse args for bay-routing keywords (see keyword table above).

### Step 2: Classify Intent

Match the user's free-text against the `when` fields across all three layers. Score by:
- Direct keyword match in `when` field: +3
- Bay keyword match: +2
- Org match (skill's org includes detected org, or skill is global): +1
- Persona match (if user mentioned a persona name): +2

### Step 3: Present Recommendations

Show the **top 3** matches. For each:

```
1. /investigate — Mechanics Garage
   Quinn -> Amelia -> Quinn pipeline for root cause analysis
   When: Something isn't working. Need root cause before fixing.
   Invoke: /investigate [description]
```

If confidence is low or ambiguous between bays, ask ONE clarifying question:

> "Are you trying to **fix** something, **build** something new, **review** existing work, or **figure out** what to do next?"

Then re-rank with the answer.

### Step 4: BMAD Bridge

When the user's intent maps to a BMAD planning workflow (epic creation, persona-driven design, story writing), append:

> For step-by-step BMAD workflow guidance: `/bmad-help`

Do not duplicate `/bmad-help`'s CSV-based workflow navigator logic.

---

## Mode 2: Browser

Triggered by flags: `--browse`, `--bay`, `--persona`, `--all`.

### `--browse` (Bay Overview)

Display the 7-bay table from Bay Definitions above. After displaying, ask: "Which bay?" Then expand that bay.

### `--bay <code>` (Expand One Bay)

List all tools in that bay across all three layers. For each tool:

```
- /skill-name — one-line description
  When: ...
  When not: ...
  Invoke: /skill-name [args]
  Personas: Quinn, Winston
```

Group by Layer (self-declared first, overrides second, fallback last). Indicate org-scoped tools with `[klever]` or `[supervisr]` tag.

### `--persona <name>` (Filter by Persona)

List all tools where `personas` includes the named persona, across all bays. Group by bay.

### `--all` (Full Flat List)

All tools grouped by bay. Compact format: one line per tool.

```
## Assembly Line (build)
- /dark-factory — Full ticket-to-dev pipeline [klever]
- /autonomous-ticket-ship — Ship scoped ticket autonomously [klever]
- /bmad-epic-lifecycle — Full BMAD concept-to-ship pipeline
- sprint-crawl (agent) — Multiple tickets, overnight autonomous
...

## Mechanics Garage (fix)
- /investigate — Quinn->Amelia->Quinn root cause pipeline [klever]
...
```

---

## Org Filtering

When org is detected from cwd:
- Show all **global** tools (no `org:` tag)
- Show tools matching the detected org
- **Hide** tools tagged for a different org

Exception: `--all` shows everything but marks org-scoped tools.

---

## Presentation Rules

1. **Max 3 recommendations** in recommender mode. Use progressive disclosure.
2. **Exact invocation syntax** always shown. User should be able to copy-paste.
3. **`when_not` is critical** for disambiguation. Always show it when two similar tools appear.
4. **Persona names** displayed only when relevant (user asked, or persona is distinctive for the tool).
5. **No SKILL.md content dumping.** Show routing info only. The user invokes the skill separately.
6. **Layer 3 tools** get a note: "(no nav: frontmatter, routing by description match)"

---

## Disambiguation Rules

When two skills seem to overlap, use `when_not` to disambiguate:

| Pair | Resolution |
|------|-----------|
| `/investigate` vs `/systematic-debugging` | investigate is the full Quinn pipeline; systematic-debugging is the superpowers skill invoked inside investigate |
| `/adversarial-cascade` vs `/challenge` | adversarial-cascade reviews code; challenge reviews ideas/decisions |
| `/adversarial-cascade` vs `/test-adversarial` | adversarial-cascade reviews implementation; test-adversarial reviews test validity |
| `/dark-factory` vs `/autonomous-ticket-ship` | dark-factory is multi-phase pipeline; autonomous-ticket-ship is faster, less ceremony |
| `/dark-factory` vs `sprint-crawl` (agent) | dark-factory is interactive; sprint-crawl is overnight autonomous |
| `/morning-primer` vs `/morning-brief` | primer is standalone recon; brief processes a transcript/recording |
| `/sitrep` vs `/morning-primer` | sitrep is on-demand status; primer is daily structured recon |
| `/klever-local-stack` vs `/klever-local-stack-real-bq` | basic local is mock data; real-bq wires to dev BigQuery |
| `/bibliotheque-librarian` vs `/bibliotheque-refresh` | librarian processes inbox entries; refresh re-distills after Notion export |

---

## Implementation Notes

**Reading Layer 1:** Use `Glob` to find `~/.claude/skills/*/SKILL.md`, then `Read` each file's first 20 lines to extract YAML frontmatter. Parse `nav:` block. Cache in working memory for the session.

**Reading Layer 2:** `Read ~/.claude/library/context/harness-overrides.yaml`. Parse YAML.

**Reading Layer 3:** The system-reminder skill list is already in context. Scan for skill names not found in Layer 1 or Layer 2. Extract description text. Apply keyword matching.

**Performance:** Layer 1 scan touches ~87 files but only reads frontmatter (first 10-20 lines each). Dispatch to a Sonnet subagent for the scan to keep orchestrator context clean. Layer 2 is one file. Layer 3 is already in context.
