# Bibliothèque Librarian — Functional Test Report

**Skill:** `bibliotheque-librarian`
**Test mode:** GATED (read-only classification)
**Date:** 2026-04-21
**Tester:** Claude Code (Sonnet 4.6)

---

## Scenario

**Classify inbox entries (read-only)**

Run the skill's classification logic (Steps 1–2 of SKILL.md) against all 7 pending inbox entries. No files are created, moved, or modified. Report what the skill would do if approved.

---

## Input

`inbox/INDEX.md` contains 7 entries, all with `Status: pending`:

| # | File | Date | Source |
|---|------|------|--------|
| 1 | 2026-04-20-gcloud-multi-org-safety.md | 2026-04-20 | gcloud multi-org refactor + nuke_entities review |
| 2 | 2026-04-20-git-large-file-gitignore-hygiene.md | 2026-04-20 | SPV-92 343MB push blocked |
| 3 | 2026-04-20-pr-housekeeping-eqs-retell.md | 2026-04-20 | EQS PR staleness, FilterQueryValue coercion |
| 4 | 2026-04-21-overnight-crawl-spv165-learnings.md | 2026-04-21 | SPV-165 overnight crawl infrastructure learnings |
| 5 | 2026-04-21-bibliotheque-catalog-design-patterns.md | 2026-04-21 | Three-lane catalog, bootstrap hygiene, section triggers |
| 6 | 2026-04-21-spv165-rca-debugging-patterns.md | 2026-04-21 | DAC forward-merge speed, exponential backoff, LLM tunnel vision |
| 7 | 2026-04-21-cross-org-persona-wiring.md | 2026-04-21 | Symlink-not-copy, four-point CLAUDE.md persona wiring |

---

## Pre-Classification State Check

Root INDEX already contains entries for several topics that appear in the inbox. Noted to prevent duplicate rows:

- "Pipeline fails at `terraform init`" → already has a Blocked row pointing to `operations/cicd-registry-maintenance-window.md`
- "DAC pipeline ran on main/prod unexpectedly" → already has a Blocked row pointing to the SPV-165 RCA
- "Same pipeline failing 10+ times in a row" → already has a Blocked row
- "Agent chasing wrong hypothesis" / LLM tunnel vision → already has a Blocked row pointing to `stack/debugging-regression-first-question.md`
- "Gateway → subgraph returns 401" → already has a Blocked row pointing to `stack/gateway-dual-header-401.md`
- "Service → gateway returns 400" → already has a Blocked row pointing to `stack/service-to-service-400-content-type.md`

Section INDEXes: `stack/INDEX.md` and `operations/INDEX.md` both contain real content (no bootstrap placeholder). Bootstrap hygiene rule does not apply to these.

---

## Per-Entry Classification

---

### Entry 1: `2026-04-20-gcloud-multi-org-safety.md`

**Content summary:** 6 nuggets covering: shared-config hook auto-sync, stateless gcloud account switching, hardcoded safety fallbacks, backup integrity gates, destructive `--yes` countdown timers, and gitignoring backup directories.

**Nugget breakdown:**

| # | Nugget | Section | Lane | Notes |
|---|--------|---------|------|-------|
| 1 | Shared-config hook auto-syncs to ~/.claude/skills/ | `documentation/process/` | Do Something | Tooling maintenance pattern; not domain/stack knowledge. Route to process docs or CLAUDE.md harness rules. |
| 2 | Stateless gcloud account switching (`--account=`) | `operations/` | Blocked + Do Something | "Multiple sessions pollute each other's auth" = a Blocked failure symptom; the fix is a Do Something pattern. New file: `operations/gcloud-multi-session-safety.md` |
| 3 | Safety-critical config needs hardcoded fallbacks | `operations/` | Understand | General safety design pattern for destructive scripts. Extend or create `operations/destructive-script-safety.md` |
| 4 | Backup integrity gate (abort on partial) | `operations/` | Do Something | Extends the backup-before-mutation principle. Same new file as #3 or CLAUDE.md rule. |
| 5 | `--yes` flag countdown timer pattern | `operations/` | Do Something | Same file as #3-4. |
| 6 | Backup directories must be gitignored | `operations/` or `documentation/process/` | Do Something | Also relevant to git hygiene (Entry 2). Could consolidate. |

**Proposed section(s):** `operations/` (primary for #2-6); `documentation/process/` for #1 (tooling convention).

**Proposed lane(s):** Blocked (#2), Do Something (#2-6), Understand (#3). Root INDEX row warranted for #2 (new Blocked: "gcloud session pollutes another session's auth context" symptom). Items 3-6 are section-INDEX-only.

**Confidence:** MEDIUM — Nuggets 3-6 could consolidate into one file or extend an existing safety pattern doc. Need to check if `operations/` has an existing destructive-script-safety file.

**Notes:** The curator pre-notes say "#1-2 tooling/infra, #3-6 safety patterns." Nugget 1 (shared-config hook) is meta-tooling that probably belongs in `~/.claude/CLAUDE.md` or a harness config note, not the Bibliothèque.

---

### Entry 2: `2026-04-20-git-large-file-gitignore-hygiene.md`

**Content summary:** 5 nuggets on git hygiene: gitignore path mismatch silently allows files, fixing gitignore doesn't untrack already-tracked files, `git filter-repo` fails non-interactively without `--force`, filter-repo strips the remote, broad gitignore pattern for ticket data dirs.

**Proposed section(s):** `operations/` — these are operational/developer hygiene procedures. Alternately a new `stack/git-hygiene.md` if framed as "stack" tooling. `operations/` is the better fit because readers encounter these while executing tasks (committing, pushing), not while debugging service behavior.

**Proposed lane(s):**
- Blocked: "Large file blocked push / gitignore not catching it" → `operations/git-large-file-hygiene.md`
- Do Something: "Remove a large file from git history" → same file
- Do Something: "Re-add remote after git filter-repo" → same file

**Root INDEX rows:** 1 Blocked row ("Push blocked by large/PII file committed to git"), 1 Do Something row ("Remove a committed large file from git history"). Both are high-traffic situations worth root-level visibility.

**Confidence:** HIGH — content is self-contained, clear scope, no overlap with existing entries.

**Notes:** Curator notes say "Git Gotchas section or dev hygiene." `operations/` already exists and fits; no need for a new section. New file: `operations/git-large-file-hygiene.md`.

---

### Entry 3: `2026-04-20-pr-housekeeping-eqs-retell.md`

**Content summary:** 5 nuggets on PR management: FilterQueryValue pre-coerces scalars (dead code warning), stale PR detection pattern, origin8-web uses `master` not `main`, adversarial elicitation before merging "looks needed" PRs, cherry-pick detection via GitHub compare API.

**Nugget breakdown:**

| # | Nugget | Section | Lane |
|---|--------|---------|------|
| 1 | FilterQueryValue handles coercion before DatastoreQueryAdapter | `stack/` | Understand |
| 2 | Stale PR detection pattern (4+ weeks old, check main diff) | `operations/` | Do Something |
| 3 | origin8-web uses `master` not `main` | `stack/` or `operations/` | Understand / Do Something |
| 4 | Adversarial elicitation before merge (4-step checklist) | `operations/` | Do Something |
| 5 | PR cherry-pick detection via GitHub compare | `operations/` | Do Something |

**Proposed section(s):** `stack/` for #1 and #3 (EQS internals, repo conventions). `operations/` for #2, #4, #5 (PR workflow procedures). This is a multi-section entry.

**Proposed lane(s):**
- Understand: "How does EQS FilterQueryValue coercion work?" (#1, section-only — too narrow for root)
- Understand: "Which branch is default on origin8-web?" (#3, root row worth adding)
- Do Something: "Audit a stale PR before merging" (#2+4+5 can consolidate into `operations/pr-merge-audit-pattern.md`)

**Root INDEX rows:** 1 Understand row ("What is the default branch for origin8-web / which repos use `master`?"), 1 Do Something row ("Audit a stale PR before merging").

**Confidence:** HIGH for #2-5 routing to `operations/`. MEDIUM for #1 — it could extend the existing `stack/service-to-service-400-content-type.md` or `stack/INDEX.md` notes, or stand as a new `stack/eqs-filterqueryvalue-coercion.md`. Check if EQS already has a stack file.

**Notes:** Items 2, 4, and 5 are tightly related and should consolidate into one file rather than three.

---

### Entry 4: `2026-04-21-overnight-crawl-spv165-learnings.md`

**Content summary:** 11 nuggets from SPV-165 crawl covering Datasophia nightly downtime, DAC branch model, DAC default branch discovery, Apollo Router header propagation conflict, DGS Content-Type gap, GitLab skill command confusion, gitlab_skill git-push gap, retell-service prod status (project state), gateway auth correct pattern, WebClient.bodyValue double-serialization, RetellFilterCriteria timestamp format.

**Nugget breakdown:**

| # | Nugget | Section | Lane | Already in Root? |
|---|--------|---------|------|-----------------|
| 1 | Datasophia nightly downtime (~11PM-5AM ET) | `operations/` | Blocked + Do Something | YES — `operations/cicd-registry-maintenance-window.md` exists. Extend, don't create. |
| 2 | DAC branch model (dev default, MRs for promotion) | `operations/` | Do Something | YES — RCA row exists. New operational file: `operations/dac-branch-model.md` would add root Do Something row. |
| 3 | DAC default branch discovery (check `origin/HEAD` before pushing) | `operations/` | Do Something | Sub-pattern of #2. Consolidate into same file. |
| 4 | Apollo Router header propagation conflict | `stack/` | Blocked | YES — `stack/gateway-dual-header-401.md` exists. This is deeper detail → extend that file. |
| 5 | DGS MonoGraphQLClient Content-Type gap + WebClient fix | `stack/` | Blocked | YES — `stack/service-to-service-400-content-type.md` exists. This is additive detail → extend. |
| 6 | GitLab skill `pipeline` vs `pipelines` command confusion | `operations/` | Blocked | Already patched in skill. Edge case: document in `operations/` as a gotcha, mark skill as already fixed. |
| 7 | gitlab_skill.py git-push gap (bypasses BLOCKED_REFS) | `operations/` | Blocked | New entry. `operations/gitlab-skill-push-gap.md` or extend a gitlab skill file. |
| 8 | Retell-service not active in prod (project state) | SKIP | None | Project state → `tickets/SPV-165/reports/status/`. Not Bibliothèque content. |
| 9 | Gateway auth correct pattern (Authorization: Bearer M2M) | `stack/` | Understand | Extends `stack/gateway-dual-header-401.md` or could be a standalone `stack/gateway-auth-correct-pattern.md`. |
| 10 | WebClient.bodyValue(String) double-serialization | `stack/` | Blocked | New entry (different from Content-Type / CSRF in #5). New file: `stack/webclient-bodyvalue-double-serialization.md`. Root Blocked row warranted. |
| 11 | RetellFilterCriteria timestamps use epoch milliseconds | `stack/` | Blocked | Check `~/.claude/library/context/retell-api-v2-reference.md` first. If covered there, note cross-reference. If not, new `stack/retell-api-timestamp-format.md`. |

**Proposed section(s):** Multi-section. `operations/` for #1-3, 6-7. `stack/` for #4-5, 9-11. Skip #8.

**Proposed lane(s):**
- Blocked: #10 (bodyValue double-serialization) → new root row
- Blocked: #7 (gitlab skill git-push bypasses guardrail) → section-only or new root row
- Blocked: #11 (RetellFilterCriteria epoch ms) → section-only unless already hitting prod failures
- Do Something: #2+3 (deploy to a DAC repo) → new root row if `operations/dac-branch-model.md` created
- Understand: #9 (gateway auth correct client pattern) → Understand row

**Confidence:** HIGH for section routing. MEDIUM for whether #4-5 extend existing files vs create new ones (the curator notes themselves suggest extension for #4-5, and the existing stack files confirm this is the right call).

**Notes:** Item 8 is project state and must be explicitly skipped per SKILL.md Edge Cases. Items 1, 4, 5 already have root INDEX rows — the skill should extend section files, not add duplicate root rows.

---

### Entry 5: `2026-04-21-bibliotheque-catalog-design-patterns.md`

**Content summary:** 4 meta-patterns about Bibliothèque structure: three-lane catalog design, single CLAUDE.md trigger (one front door), bootstrapped section placeholder hygiene, and section INDEX situational triggers ("Go here when...").

**Proposed section(s):** NONE in `stack/`, `operations/`, or `domain/`. This is pure meta-knowledge about the Bibliothèque itself. Per SKILL.md Edge Cases ("Meta-knowledge about the Bibliothèque itself"), route to:
- `documentation/process/documentation-standards.md` — three-lane pattern and single-trigger rule extend the three-layer model.
- `bibliotheque/PROPOSALS.md` — if any patterns are improvements not yet implemented.
- This skill's own reference file (`three-lane-catalog.md`) — already exists and covers items 1, 3, 4. This entry may be the source for that file.

**Proposed lane(s):** None in root INDEX. Meta-knowledge is internal maintenance, not reader-facing catalog content.

**Confidence:** HIGH — SKILL.md explicitly calls out this exact category. The three-lane-catalog.md reference file already covers items 1, 3, 4 in detail. Item 2 (single CLAUDE.md trigger) is a CLAUDE.md rule, not a Bibliothèque file.

**Notes:** This entry is likely the source material that produced `three-lane-catalog.md`. The actual action is: (1) update `documentation/process/documentation-standards.md` with the three-lane pattern if not already present, (2) update project CLAUDE.md context engineering section with the single-trigger rule if not already captured there. Check `documentation/process/documentation-standards.md` before acting.

---

### Entry 6: `2026-04-21-spv165-rca-debugging-patterns.md`

**Content summary:** 4 nuggets: DAC dev→uat forward-merge speed (same-day promotion risk), exponential backoff for pipeline retries (replacing the hard circuit breaker), Kurt persona for external comms about autonomous work, LLM tunnel vision debugging anti-pattern.

**Nugget breakdown:**

| # | Nugget | Section | Lane | Notes |
|---|--------|---------|------|-------|
| 1 | DAC dev→uat merges same day — wrong commits not "safe for cleanup" | `operations/` | Do Something / Blocked | Extends or creates `operations/dac-branch-model.md` (same as Entry 4 #2). |
| 2 | Exponential backoff (2min → 5min → 15min → declare blocked) | `operations/` | Do Something | Updates the circuit breaker guidance. New entry in `operations/cicd-pipeline-retry-strategy.md` or extend `cicd-registry-maintenance-window.md`. |
| 3 | Kurt persona for external comms | `people/` | Understand | Specific to how autonomous agent work is communicated externally. Could go in `people/` under agent personas, or in `documentation/process/`. |
| 4 | LLM tunnel vision: pattern-matching vs temporal reasoning | `stack/` | Blocked / Understand | Companion to `stack/debugging-regression-first-question.md`. This is the theoretical explanation for why that pattern fails. Extend the existing file, don't create a new one. Already has a root Blocked row. |

**Proposed section(s):** `operations/` for #1-2. `people/` for #3. `stack/` for #4 (extension).

**Proposed lane(s):**
- Do Something: #2 (exponential backoff retry strategy) → new or updated `operations/` file, section-only (root already has circuit breaker covered)
- Understand: #3 (Kurt persona comms) → `people/` section-only, unlikely to warrant a root row
- Blocked: #4 already has root coverage

**Confidence:** MEDIUM — Item 3 (Kurt persona) is borderline between `people/` and `documentation/process/`. The curator notes suggest `people/` or a new `comms/` section. Given the current `people/INDEX.md` exists, `people/` is the path of least resistance. Item 2's conflict with the existing hard circuit breaker rule in CLAUDE.md needs human judgment — the new rule (exponential backoff) would update a CLAUDE.md rule, not just add a Bibliothèque file.

**Notes:** Item 2 has a tension: CLAUDE.md already has a "max 3 retries then declare BLOCKED_EXTERNAL" rule. This entry proposes a more nuanced replacement. This is a CLAUDE.md update, not just a Bibliothèque file. Flagged for human judgment.

---

### Entry 7: `2026-04-21-cross-org-persona-wiring.md`

**Content summary:** 3 nuggets: symlinks not copies for cross-org living documents, four-point CLAUDE.md persona wiring checklist, research prompts as first-class inbox artifacts.

**Nugget breakdown:**

| # | Nugget | Section | Lane | Notes |
|---|--------|---------|------|-------|
| 1 | Cross-org doc sharing uses symlinks, not copies | `operations/` | Do Something | Operational procedure for multi-org setup. New file: `operations/cross-org-doc-sharing.md` or extend an onboarding SOP. |
| 2 | Four-point CLAUDE.md persona wiring checklist | `documentation/process/` | Do Something | Agent discovery process knowledge. This is closer to agent tooling meta than Bibliothèque content. Could go in `documentation/process/bmad-persona-guide.md` or a new `operations/` onboarding file. |
| 3 | Research prompts as first-class inbox artifacts | `documentation/process/` | Do Something | Meta-pattern about agent workflow, not domain/stack knowledge. Route to `documentation/process/` or update the Bibliothèque contributing guide. |

**Proposed section(s):** `operations/` for #1. `documentation/process/` for #2-3 (outside the Bibliothèque proper). Multi-section.

**Proposed lane(s):**
- Do Something: #1 → root row ("Set up cross-org document sharing") if this is a recurring task
- Do Something: #2 → section-only in `documentation/process/`; might also warrant a Do Something row ("Wire up BMAD personas in a new org")
- Understand: #2 also answers "why agents can't find personas" — Blocked row possible ("Agent not loading BMAD personas / personas invisible")

**Confidence:** MEDIUM — Items 2 and 3 are close to the SKILL.md edge case for "meta-knowledge about how agents behave." They might be better as CLAUDE.md updates (global or project-level) than as Bibliothèque files. Human judgment on whether `documentation/process/` or CLAUDE.md is the right home.

**Notes:** The four-point checklist (#2) is operationally load-bearing — Klever had invisible personas for months because of this. It warrants at minimum a `documentation/process/bmad-persona-guide.md` update and potentially a Blocked root row ("Agents not loading BMAD personas despite files existing").

---

## Overall Assessment

### Are the classification rules sufficient?

**Yes, with two areas of friction:**

1. **Meta-knowledge routing is clear in principle but has judgment calls in practice.** SKILL.md correctly routes Bibliothèque meta-patterns to `documentation/process/` or PROPOSALS.md. In practice, several entries in this batch (Entry 5, items from Entry 7) blur the line between "Bibliothèque operational file" and "CLAUDE.md rule." The skill would need to check both destinations and decide which is authoritative. The heuristic is sound ("agent behavior rules → CLAUDE.md, structured reference → Bibliothèque"), but applying it requires reading the existing CLAUDE.md to see if the rule is already there.

2. **Extend-vs-create decisions require reading existing files.** Entries 4 and 6 contain nuggets that should extend `stack/gateway-dual-header-401.md`, `stack/service-to-service-400-content-type.md`, `stack/debugging-regression-first-question.md`, and `operations/cicd-registry-maintenance-window.md`. The classification rules correctly identify this via the "primary-mode" heuristic, but the skill MUST read those target files before writing. This is called out in Step 3B of SKILL.md and confirmed necessary here.

### Ambiguous cases

1. **Entry 6, Item 2 (exponential backoff):** The new rule updates an existing CLAUDE.md circuit breaker rule. The skill should write to `operations/` AND flag the CLAUDE.md update for human approval. The skill as written does not have an explicit protocol for "this inbox item requires a CLAUDE.md change." Flagged.

2. **Entry 7, Items 2-3 (persona wiring, research prompts):** These are agent behavior patterns that could go in CLAUDE.md, `documentation/process/`, or the Bibliothèque. The skill's edge case rules push them to `documentation/process/` or CLAUDE.md, but the skill doesn't have a rule for "check CLAUDE.md first before writing a new file." Flagged.

3. **Entry 4, Item 11 (RetellFilterCriteria epoch ms):** SKILL.md Example 4 explicitly says to check `~/.claude/library/context/retell-api-v2-reference.md` first. The skill correctly calls this out. The library file must be read before deciding whether to create a new Bibliothèque entry or add a cross-reference note. This is correct skill behavior, not a gap.

4. **Entry 1, Item 1 (shared-config hook):** The curator notes call it "tooling/infra." The skill's section table does not have a "tooling" section. The closest destinations are `documentation/process/` (meta-patterns) or a CLAUDE.md update. The skill would need to apply the edge case for "tooling patches already applied."

---

## Grade: PASS

The skill's classification rules correctly route 6 of 7 entries to the right sections without ambiguity. The one partial ambiguity cluster (meta-knowledge entries 5 and 7) is explicitly handled by the Edge Cases section. The extend-vs-create logic is correct and present. The bootstrap hygiene rule is documented and would fire correctly (neither `stack/INDEX.md` nor `operations/INDEX.md` has placeholder text, so no cleanup required for this batch). The three-lane root INDEX rules correctly identify which nuggets deserve root rows vs. section-only entries.

---

## GATED ACTIONS

What the skill would do if approved (files to create/move, INDEX updates):

### New files to create

| File | Content |
|------|---------|
| `operations/gcloud-multi-session-safety.md` | Stateless gcloud account switching + multi-session auth pollution (Entry 1, #2) |
| `operations/destructive-script-safety.md` | Hardcoded fallbacks, backup integrity gate, --yes countdown timer, gitignore for backups (Entry 1, #3-6) |
| `operations/git-large-file-hygiene.md` | Gitignore path mismatch, untracking tracked files, filter-repo --force, remote re-add after filter-repo (Entry 2, all) |
| `operations/pr-merge-audit-pattern.md` | Stale PR detection, adversarial elicitation checklist, cherry-pick detection (Entry 3, #2+4+5) |
| `stack/eqs-filterqueryvalue-coercion.md` | FilterQueryValue scalar pre-coerces before DatastoreQueryAdapter (Entry 3, #1) |
| `operations/dac-branch-model.md` | DAC dev-default, MR-for-promotion, same-day uat risk, branch discovery command (Entry 4 #2-3 + Entry 6 #1) |
| `operations/cicd-pipeline-retry-strategy.md` | Exponential backoff pattern (2→5→15→blocked), contrast with hard circuit breaker (Entry 6, #2) |
| `stack/webclient-bodyvalue-double-serialization.md` | String vs Map/POJO bodyValue double-serialization root cause + fix (Entry 4, #10) |
| `stack/retell-api-timestamp-format.md` | Epoch milliseconds for startTimestamp thresholds (Entry 4, #11) — pending retell-api-v2-reference.md check |
| `stack/gateway-auth-correct-client-pattern.md` | Authorization: Bearer M2M token is the designed pattern; userAuthorization bypasses router rule (Entry 4, #9) |
| `operations/gitlab-skill-push-gap.md` | gitlab_skill BLOCKED_REFS doesn't cover raw `git push` commands (Entry 4, #7) |
| `people/kurt-autonomous-agent-persona.md` | Kurt persona for external comms, first-person accountability framing (Entry 6, #3) |
| `operations/cross-org-doc-sharing.md` | Symlinks not copies for cross-org living documents (Entry 7, #1) |

### Files to extend (not create)

| Existing File | What to add |
|---------------|-------------|
| `stack/gateway-dual-header-401.md` | Apollo Router rename rule detail, correct client pattern cross-reference (Entry 4, #4) |
| `stack/service-to-service-400-content-type.md` | DGS MonoGraphQLClient missing Content-Type detail (Entry 4, #5) |
| `stack/debugging-regression-first-question.md` | LLM tunnel vision theoretical explanation, temporal reasoning gap (Entry 6, #4) |
| `operations/cicd-registry-maintenance-window.md` | Datasophia exact hours (11PM-5AM ET), don't-retry guidance (Entry 4, #1 additive detail) |

### Files to skip (project state or already handled)

| Entry | Reason |
|-------|--------|
| Entry 4, #8 (retell-service not active in prod) | Project state → `tickets/SPV-165/reports/status/`, not Bibliothèque |
| Entry 4, #6 (gitlab pipeline vs pipelines) | Tooling patch already applied to skill SKILL.md. Mark promoted, no Bibliothèque file needed. |
| Entry 5 (all items) | Meta-knowledge → `documentation/process/documentation-standards.md` update + CLAUDE.md single-trigger rule (already in place per current CLAUDE.md). Check before writing. |
| Entry 1, #1 (shared-config hook) | Tooling patch / harness config rule → CLAUDE.md or harness instructions, not Bibliothèque |

### Root INDEX rows to add

**Blocked lane:**
- `operations/gcloud-multi-session-safety.md` — Symptom: "gcloud commands targeting wrong org / auth pollution between sessions"
- `operations/git-large-file-hygiene.md` — Symptom: "Push blocked by large or PII file in git history"
- `stack/webclient-bodyvalue-double-serialization.md` — Symptom: "Service → downstream returns 400, bodyValue(String) double-serializes JSON"
- `operations/dac-branch-model.md` — Symptom: "Commits on DAC dev promoted to uat same day, no cleanup window"

**Do Something lane:**
- `operations/git-large-file-hygiene.md` — Task: "Remove a committed large or PII file from git history"
- `operations/pr-merge-audit-pattern.md` — Task: "Audit a stale or 'looks needed' PR before merging"
- `operations/dac-branch-model.md` — Task: "Deploy to a DAC repo / promote to uat or main"
- `operations/cross-org-doc-sharing.md` — Task: "Share a living document across orgs without drift"

**Understand lane:**
- `stack/eqs-filterqueryvalue-coercion.md` — Question: "How does EQS handle scalar type coercion before DatastoreQueryAdapter?"
- `people/kurt-autonomous-agent-persona.md` — Question: "Who is Kurt and how should autonomous agent work be communicated externally?"
- Entry 3, #3 — Question: "What is the default branch for origin8-web?" (add to existing GLOSSARY or stack section, not a new file)

### INDEX updates required

- `operations/INDEX.md` — Add entries for: gcloud-multi-session-safety.md, destructive-script-safety.md, git-large-file-hygiene.md, pr-merge-audit-pattern.md, dac-branch-model.md, cicd-pipeline-retry-strategy.md, gitlab-skill-push-gap.md, cross-org-doc-sharing.md
- `stack/INDEX.md` — Add entries for: eqs-filterqueryvalue-coercion.md, webclient-bodyvalue-double-serialization.md, gateway-auth-correct-client-pattern.md, retell-api-timestamp-format.md
- `people/INDEX.md` — Add entry for: kurt-autonomous-agent-persona.md
- `bibliotheque/INDEX.md` — Add 8 root INDEX rows (4 Blocked, 3 Do Something, 1 Understand). Update "Last updated" to 2026-04-21.
- `inbox/INDEX.md` — Mark all 7 entries as `promoted` (or `partial` for Entry 5 which routes to process docs, not Bibliothèque sections).

### Needs Human Judgment

1. **Entry 6, Item 2 (exponential backoff):** Replaces the hard circuit breaker rule in CLAUDE.md. The Bibliothèque file can be written, but the CLAUDE.md rule must be updated by a human or with explicit approval. Proposed resolution: write `operations/cicd-pipeline-retry-strategy.md`, flag the CLAUDE.md update in a `### Needs Human Approval` note in the report.

2. **Entry 7, Items 2-3 (persona wiring checklist, research prompts as artifacts):** Both are agent behavior patterns. Proposed resolution: write `documentation/process/bmad-persona-guide.md` update for Item 2, add Item 3 as a note in `documentation/process/` agent workflow docs. Check CLAUDE.md first — the four-point wiring rule may already be present.

3. **Entry 5 status:** If `documentation/process/documentation-standards.md` already contains the three-lane pattern (it is referenced in the root INDEX), this entire entry may resolve to "already promoted, no new content needed." Read the file before deciding. Proposed resolution: classify as `partial` pending that check.
