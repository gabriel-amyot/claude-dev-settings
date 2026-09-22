# Harness Evolution Plan — 2026-07

Author: synthesis architect (Opus) from 4 Sonnet recon reports.
Owner: Gabriel (Klever, solo dev). Scope: `~/.claude/` global harness + Klever project-management.
Rule for executors: this plan is the spec. Each workstream below is a self-contained task card — a fresh Sonnet/Opus session can run it without reading the recon. Do NOT invent scope beyond the card.

---

## VERDICT

### #1 BOTTLENECK — Forced producers have no automated consumer; Gabriel *is* the drain
The harness mechanically forces capture but leaves draining to a human who is overwhelmed.
- `session-close-operationalize-guard.sh` blocks ledger close until capture runs, yet **nothing** drains what capture produces. Skill-proposals backlog: **37 pending, oldest 63 days**; the nudge hook fired and was ignored for **35 days**.
- Handoffs: **42 of 122 (34%) stuck at `awaiting_initiation`**, oldest 5+ weeks. No automation initiates or expires them.
- **37% of all skill calls (113/305)** are meta-process (`gab-operationalize` 72 + `post-comment` 41). Gabriel spends more than a third of his tool budget feeding queues nobody drains.
- **Impact:** the capture machine runs at full speed into queues that only grow. The system generates obligations faster than the one human can retire them.

### #1 WASTE — 137 of 177 skills (77%) never invoked, taxing every session
- **45.9 KB of skill descriptions (34% of the ~133.5 KB / 34,200-token fixed context tax)** load every session; 77% are for skills with **zero invocations in 30 days** (sprint-factory, klever-test, morning-brief/primer, all `bmad-*`, `batch-*`, `claude-reflect:*`).
- Dead machinery still runs: `knowledge-capture/` dir is **empty but still scanned** by operationalize-audit; a PostToolUse hook references `compliance-audit.sh` **that does not exist**.
- **Impact:** ~26 KB of the per-session tax buys nothing. Paid once per session, ~5 sessions/day.

### #1 MISSED OPPORTUNITY — The self-sustaining loop is one scheduled job away
- **Zero cron/scheduled jobs exist**, yet `CronCreate` and the `/loop` primitive are available and the drain logic already exists as skills (`harness-audit`, `operationalize-audit`, `bibliotheque-librarian`).
- The librarian half of the loop **already works** (inbox healthy at 2 pending) *because* `session:check` mechanically curates it — proof the symmetry pattern works when a consumer is wired.
- **Impact:** one weekly steward job that runs the existing audits and drains the queues would convert Gabriel from operator to reviewer. The parts are on the shelf; nothing assembles them.

---

## PARADIGM — "Self-Sustaining Steward"

Gabriel reviews digests. He does not operate the meta-system.

1. **One weekly scheduled steward job** (cron) runs the existing audits, drains every queue (proposals, handoffs, orphan dirs), checks invariants (MEMORY size, hook existence), and writes **one digest** to the inbox. Everything else stops nagging.
2. **Symmetry principle (the core rule):** no forced producer ships without an automated consumer. Capture is forced → the steward drains it. Handoff is written → the steward expires it. If you can't name the automated consumer, don't add the producer.
3. **Subtraction-first:** archive the 137 unused skills out of the *registered* path (`~/.claude/skills-archive/`, restorable, not deleted) to reach ~35–40 active skills a human can hold in their head. Cuts description tax from 45.9 KB toward ~12 KB.
4. **Diet the always-loaded surface:** CLAUDE.md procedural sections → satellite files (progressive disclosure, which it already preaches); skill descriptions → one-line rule; `session:check` keeps only the mechanical capture-gate per-session and folds triage/orphan-prune/reporting into the weekly steward.
5. **Fix the live bugs once, then let the steward hold the line:** repair the handoff read/write path split, the dead `knowledge-capture/` scan, the broken hook, and the MEMORY.md overage as one-time repairs; the steward then keeps steady state.

Net surface change: **removes far more standing obligation than it adds** — one weekly job + a handful of one-time repairs, against 137 archived skills, 2 CLAUDE.md files slimmed, and per-session `session:check` cut from ~35 tool calls to a single gate.

---

## WORKSTREAMS

Sequence: **Week 1** = one-time repairs + archival sweep · **Week 2** = steward job + diet · **Week 3** = validation + tune.

---

### WEEK 1 — One-time repairs + archival

#### WS1 — Fix the handoff read/write path split *(LIVE BUG)*
- **Goal:** `session:handoff` (writes `{slug}/prompts/`) and `session:pickup` (reads legacy flat `sessions/active/prompts/`) read and write the same path. Reconcile the 16/122 dangling ledger entries.
- **Files:** `~/.claude/skills/session/handoff/SKILL.md` (+ scripts), `~/.claude/skills/session/pickup/SKILL.md` (+ scripts); ledger `~/Developer/grp-beklever-com/project-management/sessions/ledger.yaml`; dirs `sessions/active/prompts/` (78 legacy files) and per-slug `sessions/*/prompts/`.
- **Steps:** (1) Decide canonical path — recommend per-slug `{slug}/prompts/` (matches writer, richer). (2) Update `pickup` to read the canonical path; add a one-time back-compat scan of the flat dir. (3) Migrate the 78 flat files into their slug folders (or a `legacy/` slug); update ledger `handoff_file` fields. (4) Reconcile the 16 dangling entries: mark `abandoned` if no file, or repoint if the file moved.
- **Verification:** `session:pickup` lists the same handoffs the ledger shows; zero dangling entries (`for each ledger handoff → file exists`); a fresh handoff written by `session:handoff` is immediately visible to `session:pickup`.
- **Effort:** M · **Model:** opus (path semantics + migration correctness) · **Deps:** none.

#### WS2 — Remove the dead `knowledge-capture/` scan *(LIVE BUG)*
- **Goal:** operationalize-audit Step 1 no longer scans the empty, permanently-dead `knowledge-capture/` dir (gab-operationalize now writes to the bibliothèque inbox).
- **Files:** `~/.claude/skills/operationalize-audit/SKILL.md` (+ any `resources/*.sh` doing the scan); `~/.claude/skills/gab-operationalize/` (confirm current write target).
- **Steps:** (1) Grep both skills for `knowledge-capture`. (2) Confirm gab-operationalize's real output path (bibliothèque inbox). (3) Delete the Step-1 scan or repoint it to the real inbox. (4) Remove/empty the dead dir.
- **Verification:** `grep -r knowledge-capture ~/.claude/skills` returns only historical/comment references; operationalize-audit run produces no no-op scan step.
- **Effort:** S · **Model:** sonnet · **Deps:** none.

#### WS3 — Fix the broken `compliance-audit.sh` hook *(LIVE BUG)*
- **Goal:** no hook references a missing script.
- **Files:** `~/.claude/settings.json` (PostToolUse block); `~/.claude/skills/dark-factory/resources/` (missing `compliance-audit.sh`).
- **Steps:** (1) Locate the PostToolUse entry pointing at `dark-factory/resources/compliance-audit.sh`. (2) Decide: the script was never shipped → **remove the hook entry** (recommended; dark-factory has 0 external need for a global PostToolUse). If it's genuinely wanted, restore the script from git history and make it exit 0 on non-dark-factory contexts. (3) Validate JSON.
- **Verification:** `WS-hookcheck` from WS6 passes; `jq . ~/.claude/settings.json` valid; no PostToolUse path resolves to a nonexistent file.
- **Effort:** S · **Model:** sonnet · **Deps:** none.

#### WS4 — MEMORY.md diet under cap
- **Goal:** `MEMORY.md` ≤ 24.4 KB load cap (currently 28.9 KB — References/Agents tail silently truncated every session).
- **Files:** `~/.claude/projects/-Users-gabrielamyot-Developer-grp-beklever-com-project-management/memory/MEMORY.md` + topic files in that dir.
- **Steps:** (1) Enforce the file's own rule: one line per index entry, ≤~200 chars. Many entries carry a full sentence of detail — move detail into the linked topic file, leave a hook in the index. (2) Consolidate resolved/stale entries (completed projects, closed sprints — e.g. Sprint 1 Q2 CLOSED). (3) Target ~20 index entries per the governance rule. (4) Re-measure.
- **Verification:** `wc -c MEMORY.md` < 24400; no truncation warning on next session; every `[[link]]` resolves.
- **Effort:** M · **Model:** sonnet · **Deps:** none.

#### WS5 — Archival sweep (unused skills, by tier — PROPOSAL then move)
- **Goal:** shrink the registered-skill surface to ~35–40 active, restorable. This is the single biggest tax cut. But the 137 unused skills are NOT one movable pile — they live in three tiers with different removal mechanics, and the 30-day window undercounts seasonal skills. So this workstream produces a **proposal table for Gabriel's one-pass review first, and moves nothing until he approves.**
- **The three tiers (removal mechanic differs per tier):**
  - **(a) Personal skills** under `~/.claude/skills/` — Gabriel owns the files. Removal = `mv` the skill dir to `~/.claude/skills-archive/`. Fully in scope.
  - **(b) Plugin-shipped skills** under `~/.claude/plugins/*` (`superpowers:*`, `bmad-*`, `claude-reflect:*`, `crit:*`, `ralph-loop:*`, `skill-creator`, `frontend-design`, `dataviz`, `agent-browser`, `mapping:*`, `adtech:*`, etc.) — individual skill files are NOT freely movable (plugin-owned, path-locked). Removal mechanic = **disable the whole plugin** via settings, and ONLY when *every* skill that plugin ships is at zero invocations. A partially-used plugin stays entirely (don't fight its internal structure). Output for this tier is a per-plugin verdict, not a per-skill move.
  - **(c) Harness built-ins** (`verify`, `code-review`, `simplify`, `loop`, `claude-api`, `init`, `review`, `security-review`, `run`, etc.) — NOT removable and out of scope. Do not list them.
- **Files:** `~/.claude/skills/*` (tier a source), `~/.claude/skills-archive/` (new, NOT on the registration path), `~/.claude/settings.json` (tier b plugin enable/disable), the 30-day usage data from recon.
- **Steps:**
  1. **Tier every unused skill** into (a) personal, (b) plugin (annotate which plugin), or (c) built-in (exclude).
  2. **For tier (b), roll up by plugin:** a plugin is a disable candidate ONLY if all its shipped skills are zero-invocation in 30 days. Any usage → the whole plugin stays.
  3. **Build the PROPOSAL table** — one row per personal skill and per candidate plugin: `name | tier | last-seen | recommendation (archive / disable / keep)`. Write it to `~/.claude/harness/ws5-archive-proposal.md`. **Move/disable nothing yet.**
  4. **Keep-set = the 41 skills invoked in 30 days ∪ a rare-but-load-bearing allowlist** (see false-dead note) ∪ any skill Gabriel marks keep on review.
  5. **After Gabriel's one-pass approval:** `mv` approved personal skills to the archive; disable approved fully-dead plugins in settings; write `~/.claude/skills-archive/RESTORE.md` (one-line restore per personal skill; per-plugin re-enable line for tier b).
- **False-dead risk (must honor):** the 30-day window undercounts **seasonal / incident-response** skills — sprint-boundary tools (`klever-sprint-exit`, `sprint-close`, `sprint-estimation`), incident tools (`har-diagnostic`, the pr-panic protocol, `deploy-identity`, `dev-status`). These fire rarely but are load-bearing when they fire. Default them to **keep** in the proposal and let Gabriel maintain a short "rare but load-bearing" keep-list. Never auto-archive a skill just because it's cold; the proposal table + human pass is the gate (consistent with the digest-review paradigm).
- **Safety allowlist (rare, keep regardless of 30-day count):** `post-comment`, `klever-mr`, `session:*`, `jira`, `gitlab`, `bibliotheque-librarian`, `harness-audit`, `operationalize-audit`, `deploy-identity`, `create-tickets`, plus the seasonal/incident set above.
- **Verification:** proposal table exists and covers every unused skill tagged by tier; no built-in listed as archivable; no plugin marked disable while any of its skills shows usage; after the approved move, active registered skill count 35–40 and every archived personal skill restorable in one `mv`, every disabled plugin re-enablable in one settings edit; no keep-set or seasonal skill archived.
- **Effort:** L · **Model:** opus (tiering + keep/cut judgement is load-bearing; a wrong cut removes a safety or seasonal skill) · **Deps:** none, but coordinate with WS10 (agents) and WS8 (descriptions). Human approval gate between step 3 and step 5.

#### WS10 — Retire unused purpose-built agents
- **Goal:** remove routing surface for agents that never fire. **Decision: archive the unused ones** (don't try to "make routing cheaper" — the router demonstrably reaches for `general-purpose`+`Explore` at 85%, and adding routing hints is more standing surface, violating subtraction-first).
- **Files:** `~/.claude/agents/*.md`; archive to `~/.claude/agents-archive/`.
- **Steps:** (1) Keep: `general-purpose`, `Explore`, `Plan`, `dexter` (7 uses), plus any agent a kept skill invokes internally (`bibliotheque-librarian`, `post-comment`). (2) Archive zero-invocation agents: `story-quality-gate`, `sprint-crawl`, `night-crawl`, `dev-crawl`, `colleague-review`, `pickup-ticket`, `review-responder`, `pr-response-sweep`, `mother-base-housekeeper`, the Supervisr-specific `supervisr-*` (Klever machine). (3) Note restore path in `agents-archive/RESTORE.md`.
- **Verification:** `ls ~/.claude/agents` shows only the keep-set; no kept skill references an archived agent (`grep -rl <agent> ~/.claude/skills`).
- **Effort:** M · **Model:** sonnet · **Deps:** WS5 (do together — a skill and its agent get archived as a pair).

---

### WEEK 2 — Steward job + diet

#### WS6 — Build the weekly Steward job *(the keystone)*
- **Goal:** one scheduled job that drains every queue and writes ONE digest. This is the automated consumer that makes the whole paradigm work.
- **Files:** new `~/.claude/harness/steward/steward.md` (the prompt/runbook), scheduled via `CronCreate` (weekly, e.g. Mon 06:00 ET); writes digest to the Klever inbox (`general/inboxes/` per current structure — confirm live path).
- **Steps — the steward run does, in order:**
  1. **Audit:** invoke `harness-audit` + `operationalize-audit`; update `.last-audit`.
  2. **Triage skill-proposals:** auto-reject proposals >30 days old OR duplicate of an existing skill (log reason); shortlist ≤5 highest-value for human; everything else stays pending with a reason. Target: pending ≤5 after run.
  3. **Drain handoffs:** any `awaiting_initiation` >14 days → move to a `proposed-abandon` list in the digest (don't auto-delete; Gabriel confirms). Repoint/close danglers.
  4. **Prune orphaned session dirs:** the 6 orphaned folders — archive dirs with no ledger entry and no activity >14 days.
  5. **Invariant checks:** MEMORY.md size vs 24.4 KB cap; every hook `command` path in settings.json exists on disk (`WS-hookcheck`); every registered skill has a valid SKILL.md.
  6. **Write ONE digest** to the inbox: queue sizes before/after, the ≤5 proposal shortlist, proposed-abandon handoffs, any invariant breach. Nothing else nags Gabriel between runs.
- **Verification:** run once manually; confirm digest lands in inbox with all six sections; confirm it is idempotent (second run same week is a near-noop); after run, proposal backlog ≤5 and handoff-pending ≤10.
- **Effort:** L · **Model:** opus (orchestration + safe auto-reject rules) · **Deps:** WS1 (handoff paths), WS2 (dead scan), WS3 (hook check needs clean baseline).

#### WS7 — CLAUDE.md diet (extract procedure to satellites)
- **Goal:** global CLAUDE.md 31.4 KB → ~12 KB; project-management CLAUDE.md 30.2 KB → ~12 KB. Both currently violate their own progressive-disclosure rule.
- **Files:** `~/.claude/CLAUDE.md`; `~/Developer/grp-beklever-com/project-management/CLAUDE.md`; satellites in `~/.claude/library/context/` and `documentation/process/`.
- **Steps:** (1) Global: extract Development Workflow (8.3 KB), On-Demand table detail (3.9), Shipping Safeguards (2.9), Factory Family (2.2), Spec Fidelity (1.3) into named satellite files; leave a one-line rule + On-Demand pointer in CLAUDE.md. (2) Project: extract File Placement (4.0), Klever Dev Workflow (3.2), Browser Testing (2.3 — already duplicated in its own sub-files, so just point to them), Sprint routing (1.8). (3) Keep in CLAUDE.md only: identity, the absolute rules (single-trunk, no-force-push, IAM gate), and the On-Demand trigger table.
- **Verification:** `wc -c` on both files near target; every extracted section has an On-Demand table row so it's still discoverable; no rule lost (diff the section list).
- **Effort:** L · **Model:** opus (must preserve every load-bearing rule while cutting) · **Deps:** none, but read `claude-md-authoring.md` first.

#### WS8 — Skill-description diet (one-line rule) — **personal skills only**
- **Goal:** every kept **personal** skill's `description:` is one line stating trigger + scope; remove the long disambiguation prose (sprint-family especially — `klever-sprint-exit` alone is ~1.5 KB).
- **Scope caveat (same tiering as WS5):** only diet skills whose SKILL.md files **Gabriel owns** — i.e. tier-(a) personal skills under `~/.claude/skills/`. Do NOT edit tier-(b) plugin-shipped descriptions (`superpowers:*`, `bmad-*`, `crit:*`, `dataviz`, etc.) — they're plugin-owned, edits are overwritten on plugin update, and the lever there is enable/disable (WS5), not description edits. Tier-(c) built-ins are untouchable.
- **Files:** `description:` frontmatter of each kept **personal** skill (post-WS5 keep-set, tier (a) only).
- **Steps:** (1) For each kept personal skill, rewrite `description` to ≤~200 chars: what it does + primary trigger + org scope. (2) Move multi-example trigger lists into the SKILL.md body (loaded only on invoke), not the description (loaded always). (3) Resolve the routing that the prose was doing via the On-Demand/floor-manager tables instead.
- **Verification:** re-measure total description tax (target ≤~12 KB combined with WS5); no plugin/built-in description modified (`git`/diff scoped to `~/.claude/skills/`); spot-check that trimmed skills still trigger on their primary phrase.
- **Effort:** M · **Model:** sonnet · **Deps:** WS5 (only diet the keep-set; tier-(a) subset).

#### WS9 — Simplify `session:check` (keep gate, fold the rest into steward)
- **Goal:** cut per-session close from ~35 tool calls / 10 phases to a thin mechanical gate; move triage/orphan-prune/reporting to WS6.
- **Files:** `~/.claude/skills/session/check/SKILL.md` (852 lines); `session-close-operationalize-guard.sh`.
- **Steps:** (1) Keep mechanical per-session: the capture-gate (operationalize) + ledger close + handoff persist. (2) Remove from per-session and hand to the weekly steward: intent-tree archival heuristics beyond a simple write, orphan-dir scanning, retroactive scaffolding, cross-session reporting. (3) Keep the operationalize guard hook (it's the working half of the symmetry — WS6 is now its consumer).
- **Verification:** a session close runs in materially fewer tool calls (count before/after); capture still forced; steward now owns the folded-out duties (cross-check WS6 covers each removed phase).
- **Effort:** M · **Model:** opus (don't drop a phase that has no steward home) · **Deps:** WS6 (steward must exist to receive the folded-out work).

---

### WEEK 3 — Validation + tune

#### WS11 — Validate + tune
- **Goal:** confirm the targets in Measurement are met; tune steward thresholds.
- **Files:** all of the above; `~/.claude/harness/evolution-plan-2026-07.md` (append a results block).
- **Steps:** (1) Re-run the context-tax measurement (skill descriptions + CLAUDE.md + MEMORY). (2) Check queue sizes after one steward cycle. (3) Run `WS-hookcheck`. (4) Tune: if the ≤5 proposal shortlist is too aggressive or the 14-day handoff expiry too short, adjust in `steward.md`. (5) Append actual-vs-target results to this file.
- **Verification:** see Measurement section — all four targets green.
- **Effort:** M · **Model:** opus (judgement on tuning) · **Deps:** WS1–WS10 landed.

---

## MEASUREMENT — how we know it worked

| Metric | Baseline (2026-07) | Target | How to measure |
|---|---|---|---|
| Fixed context tax | ~133.5 KB / 34.2k tok | **≤ ~60 KB** | sum skill descriptions + 2 CLAUDE.md + MEMORY |
| Skill-proposal backlog | 37 (oldest 63 d) | **≤ 5** | count `skill-proposals/` after a steward run |
| Handoffs `awaiting_initiation` | 42 (34%) | **≤ 10** | ledger query |
| Broken hooks | 1 (`compliance-audit.sh`) | **0** | `WS-hookcheck`: every settings.json hook `command` path exists |
| Active registered skills | 177 | **35–40** | `ls ~/.claude/skills` minus archive |
| Meta-process share of skill calls | 37% | **< 15%** | transcript jq (proxy: steward now does the draining) |
| Scheduled steward | 0 jobs | **1 weekly** | `CronList` shows the steward job |

`WS-hookcheck` (reusable snippet for WS3/WS6/WS11): parse `~/.claude/settings.json`, for every hook `command`, resolve the script path and assert it exists and is executable; exit non-zero listing any miss.

---

## GUARDRAILS FOR EXECUTORS
- **Archive, never delete.** WS5/WS10 move to `*-archive/` with a RESTORE.md. Reversible.
- **Auto-reject logs a reason.** WS6 never silently drops a proposal or handoff; the digest lists every action for Gabriel to override.
- **Don't add a producer without its consumer.** Any new capture/queue must name the steward step that drains it, or it doesn't ship.
- **project-management is single-trunk.** No branches/worktrees there (per its CLAUDE.md). Edits to that repo's files (ledger, MEMORY, CLAUDE.md) happen directly on `main`.
- **CLAUDE.md edits preserve every absolute rule** (single-trunk, no-force-push, IAM gate, DAC merge-forward). Diet moves procedure to satellites; it never removes a safety rule.
