# Nuggets Extracted from Archived Proposals

Valuable ideas extracted before archiving. These should be cross-pollinated into existing tools.

Last updated: 2026-04-21

---

## From: overnight-mission (2026-04-13)
**Superseded by:** sprint-crawl agent + ralph-loop plugin

### Nugget 1: GREEN_LIGHT.md / BLOCKER.md Disk-Gated Phase Handoff
Instead of a single continuous crawl, split into Alpha (investigate) and Bravo (execute) phases with a binary file on disk as the gate. The outer loop reads the file to decide whether to proceed. This prevents execution starting before investigation is complete.

**Where it could go:** sprint-crawl agent or ralph-loop plugin as an optional two-phase mode.

### Nugget 2: Per-Iteration Constraint Anchor File
Write hard guardrails to disk before going headless. The agent re-reads this file at the start of each iteration to prevent drift across compaction boundaries. Current night-crawl has inline Critical Rules but no disk-committed anchor.

**Where it could go:** sprint-crawl agent (add "read constraints file at iteration start" to compaction survival protocol).

### Nugget 3: 6-Track Investigation Structure
For open-ended debugging (not test-gate work), use parallel investigation tracks: (1) deployment state, (2) e2e smoke, (3) dashboard/read path, (4) auth chain, (5) toolkit validation, (6) workaround discovery. Night-crawl's test-gate model doesn't cover this.

**Where it could go:** bibliothèque operations as a debugging investigation template. Or a new agent mode for sprint-crawl.

---

## From: split-session-handoff (2026-04-13)
**Superseded by:** sprint-crawl + worktree + SESSION_STATE.md convention

### Nugget 4: 11-Item Handoff Checklist
Every session handoff must include: (1) mission in one sentence, (2) hard guardrails, (3) required reading list in order, (4) known facts section, (5) output location on disk, (6) return format with max word count, (7) coordination rules if parallel work, (8) "do not ask user questions" directive if offline, (9) data-on-disk rule reminder, (10) branch name + last commit SHA, (11) next AC or task.

Sprint-crawl's sendoff is less granular. This checklist fills the gap.

**Where it could go:** SESSION_STATE.md template or sprint-crawl sendoff spec.

### Nugget 5: Parallel-Session Coordination Rules
When two terminal sessions run against the same repo: (a) each session's brief names which files/branches it owns, (b) ownership conflicts are resolved by the INDEX.md on disk, (c) sessions must NOT touch files outside their ownership scope.

**Where it could go:** CLAUDE.md rule (already partially there as "Ralph Loop Multi-Terminal Conflicts"). Could be expanded.

### Nugget 6: Offline Decision Taxonomy
Categories of decisions the agent makes unilaterally when user is offline: (a) minor scope adjustments that don't change the AC, (b) test fixture gaps (create fixtures, don't skip tests), (c) dependency version bumps (patch only), (d) file placement within existing structure. Categories that MUST block: (a) IAM/auth changes, (b) spec contradictions, (c) data mutations, (d) external posts.

**Where it could go:** sprint-crawl agent or global CLAUDE.md (autonomous mode rules).

---

## From: pr-inventory-scan (2026-04-20)
**Superseded by:** pr-response-sweep + colleague-review agents

### Nugget 7: Staleness Threshold
PRs open >4 weeks should be flagged for explicit human decision (close, merge, or escalate). Neither existing agent classifies by age.

**Where it could go:** pr-response-sweep agent (add Phase 0 triage before comment analysis).

### Nugget 8: Branch-Behind-Main Detection
Check whether PR branch is behind base branch by N commits. Surface as a warning. Current agents focus on diff content, not branch health.

**Where it could go:** pr-response-sweep or a pre-ship-check enhancement.

### Nugget 9: PR-Level Action Categorization
Categorize each PR by who needs to act: (a) author action needed, (b) reviewer action needed, (c) blocked on CI, (d) stale no activity. This triage layer is absent from both existing agents.

**Where it could go:** pr-response-sweep Phase 0, or a standalone lightweight script.

---

## From: session-close-hook (2026-04-03, merged 2026-04-12)
**Superseded by:** PreCompact/Stop hooks in settings.json

### Nugget 10: Structural Validation Pass
After each session, verify: (a) every new file has a corresponding INDEX.md update, (b) no dead links introduced in CLAUDE.md On-Demand Context table, (c) MEMORY.md is still index-only (no inline prose >3 lines), (d) library CATALOG.md updated for any new library files.

Knowledge mining already fires. This hygiene check doesn't.

**Where it could go:** A lightweight post-session hook or a monthly `/context-audit` skill.

---

## Pure Duplicates (no nuggets)

- **placer-api-integration** — every item already in `klever-placer-api` skill
- **sprint-close-sequencing-gate** — bug already fixed in sprint-close
- **paralysis-pivot** — already a CLAUDE.md rule + feedback memory
