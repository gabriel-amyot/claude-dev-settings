# Session Plugin v2.0 — Design Decisions

Grill session conducted 2026-05-29. All 15 decisions resolved interactively.

## Decisions

### 1. Uninit'd sessions at close
**Question:** How should close handle sessions that were never initialized via `/session:init`?
**Decision:** Retroactive init. Scaffold folder + ledger entry using intent tree root as the intent field.
**Rationale:** Every closed session needs a consistent archive shape for the future `insights` skill to work without special-casing. The alternative (flat file fallback) would mix intent trees alongside handoff prompt files in `sessions/archive/done/`, creating an undifferentiated dumping ground.

### 2. Init invocation vs logic extraction
**Question:** Should close literally invoke `/session:init`, or extract the scaffold logic?
**Decision:** Document the shared scaffold contract. Each skill implements independently but follows the same rules.
**Rationale:** Avoids the confusing UX of "initializing a session just to close it" and avoids tight coupling between skills.

### 3. Auto-handoff quality
**Question:** How should close handle auto-handoff when context might be degraded?
**Decision:** Use the real `/handoff` skill. No degraded stubs.
**Context:** With Opus 1M, compaction is essentially a non-issue. Context is almost always fresh at close time. The "degraded context" premise from the original plan was wrong for this usage pattern.

### 4. Check/close split
**Question:** Given that close will use real `/handoff` (interactive), is the check/close split still justified?
**Decision:** Merge back into one skill. Check stays unified with `--close` flag.
**Rationale:** When close uses real `/handoff` for OPEN branches, it becomes "check + guaranteed shutdown." The speed distinction collapses. One skill is simpler. See ADR-001.

### 5. Scope of check improvements
**Question:** With check staying unified, which improvements from the plan are kept?
**Decision:** All four: intent tree persistence, neutral triage bias, retroactive init on close, report-back composition.

### 6. Insights skill depth
**Question:** How much should we invest in the insights skill right now?
**Decision:** Stub + schema contract only. Ship when intent trees accumulate (target: 10+ trees).
**Rationale:** Zero intent trees exist today. Pattern detection on 2-3 trees produces noise. The implementation is straightforward once data exists.

### 7. Auto-init hook location
**Question:** Where should the SessionStart hook live?
**Decision:** Plugin-level hook in `hooks/hooks.json`. Not global `settings.json`.
**Context:** SessionStart is a fully supported plugin hook event (documented in Claude Code's hook-development skill). Plugin hooks support the same lifecycle events as user settings hooks. The hook must be a command hook (not prompt), as SessionStart doesn't support prompt hooks. See ADR-002.

### 8. Pickup default filter
**Question:** How should pickup's default list filter work?
**Decision:** Default shows only `awaiting_initiation` forward handoffs. `--all` shows everything. The `--awaiting` flag from the plan is redundant (awaiting IS the default).

### 9. Pickup grouping
**Question:** How should pickup group related handoffs?
**Decision:** Theme field in ledger entries. Pickup groups by theme on the fly.
**Context:** The ledger accumulates clusters of related handoffs (e.g., 5 dark-factory improvements, 3 KTP-679 handoffs). A flat list obscures these groupings.

### 10. Theme field location
**Question:** Should theme appear in both ledger and handoff file, or just one?
**Decision:** Ledger only. Keeps file format lean.
**Tradeoff:** If the ledger is ever rebuilt from files, theme is lost. Acceptable because the ledger is the operational source of truth and file-based rebuilds don't happen. See ADR-003.

### 11. Intent tree schema location
**Question:** Where should the intent-tree.md schema contract live?
**Decision:** `sessions/schema.yaml`, new `intent_tree_format` section. Producer (check) and consumer (insights) both reference it.

### 12. Theme derivation in handoff
**Question:** How should the handoff skill determine the theme?
**Decision:** Derive with fallback. Auto-derive from ticket epic or session context keywords. Ask only when derivation fails (~30% of cases).
**Note:** Ticket field is populated 86% of the time (37/43 entries). The problem is KTP-680 is a catch-all used for 17 different handoffs, making ticket alone insufficient for thematic grouping. Theme provides the second dimension.

### 13. Hook message verbosity
**Question:** How verbose should the SessionStart hook message be?
**Decision:** One-liner nudge. Count + stale count + skill suggestion. Example: `SESSION: 12 handoff(s) awaiting (3 stale). Run /session:init or /session:pickup.`

### 14. Triage bias fix
**Question:** How should we fix check's bias toward recommending CLOSE?
**Decision:** Hard rule. If OPEN node count > 0 after Phase 1b resolution, never recommend CLOSE as the primary option. User can still select it via the AskUserQuestion menu.
**Rationale:** The original plan proposed making check advisory-only to remove the incentive. Since we merged check/close back, the alternative is a hard constraint in Phase 1e triage.

### 15. Report-back in shutdown
**Question:** Should report-back be automatic during shutdown for handoff-origin sessions?
**Decision:** Automatic. If the session originated from a handoff, always invoke `/report-back` during shutdown. No confirmation needed. The contract demands it.
