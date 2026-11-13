# Harness Routing: Factories, Crit, Skill Authoring, File Handling

On-demand context. Moved out of the global CLAUDE.md on 2026-11-13 (session `splitting-lynx`)
so these rules load only when the task needs them. The recall hook surfaces this file through
`ALIASES.md`.

## Autonomous Mode & The Factory Family

Three tools cover ticket-to-dev automation. They are **different modes, not three versions of one thing.** Pick by shape of work.

| Tool | Substrate | Use it for |
|------|-----------|-----------|
| **dark-factory** (`/dark-factory KTP-XXX`) | Workflow-tool script, JS gates (un-skippable), human concierge front gate, tool belts (java/scripting), segregated review + bounded fix loop + QA in worktrees, Retro telemetry. Terminal state `READY_TO_SHIP`; main loop does MR+Jira+validate. | **Single ticket, interactive/gated.** The default for one well-specified ticket where you want a human decision point at the front. (Formerly "dark-factory v2".) |
| **Sprint Factory** (`/sprint-factory`, formerly "dark-factory v1") | Prose orchestration + agent dispatch. Multi-ticket DAG: flat list (auto-dep-checked) or plan-file with YAML dependency graph → topological tiers → parallel dispatch → inter-tier gates → integration tests. Idempotent rerun (reconciles from Jira + ledger). | **Multi-ticket / epic.** When tickets have dependencies and you want tiered parallel execution. Conducts each ticket through `/dark-factory` via handoffs. |
| **sprint-crawl** (`/sprint-crawl KTP-XXX`) | Agent + sprint-harness Bash hooks (phase-gate, stop-guard, context-reinject, audit-trail). Per-AC, resumable across context death. | **Overnight-autonomous, single ticket, per-AC.** When you'll lose the session (sleep, long run) and need hook-enforced resilience. Wrap in ralph-loop for persistence. |

**Triggers** ("go autonomous", "work overnight", "run this ticket", "one-shot this"): for an unattended overnight single ticket → `sprint-crawl` (+ ralph-loop). For an interactive single ticket → `/dark-factory`. For a dependency-linked set → `/sprint-factory`.

**Overnight with ralph-loop:**
```
/ralph-loop:ralph-loop "sprint-crawl KTP-XXX" --completion-promise "ALL_ACS_DONE" --max-iterations 10
```

**When NOT to use any of them:** Spikes, quick bug fixes, research tasks, tickets without clear ACs.

**Legacy agent** night-crawl remains for local validation loops. The other Supervisr agents (dev-crawl, supervisr-autopilot, supervisr-ship and the GitHub review agents) are archived in `~/.claude-shared-config/_archive/agents/`.

## Inline Review with Crit

- **Recommend `/crit:crit` before committing to a plan or a large diff.** When you finish a written plan, or when a diff is large enough that scanning it inline is error-prone (roughly 100+ changed lines or 5+ files), proactively suggest running `/crit:crit` so the human can leave inline comments in the browser and you address them in a loop. Recommend, don't force: a one-line change or a quick answer doesn't need it.
- The crit CLI must be installed (`brew install crit`); the plugin ships only the skill. If `crit` returns `command not found`, surface that and stop rather than guessing an install path.
- **Never open a crit review with an auto-close timer.** Open it and leave the connection open; the user reports back manually when they're done reviewing. An auto-timer closes the review before they're finished.

## Creating New Skills & Agents

Design from the consumer backwards: identify the pipeline gap the thing fills, read the formats it must consume and produce, then build. Update `MEMORY.md` and any skills index with its pipeline position.

**Every new SKILL.md needs a `nav:` block** in its frontmatter (bays: `build`, `fix`, `review`, `ship`, `plan`, `know`, `ops`) with `when:` and `when_not:`. Copy the shape from an existing SKILL.md.

Full procedure: the `write-a-skill` and `skill-creator` skills.

## graphify

- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

## Reading .pptx Files

When asked to read or analyze a `.pptx` file:
1. Unzip it to `/tmp/` using Python's `zipfile` module
2. Slides are stored as images in `ppt/media/` (e.g., `Slide-1-image-1.png`)
3. Read each image using the Read tool to see slide content visually
- Text in `.pptx` slides is often embedded in images, not extractable as text directly
