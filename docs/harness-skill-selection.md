# Shared skill selection

Live view: [Harness observatory](../harness/view/index.html). [Operations and schema](../harness/INDEX.md).

Source: Gabriel's selection on 2026-10-26. These preferences apply to Claude and Codex.
Usage is self-reported, not inferred from invocation counts. An unused skill is a review candidate, not permission to delete it.

## Priorities

| Priority | Area | Decision |
|---|---|---|
| 1 | Session continuity, knowledge library and durable memory | Highest priority. Include plugin session skills, not just the shared skills directory. Keep knowledge in the shared library and org bibliothèque. |
| 2 | Review and documentation | Keep tech-doc-review-flow, push-adr, pr-review, index-context and bmad-debrief. Promote agent-os documentation use, although Gabriel currently uses it little. |
| 2 | Tickets and specifications | Keep the whole group. Explain each skill's purpose when selecting a workflow. |
| 2 | Feedback and investigation | feedback-to-spec is very important. Keep investigate. |
| Strategic | dark-factory and its ecosystem | Bread and butter, with substantial future investment intended. Preserve its deterministic gates during Codex portability work. Sprint estimation and sprint close are important. |
| Review | adversarial-cascade | Gabriel reports not using it in either Claude or Codex. Review its role before promoting or linking it. |
| Review | crawl-adversarial-review-cascade | Gabriel reports not using it in either agent. Review its role and overlap before promoting or linking it. |
| Dormant | ralph-loop-preflight | Gabriel has not used it for a long time. Review later; do not prioritize a port. |

## Sessions missing from the original catalog

The local session plugin contains init, check, handoff, pickup, report-back, insights and autopilot.
Its live directory and the shared backup were independent copies. The live plugin was moved without copying to ~/.claude-shared-config/plugins/session, and Claude's original plugin path now symlinks there. Codex links point to this same live source. The old backup is not exposed.
Session identity belongs to the current conversation. Never adopt another session because it is the newest active folder.
Every ledger mutation uses the existing locking helper. Sharing skills does not install Claude lifecycle hooks in Codex.

## Ticket and specification skills

| Skill | Purpose | Maintenance attention |
|---|---|---|
| archive | Preserve finished ticket artifacts and promote durable decisions | Old promotion/location rules need reconciliation with repo-specific agent-os ownership. |
| create-tickets | Create related Jira work with structured ACs | Repair frontmatter and use current ticket paths. |
| epic-reorganization | Split epics and re-parent work | Confirm tracker operations and current local paths before changes. |
| leo-ac-scaffold | Draft missing acceptance criteria | Load the actual persona and respect AC-LOCAL overrides. |
| status-index | Summarize completion in snapshots | A deployed tag alone is not AC evidence. Honor AC-LOCAL.md. |
| ticket-init | Create the ticket folder and tracking scaffold | Correct the hardcoded Jira-domain example. |
| ticket-to-pr-analyst | Investigate a ticket before design and implementation | Update old missing-epic paths and honor AC-LOCAL.md. |
| to-issues | Break a plan into vertical implementation issues | Use the configured tracker and labels. |
| to-prd | Convert agreed context into a PRD | Use the configured tracker and agreed publication scope. |
| triage | Classify incoming work and its readiness | Use existing tracker states and labels. |
| setup-matt-pocock-skills | Configure tracker and domain-document conventions | One-time setup; preserve existing conventions. |
| spillover-scan | Collect accepted findings and deferred test gaps | Resolve current ticket paths and deduplicate before posting. |

## Shared-source rollout

Link curated skill folders into ~/.agents/skills. Preserve Codex system skills and project skills.
Do not expose archive trees, test fixtures or stale plugin backups.
Use existing shared agent instructions through the host's available delegation tools. Do not copy agents into parallel Codex implementations.
Claude-specific hooks, plugins and the Workflow orchestrator are separate dependencies. Discovery is not evidence of executable compatibility.

## Portability work to preserve

1. Sessions: map question/task tools, preserve current-conversation identity, fix stale handoff paths and claim ordering, then validate discovery and ledger reads.
2. Knowledge: make the librarian's existing agent instructions accessible through native host delegation. Keep durable knowledge shared; label Claude-only transcript and auto-memory maintenance honestly.
3. Reviews: map push-adr and pr-review to available delegation. Keep tech-doc-review-flow on its proven orchestrator until an equivalent executor is verified.
4. Factory: inspect dark-factory.workflow.js and its gate tests. An adapter must preserve concierge approval, proven RED, bounded review/fix rounds, independent QA, READY_TO_SHIP, resume behavior and telemetry. Do not replace these with prose or claim a port from a symlink.

## Verification and installed links

First rollout: 33 curated skill-folder symlinks. Exact targets and discovered names are in [codex-linked-skills.json](codex-linked-skills.json).

| Group | Linked skills |
|---|---|
| Sessions (7) | session:init, session:check, session:handoff, session:pickup, session:report-back, session:insights, session:autopilot |
| Knowledge (7) | bibliotheque-librarian, bibliotheque-refresh, operationalize, vendor-api-ingest, notion, transcript-knowledge-miner, wiki-lint |
| Review/docs (4) | pr-review, push-adr, index-context, bmad-debrief |
| Tickets/specifications (9) | create-tickets, ticket-init, leo-ac-scaffold, ticket-to-pr-analyst, to-issues, to-prd, triage, setup-matt-pocock-skills, spillover-scan |
| Planning/investigation (4) | feedback-to-spec, investigate, sprint-estimation, sprint-close |
| Companion workflows (2) | jira, post-comment |
| Architecture (1) | architect-lens (added 2026-11-12, GH-680) |

The former broken ~/.agents/skills link was preserved at ~/.agents/skills.broken-link-2026-10-26. A real skills directory now contains only the curated folder links. Codex system and project skills were preserved.

Actual Codex app-server skills/list with forceReload discovered all 33 with zero errors. Frontmatter and reference targets passed validation. The creator's stricter template checker rejects existing Claude-only metadata on 23 entries; these keys were retained because real Codex discovery accepts them and Claude still uses them.

Read-only independent tests succeeded for session pickup/list and a librarian query. No handoff claim, session write/close, external post, factory run or deployment was performed. Ledger validation remained structurally OK with five existing advisories. Other sessions were active; installation issued no ledger mutation.

Usage notes were added to 37 shared skill entrypoints. Nine previously malformed description scalars were quoted. The initial discovery test caught notes accidentally inserted inside to-prd frontmatter; that edit was corrected before the passing discovery run.

## Cleanup and port backlog

| Priority | Work | Reason |
|---|---|---|
| Strategic | dark-factory runtime adapter | Its script uses injected args, schema-constrained agent calls, labels/phases, isolated worktrees and resume/cache behavior. This host has no Workflow tool. Reuse the same contracts, tool belts and gate functions. Verify against existing review-gate, tdd-gate, design-qa-gates, visual-readiness and ticket-source tests before any live pilot. |
| High | tech-doc-review-flow runtime adapter | Preserve its independent reviewer, mechanical no-code-change checks, cache and bounded rounds. |
| High | agent-os:audit-docs | Retained for promotion. Reconcile missing indexing companions, report paths and audit policy before exposing it. |
| High | archive, status-index, epic-reorganization | Keep the whole ticket group. Repair architecture ownership, evidence/spec semantics and remaining tracker/path assumptions before linking these three. |
| High | context-audit, graphify, operationalize-audit | Knowledge remains top priority. Correct scope/thresholds, graph build delegation/metrics and automatic proposal deletion/build behavior respectively. |
| Review | adversarial-cascade and crawl-adversarial-review-cascade | User reports neither is used in either agent. Assess overlap and value, with no retirement assumed. |
| Later | ralph-loop-preflight | User reports long-term non-use. |
| Maintenance | bibliotheque-refresh and wiki-lint | Refresh uses file-size change detection; librarian/standalone lint coverage differs. Assess consolidation without losing checks. |

Claude recall and lifecycle hooks do not become Codex hooks from these links. Notion refresh still uses the installed Claude executor. Transcript mining is explicitly Claude history. Autopilot run stops before mutations when Workflow is absent; insights retains its documented stub status.

## Tracking coverage and recent friction

The existing root SKILL_CATALOG.md is an intent-based skill/agent guide, not a complete live registry.
The existing skill_usage_scan.py counts Claude transcript text matches. It does not inventory local-plugin skills in installed_skills(), read Codex sessions, attribute runs to roles, or distinguish genuine execution from quoted tool payloads. Its window filters transcript file modification dates rather than individual event dates. Treat USAGE-SCAN.md and RETIREMENT-CANDIDATES.md as historical, incomplete evidence, not current usage truth.
The eval manifest and dark-factory run telemetry provide useful but separate quality/outcome evidence. They do not form a harness-wide friction log.

### 2026-10-26: Installed Claude plugin cache was a separate source

Discovery: inspecting installed_plugins.json during the tracking audit showed session@local registered at ~/.claude/plugins/cache/local/session/2.0.0. That was a real directory, independent of the marketplace path checked during the first rollout. The first rollout therefore proved Codex discovery and marketplace sharing, not Claude runtime sharing. This corrects that earlier overstatement.

Resolution: preserved the old cache as 2.0.0.before-shared-link-2026-10-26 and linked the registered cache path to ~/.claude-shared-config/plugins/session. The registry and plugin metadata were not rewritten. Both registered cache and marketplace paths now resolve to the same shared source as Codex. A same-file check verified the session check entrypoint. Already loaded conversations can retain their loaded instructions; validate a new Claude conversation before claiming behavioral parity.

Prevention: verify the registered runtime installPath as well as the marketplace path before claiming cross-host sharing. This was already documented in library/context/harness-self-management.md, under local plugin cache synchronization.

### 2026-10-26: Consolidated view installed

Gabriel approved SQLite, distinct typed data domains, producer bridges preserving original reports, and a static HTML/CSS view. The implementation is installed under harness/. Existing usage/reference/tax scanners, eval sweeps, factory telemetry and crawl scorecards now publish through the shared helper. The three standalone maintenance scanner files were preserved and symlinked to their shared sources.

Forty-nine tests passed in the installed source. The view indexes original eval definitions/artifacts separately from measured results. Historical activity coverage remains partial and is displayed explicitly. Agents can append friction and proposed decisions through validated operations; maintainer decisions and eval results have separate supported writers. The database and generated HTML are local operational data, with consistent backups and no web framework or server.

