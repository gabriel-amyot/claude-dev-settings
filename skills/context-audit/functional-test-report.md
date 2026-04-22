# Context Audit Skill — Functional Test Report

**Date:** 2026-04-21
**Tester:** Claude Sonnet 4.6 (automated functional test run)
**Skill version tested:** SKILL.md as of 2026-04-21

---

## Scenario

Audit project-management CLAUDE.md On-Demand Context table against real disk state, then audit the associated MEMORY.md for format compliance and staleness.

## Input

- **Primary:** `/Users/gabrielamyot/Developer/supervisr-ai/project-management/CLAUDE.md` — On-Demand Context table (lines 169–185)
- **Secondary:** `/Users/gabrielamyot/.claude/projects/-Users-gabrielamyot-Developer-supervisr-ai-project-management/memory/MEMORY.md`
- **Severity matrix:** `/Users/gabrielamyot/.claude/skills/context-audit/references/severity-matrix.md`

## Steps Executed

### Step 0 — Load Severity Matrix
Read `references/severity-matrix.md`. Thresholds confirmed: P0 = dead link, P1 = file >200 lines or MEMORY.md entry >150 chars, P2 = date header >90 days old, P3 = missing infrastructure.

### Step 3c — On-Demand Context Table: File Existence Check

Extracted 8 paths from the project CLAUDE.md On-Demand Context table plus the "always-on" entry. Resolved all relative to `project-management/` root and ran existence checks.

| Path | Exists? |
|------|---------|
| `general/AGENT_BRIEFING.md` (always-on) | OK |
| `documentation/org-team.md` | OK |
| `.repo-index.yaml` | OK |
| `documentation/architecture/` | OK (directory) |
| `documentation/architecture/contracts/` | OK (directory) |
| `documentation/process/bmad-persona-guide.md` | OK |
| `documentation/process/skills-and-agents-index.md` | OK |
| `documentation/bibliotheque/INDEX.md` | OK |

All 8 entries resolve. **No P0 dead links found in the On-Demand Context table.**

### Step 1a — MEMORY.md Dead Link Check

Extracted all `(filename.md)` references from MEMORY.md using macOS-compatible grep. Checked each against the memory directory.

Result: **No dead links.** All 58 linked files exist on disk.

### Step 1b — MEMORY.md Bloat Check

**Entry line length (threshold: 150 chars):**

Every single entry line in MEMORY.md (`^- [`) exceeds 150 characters. Total violating lines: 57 out of 58 entries. Counts range from 151 to 243 characters per entry.

Representative worst offenders:
- Line 39 (`feedback_empty_dashboard_triage.md`): 224 chars
- Line 60 (`project_supervisr_strategic_pivot.md`): 227 chars
- Line 6 (`feedback_interactions_mv_key_contract.md`): 243 chars

**Total MEMORY.md line count:** 83 lines (threshold: 500) — within bounds.

**Individual memory file line counts:** All files are well under 200 lines. The largest is `reference_spv92_auth_and_tools.md` at 81 lines. No P1 bloat on individual files.

### Step 1c — Staleness Check

Scanned all memory files for `^Date:` headers. **None found.** No structured date headers exist in this memory directory.

Spot-checked 5 project context files for open-blocker staleness:

| File | Dated | Open blockers as stated | Still open? | Assessment |
|------|-------|------------------------|-------------|------------|
| `project_spv3_closure_blockers.md` | 2026-04-10 (11 days ago) | Auth0 M2M creds, clarifying org missing from tick, EQS PR #8 | Unknown — within 30-day threshold | **Not stale yet** |
| `project_spv92_pr_queue.md` | 2026-04-17 (4 days ago) | 6 PRs waiting on Gab merge (HAQ-12) | Very recent | **Not stale** |
| `project_gateway_rs_auth_regression.md` | Referenced as "pending merge" | PR #20 awaiting Gab | Very recent | **Not stale** |
| `reference_spv92_auth_and_tools.md` | 2026-04-12 (9 days) | Active reference, no blockers listed | N/A | **Not stale** |
| `project_supervisr_strategic_pivot.md` | 2026-04-13 (8 days) | No blockers, strategic context | N/A | **Not stale** |

No files exceed the 90-day date threshold. No closed-blocker-as-open patterns detected within the files spot-checked.

### Step 4 — Bibliothèque Subdirectory Index Check

All three required subdirectory indexes exist:
- `documentation/bibliotheque/operations/INDEX.md` — OK
- `documentation/bibliotheque/stack/INDEX.md` — OK
- `documentation/bibliotheque/inbox/INDEX.md` — OK

---

## Findings

### P0 — Dead Links (0)

None found.

### P1 — Bloat (1 systemic issue)

- **MEMORY.md entry length:** 57 of 58 entries exceed the 150-character threshold. This is a systemic issue, not an isolated violation. The entries are well-written summaries, but every one of them contains enough inline detail to exceed the limit. The linked files hold full context, but the MEMORY.md entries are acting as mini-summaries rather than index pointers.
  - Recommended: Trim each entry to a single-sentence pointer (≤150 chars). The rule is "label + one-liner." Current entries repeat content that already lives in the linked file.
  - This is safe to fix in batches with approval. No content loss — the linked files are complete.

### P2 — Staleness (0)

No date headers found in any memory file. All project context files spot-checked are recent (within 11 days). No closed-blocker-as-open patterns detected.

### P3 — Missing Infrastructure (0)

All required infrastructure is present: MEMORY.md exists with standard sections, On-Demand Context table is present, Bibliothèque INDEX.md and all three subdirectory indexes exist.

---

## Summary

```
Total findings: 1 (P0: 0, P1: 1 systemic, P2: 0, P3: 0)
Auto-fixable with approval: P1 — trim MEMORY.md entries to ≤150 chars
Requires manual decision: none
```

The systemic P1 is worth addressing but is low urgency. The infrastructure is clean, all links resolve, and the memory is current. The MEMORY.md entry length issue is a style/discipline problem: entries were written as useful summaries rather than strict index pointers. Trimming them would reduce token overhead when MEMORY.md is loaded into context.

---

## Output Quality Assessment

The skill's steps are well-structured and executable. Step 0 (load severity matrix) correctly grounds classification before findings. Steps 1a (dead link), 1b (bloat), 3c (table path check), and 4 (Bibliothèque) all produced clear, actionable outputs with real data.

One minor friction point: the dead link extraction command in the skill uses `grep -oP` (Perl-regex mode) which fails on macOS (BSD grep). The command needed to be adapted to `grep -o '([^)]*\.md)'` for macOS compatibility. This is a latent portability bug in the skill's detection commands.

The severity matrix is comprehensive and correctly separates the four levels. The report format (Step 6) is well-defined and easy to populate.

---

## Grade

**PARTIAL**

The skill's audit logic is correct and found real findings (the systemic P1 bloat in MEMORY.md entries). The output format is useful and the severity classification is accurate. The grade is PARTIAL rather than PASS because:

1. The detection command for dead links (`grep -oP`) fails on macOS without adaptation. An agent executing this skill verbatim on a Mac would get a grep error and miss the dead link check entirely.
2. The staleness check (Step 1c) relies on `^Date:` headers that this project's memory files do not use. The skill has no fallback detection for projects that embed dates inline rather than in frontmatter headers. This means the staleness check silently produces a false "no stale files" result even though project context files do contain inline dates (e.g., "As of 2026-04-10").

Both gaps are fixable. The core logic is sound.

### Recommended Fixes for the Skill

1. **macOS grep portability:** Replace `grep -oP '\(.*?\.md\)'` with `grep -oE '\([^)]+\.md\)'` which works on both GNU and BSD grep.
2. **Staleness detection fallback:** Add a secondary staleness check for files that embed dates inline (e.g., `grep -r "as of [0-9]{4}-[0-9]{2}"`) and compare against today minus 90 days.
