# prune-memory — Detailed Check Procedures

Loaded by the bibliotheque-librarian agent in `prune-memory` mode. The agent file holds the contract (checks, severities, mutation boundary); this file holds the how.

## Design rationale (read once, it explains every rule below)

The scarce resource is **MEMORY.md index lines**, not files. Index lines are always-on: the harness auto-loads them every session and they fire passively at the moment of relevance. Wiki SOPs and CLAUDE.md on-demand files are pull-based: they fire only when something routes there. Therefore:

- "The content exists in the wiki" is NEVER sufficient grounds to remove an index line. The question is always: *does an always-on surface still carry the trigger?* Qualifying surfaces: a CLAUDE.md rule (auto-loaded) or a retained MEMORY.md line. A wiki page alone does not qualify.
- `type: feedback` files encode corrections the user already paid for by experiencing the mistake. Deleting one whose rule isn't enforced elsewhere means the agent regresses and repeats the mistake. Feedback files are therefore **immutable to removal**: verdicts allowed are KEEP or MERGE-UP only.
- This mode is garbage collection, not prevention. The harness injects memory-write instructions into every session; inflow will continue. The inflow metric exists so the treadmill is visible; if inflow stays high, the fix is upstream, not more pruning.

## Preflight detail

```bash
git -C {mem-dir} rev-parse HEAD   # must succeed → repo with ≥1 commit
```
On failure: STOP. Report the exact preflight commands the caller must run (tar backup to `~/.claude/backups/memory/{org}/`, `git init`, `git add -A`, baseline commit). Do not offer to run them yourself in headless mode.

Record run-start state before touching anything: `date +%s` (for the mtime sweep), MEMORY.md byte size, index line count, file count.

## Check 1 — Index↔file reconcile (AUTO-FIX)

1. Parse MEMORY.md: every `- [Title](file.md) — hook` line. Build line→file map.
2. Glob `*.md` in the memory dir (exclude MEMORY.md). Build file set.
3. **Phantoms** (line, no file): ERROR. Remove the line. List each removal in the report.
4. **Orphans** (file, no line): WARNING. Generate a line from the file's `description:` frontmatter field (works on both generations), ≤200 chars, format `- [Title](file.md) — hook`, appended to the section matching the file's type (`feedback_`→Feedback, `project_`→Projects, `reference_`→References, `user_`→User). If the file has no parseable description, flag REVIEW instead of inventing one.
5. **Duplicate lines** (two lines → one file): ERROR. Keep the more specific line, drop the other.
6. Exception: do NOT auto-add index lines for orphans that Check 2/3 will propose for removal in the same run; list them as "orphan, removal proposed" instead. Adding-then-removing in one run is churn.

## Check 2 — Duplicate-vs-wiki/CLAUDE.md (PROPOSE)

Per candidate file (default: all files; census hints from the caller only prioritize order, never substitute for evidence):

1. Read the FULL body. Never verdict from the index line, the filename, or a prior census — index/body divergence is a known live failure mode.
2. Extract 2-3 **distinctive identifiers**: ticket keys, file paths, exact rule phrases, numbers. Not generic words.
3. Grep for each identifier in: `{wiki-root}` (recursive), the org project-management `CLAUDE.md`, and `~/.claude/CLAUDE.md`.
4. Verdict:
   - **STRICT-SUBSET** — every distinctive identifier found in a covering doc. Removal *may* be proposed (subject to type rules and the always-on test).
   - **OVERLAP** — some found, some unique. Verdict is MERGE: name exactly what's unique and which doc it should fold into.
   - **UNIQUE** — nothing found. KEEP.
5. Always-on test for any proposed removal: name the surviving surface. If the covering doc is a wiki SOP with no CLAUDE.md routing row, the correct proposal is "add a CLAUDE.md on-demand-table row," not a memory pointer, and the removal is conditional on that row landing.
6. Type rules: `feedback` → KEEP or MERGE-UP only (merge-up = fold unique detail into the covering SOP/CLAUDE.md rule, then reduce the memory file body to a short pointer stub; the file and its index line SURVIVE; the full body remains in git history). `project` / `reference` → any verdict.

## Check 3 — Staleness (`project_` type only)

1. Candidates: `project_*` files with frontmatter/created date (or git-added date) >60 days old.
2. Collect all Jira keys mentioned across candidates; resolve in ONE batched call: `python3 ~/.claude/skills/jira/jira_skill.py search --org {org} --jql "key in (KTP-1,KTP-2,...)" ...` (fields: status). Done/Closed → propose removal.
3. No Jira key and >90 days → REVIEW flag (human decides; never auto-propose removal on age alone).
4. Sprint-status entries: check the sprint's state in `{project-management}/tickets/sprints/INDEX.md`; closed sprint → propose removal.
5. Never verdict `user_` or `feedback_` files under this check.

## Check 4 — Size budget

- MEMORY.md >20,480 B → WARNING. >23,552 B → ERROR (load limit ≈ 24.4 KB; headroom is deliberate).
- On ERROR, the proposal table must include enough removals/trims to reach ≤20 KB (still propose-only; escalate severity in the inbox item).
- Index lines >200 chars → WARNING with a proposed trimmed line (trim the hook, never the link).

## Check 5 — Frontmatter validity (INFO only)

Both generations are valid: legacy flat (`type:` top-level) and new (`metadata:` block with `type:` nested). Parse tolerance is mandatory. Report only files that parse under NEITHER (no `description:` extractable). **Never mass-rewrite frontmatter**: it clobbers mtimes (temporal evidence) for zero recall benefit.

## Inflow metric

Diff against the newest prior `{wiki-root}/reports/memory-prune-*.md` (if any): files present now but not in the prior run's file inventory = inflow; how many of those already have a STRICT-SUBSET/OVERLAP verdict = duplicate inflow rate. Report both numbers. No prior report → state "first run, no baseline."

## Concurrent-write discipline (execution phase)

Other sessions write memories at any time. Rules:
0. Advisory lock: create `{mem-dir}/.prune-lock` (agent name + ISO timestamp) before the first mutation; remove it when done, including on failure. A fresh (<2h) existing lock = another prune is running: STOP and report. A stale (≥2h) lock may be replaced, but say so in the report.
1. Execute in one continuous pass; don't leave hours between approval and execution if avoidable.
2. Re-read MEMORY.md immediately before every write to it; apply changes as minimal edits against the fresh read, never a rewrite from stale in-context state.
3. After execution: find files with mtime > run-start timestamp that you didn't touch → a concurrent session wrote them. Verify their index lines survived your edits; re-add if clobbered.
4. Final `git -C {mem-dir} diff HEAD~1` must contain only approved-manifest changes plus reconciled concurrent writes. Anything else → investigate before committing.

## Quarantine mechanics (interactive, post-approval only)

1. Order: ALL merges complete first (fold unique detail into target SOPs, commit in the project-management repo: `knowledge: fold memory-merge details into SOPs`), THEN removals. No unique detail may be at risk when files start moving.
2. Per approved removal: `mv {file} ~/.claude/backups/memory/{org}/quarantine/{YYYY-MM-DD}/` (create dir), remove its index line (two-file rule), note the restore command in the report (`mv` back + re-add line, or `git -C {mem-dir} revert {sha}`).
3. Inbound-link sweep before each move: `grep -rl "{file-stem}" {mem-dir}` — hits in other memory files → fix or flag those references first.
4. One git commit for the whole batch: `memory: prune ({org} {date}) — N reconciled, N quarantined`.
5. Quarantine is never purged by this mode. Purging is a human act.

## Proposal table format (the human gate)

One table, every index line + every orphan gets a row, sorted: proposed-removals first, then merges, then trims, then keeps (keeps may be collapsed to a count per type with an expandable list). The caller overrides by row number in one response.

```
| # | Index line (truncated) | File | Type | Verdict | Evidence (quoted match + covering path) | Unique detail / surviving always-on surface |
```

## Manifest format

Per non-KEEP file: distinctive identifiers extracted, where each was found (path + section), what remains unique, verdict, confidence, surviving always-on surface. This is the document the human approves; the report summarizes it.
