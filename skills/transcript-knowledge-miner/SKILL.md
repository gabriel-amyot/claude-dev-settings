---
name: transcript-knowledge-miner
description: Mine historical Claude Code session transcripts for reusable knowledge (procedures, gotchas, rules, decisions). Triggers: "mine transcripts", "extract from transcripts", "transcript mining", "knowledge from sessions", "review old sessions". Writes findings to bibliotheque inbox.
nav:
  bay: know
  when: "Mine session transcripts for reusable knowledge: procedures, gotchas, rules, decisions."
  when_not: "Processing a meeting transcript (use /meeting-to-action). Real-time extraction (use /gab-operationalize)."
---

# Transcript Knowledge Miner

Batch-harvest reusable knowledge from historical Claude Code session transcripts and route findings to the correct bibliotheque inbox. Designed for monthly scheduled runs or on-demand catch-up.

**Usage:**
```
/transcript-knowledge-miner                         # Mine N=10 most recent unmined transcripts
/transcript-knowledge-miner --project <slug>        # Mine all transcripts for one project
/transcript-knowledge-miner --all                   # Mine ALL unmined transcripts (slow)
/transcript-knowledge-miner --since YYYY-MM-DD      # Mine sessions since a date
/transcript-knowledge-miner --dry-run               # Report what would be mined, write nothing
```

---

## Phase 1: Discovery

**Locate transcripts:**
- Base path: `~/.claude/projects/`
- Each project is a directory named after the path (e.g., `-Users-gabrielamyot-Developer-supervisr-ai-project-management`)
- Each session is a `.jsonl` file inside the project directory
- Sentinel: a `.{session-id}.mined` file in the project directory marks a transcript as processed

**Build the candidate list:**
1. List all `.jsonl` files under `~/.claude/projects/*/`
2. Exclude any session where a corresponding `.{session-id}.mined` file exists
3. Extract metadata per candidate (no full read yet):
   - Session title: first `custom-title` record (`obj.type == "custom-title"` then `obj.customTitle`)
   - Session ID: from filename (UUID before `.jsonl`)
   - Project slug: parent directory name
   - Line count: `wc -l` as proxy for session depth
4. Sort by modification time, most recent first
5. Apply mode filter (`--project`, `--since`, `--all`, or default N=10)

Report the candidate list before mining. Format:
```
Found N unmined sessions:
  [project-slug] session-title (ID, ~L lines)
  ...
```

If `--dry-run`, stop here.

---

## Phase 2: Metadata Scan (Progressive)

For each candidate, do a **lightweight scan** before deep-reading. This controls token usage.

**Quick scan (always):**
- Read the first 20 lines to get title and agent name
- Count record types: `user`, `assistant`, `system` lines. Sessions with < 5 assistant lines are likely empty or aborted. Skip them, place sentinel, move on
- Check for summary signals: lines containing `SESSION_STATE`, `compaction`, `OPERATIONALIZE`, or `operationalize` in user messages suggest the session was already captured. Note as low-priority

**Score the session:**

| Signal | Score |
|--------|-------|
| Title contains `crawl`, `sprint`, `overnight`, `night-crawl` | +3 (likely high-density) |
| Title contains `debug`, `fix`, `incident`, `rca`, `blocker` | +2 (likely contains gotchas) |
| Line count > 200 | +2 |
| User message contains `NEVER`, `always`, `learned`, `mistake`, `wrong` | +1 per occurrence (cap 3) |
| User message contains `operationalize` or `SESSION_STATE` | -1 (may be already captured) |

Sessions scoring < 1: skip (place sentinel). Sessions scoring >= 4: deep-read. Sessions scoring 1-3: shallow-read.

---

## Phase 3: Content Extraction

### Shallow Read (score 1-3)
Read only `user` messages. Look for:
- Corrections (user pushes back on agent behavior)
- Explicit rules stated by user ("from now on", "always", "never", "don't")
- Problem declarations ("this is broken", "that caused X")

### Deep Read (score >= 4)
Read all `user` AND `assistant` messages. Look for:
- **Procedures** — step sequences with a trigger (agent documents how it solved something)
- **Rules/guardrails** — "never do X", "always Y before Z"
- **Decisions** — choices made between alternatives and the rationale
- **Gotchas** — surprising failures, unexpected behaviors, wrong assumptions corrected
- **Recurring patterns** — same approach used multiple times, candidate procedure
- **Tool/API behaviors** — limits, formats, quirks discovered during session
- **Architecture discoveries** — what exists vs. what was planned, deviations from spec

**JSONL extraction pattern (Python):**
```python
import json

def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                parts.append(item.get('text', ''))
        return '\n'.join(parts)
    return ''

messages = []
with open(transcript_path) as f:
    for line in f:
        obj = json.loads(line.strip())
        if obj.get('type') in ('user', 'assistant'):
            role = obj['type']
            content = extract_text(obj.get('message', {}).get('content', ''))
            if content.strip():
                messages.append((role, content))
```

**Extraction yield target:** 2-5 nuggets per session for deep reads, 0-2 for shallow. If a session yields 0 nuggets after a deep read, that is valid. Note it, place sentinel, move on.

---

## Phase 4: Dedup Check

Before writing any nugget, check against:

1. **`~/.claude/projects/{project}/memory/MEMORY.md`** — scan feedback and reference sections for the same concept
2. **Bibliotheque inbox files** — list filenames and titles in `{org-project-management}/documentation/bibliotheque/inbox/`; check if topic already has an entry in the last 30 days

**Dedup rule:** If the nugget is substantively covered (same rule, same scope, same lesson), skip it. Log as "already captured." Partial overlap is OK. Extract the new angle only.

**Determine target inbox:**
Map the project slug to its org using this table:

| Project slug contains | Org | Inbox path |
|-----------------------|-----|------------|
| `supervisr-ai` | supervisr-ai | `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/inbox/` |
| `grp-beklever-com` | klever | `~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/inbox/` |
| `gabriel-amyot` | personal | `~/.claude/library/inbox/` (create if missing) |
| `origin8` | supervisr-ai (legacy) | `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/inbox/` |
| Unrecognized | global | `~/.claude/library/inbox/` |

---

## Phase 5: Write Findings

**Group nuggets by org-topic**, not by session. One inbox file per topic cluster per run, not one file per session.

**File naming:** `YYYY-MM-DD-{topic-slug}-from-transcripts.md`

**File format (same as `/gab-operationalize`):**
```markdown
# Tribal Knowledge: {topic}

**Source:** Transcript mining — sessions: {session-title-1}, {session-title-2} ({date range})

---

## 1. {nugget title}
{content — the rule, gotcha, procedure, or decision}
**Session:** {session-title} ({session-id prefix, first 8 chars})

## 2. {next nugget}
...

---

**Curator notes:** {classification hints — which section(s) in the bibliotheque this belongs to}
```

**After each file write:**
1. Update `inbox/INDEX.md` with a row: `| {filename} | {date} | transcript-miner | pending |`
2. Place sentinel: create empty file `~/.claude/projects/{project-dir}/.{session-id}.mined`

**Sentinel placement is mandatory.** If writing fails, do NOT place sentinel. Sentinel = "this session's knowledge is safely on disk."

---

## Phase 6: Skill Proposals

If a session yields a nugget describing a **repeatable multi-step procedure** that does not match any existing skill in `~/.claude/skills/`, write a proposal to `~/.claude/skill-proposals/YYYY-MM-DD-{name}.md` using the standard proposal format:

```markdown
# Skill Proposal: {name}
Date: {date}
Source: Transcript mining — {session-title}

## Trigger
{when should this skill be invoked?}

## Scope
{repo-local / org / global}

## Usefulness
{why is this worth a dedicated skill?}

## Draft Steps
{2-5 step outline}
```

---

## Phase 7: Run Report

After processing all candidates, print a summary:

```
Transcript Knowledge Miner — Run Summary ({date})
==================================================
Candidates evaluated:  N
  Skipped (too short):   N
  Skipped (low score):   N
  Shallow-read:          N
  Deep-read:             N

Nuggets extracted:     N
  Already captured:    N (deduped)
  New:                 N

Inbox files written:   N
  supervisr-ai:        N
  klever:              N
  global:              N

Skill proposals:       N

Sessions processed (sentinels placed): N
```

If `--dry-run`, report what WOULD have been written without writing anything. No sentinels placed in dry-run mode.

---

## Safety Rules

- **Read-only on transcripts.** Never modify, move, or delete `.jsonl` files.
- **Sentinels only.** The only files written inside `~/.claude/projects/` are `.{session-id}.mined` sentinels.
- **Never fabricate.** Only extract what is explicitly present in the transcript. Do not infer rules not stated.
- **No secrets.** If a transcript contains credentials, tokens, or keys in plain text, skip that nugget. Never copy raw credentials to inbox files.
- **No external posts.** Findings go to inbox only. Nothing posted to Jira, Slack, or GitHub from this skill.
- **Batch size guard.** Never process more than 50 sessions in a single run without `--all` flag. Protects against context explosion on first run after a long gap.

---

## Scheduling

To schedule monthly runs (1st of month, 3 AM), use the `/schedule` skill:
```
/schedule cron "0 3 1 * *" "/transcript-knowledge-miner"
```

Verify `/schedule` is available before configuring. If unavailable, add to `~/.claude/TODO.md` as a pending automation.

---

> **Guiding principle:** Every transcript is a session someone (or some agent) ran. They solved something, hit a wall, or discovered a pattern. This skill extracts the transferable parts so future sessions don't start from scratch. Prefer extracting concrete, actionable nuggets over vague observations. A rule that can be written in one sentence is better than a paragraph of context.
