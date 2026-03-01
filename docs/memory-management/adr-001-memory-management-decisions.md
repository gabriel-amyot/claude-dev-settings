# ADR-001: Memory Management Architecture Decisions

**Date:** 2026-02-27
**Status:** Accepted
**Context:** Session spanning Feb 24-27 analyzing memory management research, current setup gaps, and optimal architecture for multi-org Claude Code usage.

---

## Decision 1: Disable Claude Code Platform Auto-Memory

**Choice:** Set `autoMemoryEnabled: false` in global `settings.json`.

**Rationale:**
- Platform memory (`~/.claude/projects/*/memory/MEMORY.md`) is a black box — writes unpredictably, loads only first 200 lines, scoped to launch directory.
- User primarily works from `project-management/` folder, not individual service repos. Only one MEMORY.md (lead-lifecycle-service) had content, and that knowledge already existed at higher durability in the service's CLAUDE.md and agent-os specs.
- Hand-crafted context engineering (CLAUDE.md hierarchy, on-demand context files, skills, agents) provides more predictable, controllable, and targeted context than auto-memory.
- Can re-enable later if Claude Code improves memory management (e.g., agent-scoped memory, semantic retrieval, scope-switching for spawned agents).

**Rejected alternatives:**
- Symlink memory dirs to shared-config for git tracking — overhead for mostly empty dirs, solving a problem that goes away by disabling the feature.
- Keep auto-memory as "spice" alongside engineered context — adds unpredictability for marginal benefit.

---

## Decision 2: Context Consolidation Strategy — Consolidate Down, Not Up

**Choice:** Keep project-management CLAUDE.md lean (index + pointers). Push detailed context *down* to service repos. Orchestrator agents inject targeted context into spawned agents.

**Rationale:**
- User works at project-management level for orchestration; developers/writers work at service level.
- Loading PM-level orchestration context (ticket formats, folder structure, pipeline config) into a developer agent working on a specific service is wasted context window.
- Each service repo has its own CLAUDE.md and agent-os specs — that's where service-specific knowledge belongs.
- Spawned agents inherit parent's CLAUDE.md and project scope (Claude Code limitation) — can't avoid some overhead, but keeping PM CLAUDE.md lean minimizes it.

**Current platform limitation:** Spawned agents cannot get a different project scope. `cd` before spawn does not work — tested and confirmed. Agents inherit parent's working directory and scope.

**Workaround:** Orchestrator includes target service path in agent's Task prompt. Agent reads service CLAUDE.md as first action. Token cost (~2K tokens for a typical CLAUDE.md) is negligible.

---

## Decision 3: New Skills and Tool Extensions Created

### `/tribal-knowledge` skill (Proposal F)
- Structured 9-layer knowledge retrieval with provenance and durability ratings.
- Searches ADRs > contracts > agent-os specs > context files > ticket artifacts > source code > SpecStory.
- Reports durability level and suggests promotion for low-durability finds.
- File: `skills/tribal-knowledge/SKILL.md`

### `gab-operationalize --memory` extension (Proposal E)
- Extends the operationalize skill with memory-extraction mode: fact-mining, NEW/MUTATE/SKIP diffing, date-tagged entries, promote-check flow.
- **2026-02-28:** Retargeted from platform MEMORY.md (disabled via Decision 1) to filesystem-based destinations. Phase 2 now asks the user where to write (in-repo docs, shared-config, or custom path) instead of hardcoding platform memory paths.
- File: `skills/gab-operationalize/SKILL.md`

### `mb-doc-housekeeping` memory enforcement (Proposals A+C)
- `memory-caps`: warns >150 lines, fails >200 lines.
- `memory-dates`: checks temporal grounding, flags stale (>90 days) and undated entries.
- Integrated into `mother-base-housekeeper` agent as Mode 3.
- Note: With auto-memory disabled, these checks apply to any in-repo `memory.md` files if we adopt that pattern. Paths may need updating.
- Files: `skills/mb-doc-housekeeping/SKILL.md`, `agents/mother-base-housekeeper.md`

### `workspace-map.yaml` dependencies (Proposal D)
- Added `dependencies:` section per org with `depends_on` and `memory` fields.
- Mostly TODO placeholders — only origin8 → supervisr_ai dependency confirmed.
- File: `context/workspace-map.yaml`

---

## Decision 4: Deferred Items

| Item | Reason | Revisit When |
|------|--------|-------------|
| Git hooks for session teardown (Proposal B) | Requires careful design; existing on-exit.sh is for a different system | After validating manual `/operationalize --memory` workflow |
| MEMORY.md index-only refactor (Proposal A structure) | Depends on whether we adopt in-repo memory.md pattern | After using `/tribal-knowledge` in practice |
| Cross-project relationship index | workspace-map.yaml has placeholder deps | When service dependency info is confirmed |
| Surprise-driven L3 promotion | High monitoring overhead | Future — aspirational only |

---

## Decision 5: Sycophancy Mitigation

**Choice:** Add explicit anti-sycophancy instruction to global CLAUDE.md.

**Rationale:** Observed pattern of reflexive agreement when challenged, leading to loss of trust in Claude's positions. Instruction should require Claude to hold positions when believed correct and state what specific new information changed its mind (not just that the user pushed back).

**Status:** TODO — to be added to CLAUDE.md.

---

## Key Insight: Platform Memory Scope vs. User Workflow Mismatch

The fundamental problem: Claude Code's memory system is scoped to the directory you launch from. User launches from `project-management/` for 90% of work. Service-level memories only load when launching from service repos (rare). This makes per-service platform memory largely useless for this user's workflow.

The fix is not to make platform memory smarter (not in our control) — it's to disable it and rely on the hand-crafted context system that already exists and works.
