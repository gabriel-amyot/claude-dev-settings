---
name: context-audit
description: Audits context engineering health across memory files, library links, and MEMORY.md entries. Run monthly or when token usage feels high, or when onboarding a new org.
---

# Context Audit

Perform a structured health check of the context engineering infrastructure. Detect dead links, bloated files, stale knowledge, and missing scaffolding. Report findings by severity and execute safe fixes on approval.

Severity classification follows `references/severity-matrix.md`. Read it before auditing.

---

## When to Run

- Monthly, as a standing maintenance task.
- When token usage feels high or agents seem to be missing context.
- When onboarding a new org (use `--compare` to benchmark against an established org).
- After a major cleanup, ticket closure sprint, or MEMORY.md purge.
- After a session where a dead link or stale rule caused a mistake.

---

## Usage

```
/context-audit                      # Full audit, all orgs, report only
/context-audit --fix                # Full audit + execute no-brainer fixes (with approval per fix)
/context-audit --org supervisrai    # Limit to one org
/context-audit --compare klever     # Compare target org against klever as reference org
/context-audit --scope memory       # Audit only memory files
/context-audit --scope library      # Audit only ~/.claude/library/
/context-audit --scope claude-md    # Audit only CLAUDE.md On-Demand Context tables
```

---

## Step 0 — Load Severity Matrix

Read `references/severity-matrix.md` before starting. It defines exact thresholds for P0/P1/P2/P3, examples, detection commands, and recommended actions. Do not classify findings from memory.

---

## Step 1 — Audit Memory Files

Memory files live at `~/.claude/projects/*/memory/`. Each project has a directory there; each directory contains `MEMORY.md` (the index) and linked detail files.

### 1a. Detect dead links in MEMORY.md

For every line in MEMORY.md that follows the format `- [Label](filename.md)`, extract the filename and verify it exists in the same directory.

```bash
# Extract linked filenames from MEMORY.md
grep -oP '\(.*?\.md\)' ~/.claude/projects/*/memory/MEMORY.md | tr -d '()'
```

For each extracted path: resolve it relative to the MEMORY.md's directory, then run `test -f`. Any path that does not resolve = **P0 dead link**. Record the exact MEMORY.md line and the missing filename.

### 1b. Check for bloat

```bash
wc -l ~/.claude/projects/*/memory/*.md | sort -rn | head -30
```

Any file exceeding 200 lines = **P1 bloat**. Record the filename and line count.

For MEMORY.md specifically: count characters per entry line (lines matching `^- \[`). Any entry line exceeding 150 characters = **P1 bloat**. Record the line number and current length.

```bash
awk '/^\- \[/ && length($0) > 150 { print NR": "length($0)" chars: "substr($0,1,80)"..." }' \
  ~/.claude/projects/*/memory/MEMORY.md
```

### 1c. Check for staleness

Find files with explicit date headers older than 90 days:

```bash
grep -rl "^Date:" ~/.claude/projects/*/memory/
```

For each match, read the `Date:` value and compare to today. Any file dated more than 90 days ago with no `Last reviewed:` line = **P2 stale**. Record the filename and date.

Also scan for project context files (`project_*.md`) that reference open blockers or pending PRs. Cross-reference against current Jira and GitLab state where feasible. Any open blocker that resolved more than 30 days ago = **P2 stale**.

### 1d. Check for missing MEMORY.md

```bash
ls ~/.claude/projects/*/memory/MEMORY.md 2>/dev/null
```

Any project directory in `~/.claude/projects/` that has a `memory/` folder but no `MEMORY.md` = **P3 missing infrastructure**.

---

## Step 2 — Audit Library

The user-level library lives at `~/.claude/library/`. It holds cross-org operational knowledge.

### 2a. Verify library root and INDEX.md exist

```bash
test -d ~/.claude/library && echo OK || echo "MISSING: ~/.claude/library/"
test -f ~/.claude/library/INDEX.md && echo OK || echo "MISSING: ~/.claude/library/INDEX.md"
```

Either missing = **P3 missing infrastructure**.

### 2b. Detect dead links in the On-Demand Context table

Read `~/.claude/library/INDEX.md`. Find the On-Demand Context table (rows with `| Trigger | File |` header). For each file path in the table, verify it exists on disk.

Also scan `~/.claude/CLAUDE.md` for its On-Demand Context table and run the same check.

Any path in a table that does not exist = **P0 dead link**. Record the table file, the trigger description, and the missing path.

### 2c. Check for orphaned library files

List all `.md` files under `~/.claude/library/context/`. For each file, verify it appears at least once in an On-Demand Context table (in `~/.claude/CLAUDE.md` or `~/.claude/library/INDEX.md`) or in an INDEX.md under `~/.claude/library/`.

Files that exist but are not referenced anywhere = **P1 bloat** (orphaned). Record the filename. These are not dead links (the file exists) but they are unreachable via progressive disclosure.

---

## Step 3 — Audit CLAUDE.md On-Demand Context Tables

Each CLAUDE.md file (global and project-level) must have an On-Demand Context table. The table must follow the `| Trigger | File |` format.

### 3a. Find all CLAUDE.md files in scope

```bash
# Global
~/.claude/CLAUDE.md

# Project-level (supervisr-ai)
~/Developer/supervisr-ai/project-management/CLAUDE.md

# Add others per org as needed
```

### 3b. For each CLAUDE.md, verify the table exists

Read the file and search for `| Trigger | File |`. If the table is absent = **P3 missing infrastructure**.

### 3c. For each table row, resolve the file path

Extract every path in the File column. For paths starting with `~`, expand to the full home directory path. Run `test -f` on each. Any missing path = **P0 dead link**.

### 3d. Flag unconditionally-loaded files that could be deferred

Any file that is read on every run (not listed as on-demand) but exceeds 100 lines where most content is workflow-specific = flag as a **P1 bloat** candidate for review. This is advisory — do not auto-fix without user confirmation.

---

## Step 4 — Audit Project Bibliothèques

Each active org must have a Bibliothèque at `{org-root}/project-management/documentation/bibliotheque/INDEX.md`.

Check known orgs:

```bash
test -f ~/Developer/supervisr-ai/project-management/documentation/bibliotheque/INDEX.md || echo "MISSING: Supervisr Bibliothèque"
test -f ~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/INDEX.md || echo "MISSING: Klever Bibliothèque"
```

Any missing Bibliothèque INDEX.md for an org with active work = **P3 missing infrastructure**.

If the Bibliothèque exists, spot-check: verify that at least the `operations/`, `stack/`, and `inbox/` subdirectories each have their own `INDEX.md`. Missing subdirectory indexes = **P3**.

---

## Step 5 — Compare Against Reference Org (Optional, `--compare` flag)

When `--compare {org}` is provided, use the named org as the reference baseline. Count its:
- Memory file count and average line length
- Library context file count
- On-Demand Context table row count
- MEMORY.md entry count

Then compare the target org against these counts. Flag gaps of more than 50% as **P3 missing infrastructure** with the note "Significantly underbuilt vs reference org {org}."

This step is informational only. Do not auto-create files based on comparison.

---

## Step 6 — Compile Report

After completing all audit steps, produce a structured findings report. Group findings by severity, P0 through P3.

### Report Format

```
## Context Audit Report — {DATE}
Scope: {orgs audited} | Flags: --fix={true/false} --compare={org or none}

### P0 — Dead Links ({count})
- [ ] {MEMORY.md or CLAUDE.md path}, line {N}: `{missing-file-path}`
  → Recommended: {remove entry | update path to X}

### P1 — Bloat ({count})
- [ ] {filename}: {N} lines (threshold: 200)
  → Recommended: extract detail to {target location}, trim to summary
- [ ] MEMORY.md line {N}: {M} chars (threshold: 150)
  → Recommended: trim to one-liner, detail already in linked file

### P2 — Staleness ({count})
- [ ] {filename}: dated {YYYY-MM-DD} ({N} days ago), no review signal
  → Recommended: verify rule still valid, add `Last reviewed:` line or archive

### P3 — Missing Infrastructure ({count})
- [ ] {expected-path} does not exist
  → Recommended: scaffold empty file/folder with standard structure

### Summary
Total findings: {N} ({P0}: {n0}, {P1}: {n1}, {P2}: {n2}, {P3}: {n3})
Auto-fixable with approval: {list of P1/P3 items safe to scaffold or trim}
Requires manual decision: {list of P0 and P2 items}
```

Present the full report before taking any action.

---

## Step 7 — Execute Fixes (requires `--fix` flag and per-fix approval)

Without `--fix`, the audit stops at Step 6. Report only.

With `--fix`, present each finding and proposed fix one at a time. Wait for explicit approval before executing. Do not batch approvals.

### Safe Auto-Fixes (present with a yes/no prompt)

**P3 — Scaffold missing MEMORY.md:**
Create with standard section headers only. No content. Sections: `## Feedback`, `## Reference`, `## Project Context`, `## User`, `## Credentials`, `## Infrastructure Rules`.

**P3 — Scaffold missing Bibliothèque INDEX.md:**
Create with empty sections matching the standard template. Do not invent entries.

**P1 — Archive oversized memory file:**
Move the oversized file to `~/.claude/projects/{project}/memory/archive/{filename}-archived-{date}.md`. Update the MEMORY.md entry to note "archived" with the date. Do not delete.

**P1 — Trim long MEMORY.md entry:**
Show the current line. Propose a trimmed version. Apply only on explicit approval.

### Fixes That Require Manual Decision (never auto-fix)

**P0 — Dead link removal:** Always ask the user whether to remove the reference or update the path. The content may have moved, not been deleted.

**P2 — Stale file archival:** Always ask the user to confirm the content is obsolete. The rule may still be valid even if old.

**Anything involving CLAUDE.md edits:** Show the proposed diff and wait for explicit approval before writing.

---

## Step 8 — Post-Audit Housekeeping

After fixing, update any INDEX.md files that reference modified or moved files. If an archived file had an entry in an INDEX.md, update that entry to note the archive status and date.

Do not create new INDEX.md files during the audit unless scaffolding missing infrastructure (P3 fix) with explicit approval.

---

## Common Pitfalls

- Do not assume a dead link means the file is permanently gone. Check git history or ask the user.
- Do not trim MEMORY.md entries without reading the linked file first. If the file has more detail than the entry implies, confirm the file is up to date before shortening the entry.
- Do not mark a project context file as stale just because it's old. Project context files for active tickets are expected to persist.
- Do not compare MEMORY.md line counts across orgs as a quality signal. Older orgs accumulate more entries naturally. Use per-entry character length, not total count, as the bloat signal.
- Credentials files (`reference_auth0_*.md`, etc.) are intentionally terse. Do not flag them as bloat based on line count.
