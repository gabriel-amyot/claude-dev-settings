# Context Audit Severity Matrix

Reference for the `/context-audit` skill. Every finding gets classified here before being reported or actioned.

---

## P0 — Dead Links

**Definition:** A file path appears in an On-Demand Context table, INDEX.md, or MEMORY.md reference entry but does not exist on disk.

**Threshold:** Any single dead link = P0. There is no acceptable count.

**Examples:**
- `~/.claude/library/context/shipping-workflow.md` listed in CLAUDE.md On-Demand Context table but file deleted.
- `documentation/bibliotheque/stack/debugging-production-perf.md` listed in project CLAUDE.md but never created.
- MEMORY.md reference entry points to `feedback_some_file.md` that was pruned without updating the index line.

**Detection:**
```bash
# For each path in On-Demand Context tables and MEMORY.md reference lines,
# run: test -f "$path" && echo OK || echo DEAD: $path
```

**Recommended Action:**
- If the linked file was renamed: update the reference path.
- If the content still exists in another file: update the reference to the correct path.
- If the content is gone and obsolete: remove the table row or MEMORY.md entry.
- Never remove a reference without confirming the content is truly gone or superseded.

**Risk:** Agents load context on-demand by following these references. A dead link silently skips context, causing agents to work with incomplete information. This is the highest-severity finding.

---

## P1 — Bloat

**Definition:** Memory or context files have grown beyond useful size, increasing load cost without proportional value.

**Thresholds:**

| File Type | Bloat Threshold |
|-----------|----------------|
| Any single `~/.claude/projects/*/memory/*.md` file | > 200 lines |
| Any single MEMORY.md index entry (one bullet line) | > 150 characters |
| MEMORY.md total line count | > 500 lines |
| Any On-Demand Context file loaded unconditionally | > 100 lines that could be deferred |
| Inline prose block in MEMORY.md (multi-line under one entry) | > 3 lines |

**Examples:**
- A feedback file (`feedback_webclient_bodyvalue_string.md`) that started as a 3-line lesson has grown to 250 lines with full code examples, stack traces, and historical context that belongs in a ticket report.
- A MEMORY.md entry reads: `- [Some rule](file.md) — Full paragraph explaining the entire incident from 2026-03-01 including all the services involved, what went wrong, what the fix was, and three caveats about edge cases that haven't been seen since.`
- A context file is loaded unconditionally (not on-demand) but 80% of its content is only relevant to one specific workflow.

**Detection:**
```bash
wc -l ~/.claude/projects/*/memory/*.md | sort -rn | head -20
# For MEMORY.md entries: awk '{ if (length($0) > 150) print NR": "length($0)" chars: "$0 }' MEMORY.md
```

**Recommended Action:**
- For oversized feedback/reference files: extract detailed content into a ticket report or library entry. Keep the memory file as a 3-5 line summary with a pointer.
- For long MEMORY.md entries: trim to the essential one-liner. The detail belongs in the linked file.
- For inline prose blocks: extract to the linked file, replace with a one-liner.
- Always preserve the linked file — only trim the MEMORY.md entry or the memory file's preamble.

**Risk:** Bloated memory files slow context loading and dilute signal. Agents spend tokens on old war stories instead of actionable rules.

---

## P2 — Staleness

**Definition:** A memory or context file contains a date in its header or frontmatter that is older than 90 days and shows no evidence of recent review or update.

**Thresholds:**

| Signal | Staleness Threshold |
|--------|---------------------|
| File header date (e.g., `Date: 2026-01-01`) | > 90 days from today |
| MEMORY.md entry referencing a specific incident date | > 180 days with no follow-up note |
| On-Demand Context file with a "Last updated" field | > 90 days |
| Project context file (e.g., `project_*.md`) referencing an open blocker | Blocker is listed as open but ticket is closed |

**Examples:**
- `reference_spv3_harness.md` has `Date: 2026-01-15` and SPV-3 has since closed, making the gotchas potentially obsolete.
- A project context file says "SPV-92 PR queue — 6 PRs approved, waiting on Gab" but all PRs merged 60 days ago.
- A feedback file references a workaround for a bug that was fixed in a library upgrade.

**Detection:**
```bash
# Find files with date headers older than 90 days
grep -rl "^Date:" ~/.claude/projects/*/memory/ | xargs grep "^Date:" | awk -F': ' '{ print $1": "$2 }'
# Manually verify project context entries against current Jira/GitLab state
```

**Recommended Action:**
- For closed ticket references: update the project context file with resolution status or archive it.
- For workaround files where the root cause is fixed: add a `## Status: Superseded` section noting the fix, or delete and remove the MEMORY.md entry.
- For files where the rule is still valid but the date is old: add a `Last reviewed: YYYY-MM-DD` line to reset the staleness clock.
- Do not delete stale files blindly. Verify the rule is still relevant first.

**Risk:** Stale context is worse than no context. Agents follow outdated rules, apply retired workarounds, or reference closed blockers as active.

---

## P3 — Missing Infrastructure

**Definition:** An org or project is missing standard context engineering infrastructure that the framework requires.

**Thresholds:** Any of the following missing = P3:

| Required Component | Expected Location | Notes |
|-------------------|------------------|-------|
| MEMORY.md | `~/.claude/projects/{project-hash}/memory/MEMORY.md` | Index-only format. Must exist for any active project. |
| User library root | `~/.claude/library/` | Cross-org operational knowledge home. |
| User library INDEX.md | `~/.claude/library/INDEX.md` | Entry point for the library. |
| On-Demand Context table | In each CLAUDE.md | Must be present in global and project-level CLAUDE.md files. |
| Org Bibliothèque | `{org-root}/project-management/documentation/bibliotheque/INDEX.md` | Required for each org with active work. |
| Ticket index | `{org-root}/project-management/tickets/` | Must exist for any org with active tickets. |

**Examples:**
- New org onboarded but `documentation/bibliotheque/INDEX.md` never created — agents have no domain knowledge index.
- MEMORY.md exists but has no sections (no `## Feedback`, `## Reference`, `## Project Context`) — agents can't navigate it by category.
- CLAUDE.md exists but On-Demand Context table was deleted during a cleanup — agents don't know what to load when.
- `~/.claude/library/` exists but `INDEX.md` is missing — agents can't discover what's in the library.

**Detection:**
```bash
# Check for MEMORY.md
ls ~/.claude/projects/*/memory/MEMORY.md 2>/dev/null || echo "MISSING: MEMORY.md"

# Check for library
test -d ~/.claude/library && test -f ~/.claude/library/INDEX.md || echo "MISSING: library/INDEX.md"

# Check for org Bibliothèques (Supervisr)
test -f ~/Developer/supervisr-ai/project-management/documentation/bibliotheque/INDEX.md || echo "MISSING: Supervisr Bibliothèque"
```

**Recommended Action:**
- For missing MEMORY.md: create with the standard section structure (`## Feedback`, `## Reference`, `## Project Context`, `## User`, `## Credentials`, `## Infrastructure Rules`). Do not backfill content — leave sections empty until real knowledge is captured.
- For missing library: create `~/.claude/library/` and `INDEX.md` with an empty On-Demand Context table. Do not invent entries.
- For missing Bibliothèque: create the INDEX.md using the standard template. Do not populate with guessed content.
- For missing On-Demand Context table in CLAUDE.md: add the table with the standard trigger/file headers. Populate only with entries that have confirmed files on disk.

**Risk:** Missing infrastructure means agents skip context loading entirely. The framework's progressive disclosure model breaks silently — agents operate without domain knowledge, rules, or history.

---

## Severity Summary Table

| Level | Name | Threshold | Auto-fix Safe? | Escalate? |
|-------|------|-----------|---------------|-----------|
| P0 | Dead Link | Any unresolvable path in a context table or index | No — verify before removing | Yes — report immediately |
| P1 | Bloat | File > 200 lines or entry > 150 chars | Yes (with approval) — trim, archive | No — batch and report |
| P2 | Staleness | Date > 90 days, no review signal | No — verify content validity first | No — batch and report |
| P3 | Missing Infra | Required file or folder absent | Yes (with approval) — scaffold empty | Only if org is active |

---

## Triage Order

When running a context audit, triage findings in this order:

1. P0 first — dead links break agent behavior immediately. Fix or remove before proceeding.
2. P3 second — missing infrastructure causes silent failures across all future sessions.
3. P1 third — bloat is a tax, not a break. Fix in batches.
4. P2 last — staleness is latent risk. Review and decide per file, not bulk-delete.
