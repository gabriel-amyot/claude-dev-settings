---
name: dark-factory
version: "1.7.0"
description: "Sprint Factory (multi-ticket conductor; formerly 'dark-factory v1'). Takes a set of Jira tickets with dependencies (flat list auto-dep-checked, or plan-file with a YAML dependency graph), computes topological tiers, and drives each ticket to dev. Role is being reframed: the per-ticket lifecycle now belongs to dark-factory-v2; Sprint Factory orchestrates the multi-ticket DAG and (target model) conducts each ticket THROUGH v2 via handoffs. Idempotent + rerunnable: reconciles from Jira ticket status + the handoff ledger, so a rerun skips in-progress handoffs and unlocks children of closed tickets. For a single ticket, use /dark-factory-v2. Klever-first. Triggers on: '/dark-factory', 'sprint factory', 'multi-ticket', 'epic to dev', 'dependency graph'."
user_invocable: true
nav:
  bay: build
  when: "Multi-ticket / epic with dependencies: tiered parallel orchestration via a YAML dependency graph. Conducts tickets through dark-factory-v2. Idempotent rerun per sprint."
  when_not: "Single ticket (use /dark-factory-v2). Overnight per-AC autonomous (use sprint-crawl). Quick ship (use /autonomous-ticket-ship)."
  personas: [amelia, quinn, winston]
  org: [klever]
---

> **⚠ Reframe in progress (2026-06-03).** This skill is becoming **Sprint Factory** — the multi-ticket
> *conductor*, not a per-ticket lifecycle engine. The single-ticket 8-phase lifecycle now lives in
> **dark-factory-v2**. Target model: Sprint Factory computes the dependency DAG, fans out one handoff per
> startable ticket (each runs through `/dark-factory-v2`), and unlocks the next tier on report-back. It
> is **idempotent and rerunnable** — on rerun it reconciles from Jira ticket status + the handoff ledger
> (skip in-progress handoffs, unlock children of closed tickets), so you run it once per sprint and can
> safely re-run if the session closes. The 8-phase prose below is **legacy reference** until the
> orchestration rewrite lands. Design + build order:
> [`docs/sprint-factory-orchestration-model.md`](docs/sprint-factory-orchestration-model.md). The hard
> rename (skill id + dir) and the Mode-1 orchestration rewrite are a scoped follow-up.

# Dark Factory  →  Sprint Factory (multi-ticket conductor)

Full autonomous pipeline: Jira ticket through deployed and verified on dev. 8 phases per ticket, tiered parallelism for multi-ticket runs, YAML dependency graphs, gate verification between tiers.

**Klever-first.** Supervisr repos (GitHub via `gh pr create`) are stubbed but not battle-tested. Will refine when used for Supervisr.

**Version:** See `version` in frontmatter. Changelog: `~/.claude/skills/dark-factory/CHANGELOG.md`. Every SKILL.md modification must bump the version and add a changelog entry.

**Behavioral rule: analysis over advocacy.** The agent that builds the code is the same agent that reviews it. This creates ownership bias. When evaluating risks, safety, or merge readiness: reason about what breaks if assumptions are wrong, not about why the code is probably fine. When findings recur across phases, that's convergence (escalate), not confirmation (carry forward). See Phase 5b.

## Invocation

```
/dark-factory KTP-499                                       # Single ticket
/dark-factory KTP-499 KTP-500 KTP-501                       # Flat list (dep-checked)
/dark-factory --plan path/to/execution-pipeline.md          # Plan file with YAML dependency graph
/dark-factory --resume                                      # Resume from pipeline-state.yaml
/dark-factory --retrospective                               # Cross-run pattern detection + LESSONS.md update
/dark-factory --help                                        # Show modes, flags, and examples
```

### Help

When invoked with `--help`, display the following and exit. No pipeline execution, no file reads beyond the skill itself.

```
Dark Factory v1.0 — Ticket-to-dev pipeline

MODES
  /dark-factory <TICKET>                    Single ticket through 8 phases (analyze → validate)
  /dark-factory <T1> <T2> <T3>             Flat list. Auto-checks Jira for dependency links,
                                            builds tiers if found, warns before running.
  /dark-factory --plan <file>               Plan-file mode. Reads YAML frontmatter for dependency
                                            graph, computes tiers, runs tickets with gate checks.
  /dark-factory --resume                    Resume from nearest pipeline-state.yaml. Picks up
                                            each ticket at its last phase and AC.
  /dark-factory --retrospective             Standalone self-improvement. Reads all runs/*.yaml,
                                            aggregates snag patterns, updates LESSONS.md.
  /dark-factory --help                      This message.

FLAGS (combinable with modes above)
  --dry-run          Parse and display tiers only. No Jira, no artifacts, no agents.
  --analyze-only     Run Phase 1 (Analyze) for all tickets, write state, stop.
  --single-session   No sub-agents. Sequential execution in current session.
  --concurrency N    Max parallel sub-agents per tier (default: all).

PHASES (per ticket)
  1. ANALYZE     Spec quality gate + AC extraction (delegates to /ticket-to-pr-analyst)
  2. DESIGN      Tactical impl plan: files, functions, tests per AC
  3. GRILL       Interrogate the impl plan, surface gaps (delegates to /grill-with-docs)
  4. IMPLEMENT   Code in worktree, one commit per AC, tech-adapted compile+test
  5. REVIEW      External adversarial agent (fresh Agent, diff + ACs only, no impl context)
  6. QA          Per-AC evidence collection: code refs, test refs, verdicts
  7. SHIP        Version bump, MR, Jira comment, transition (delegates to /klever-mr)
  8. VALIDATE    Post-merge dev verification. Human gate for frontend.
  9. RETRO       Auto: writes telemetry to runs/, updates LESSONS.md

EXAMPLES
  /dark-factory KTP-499                                  # Ship one ticket end-to-end
  /dark-factory --plan ~/tickets/KTP-667/pipeline.md     # 8-ticket epic with tiers
  /dark-factory --plan pipeline.md --dry-run             # Preview tiers without executing
  /dark-factory KTP-682 --analyze-only                   # Just run the analyst
  /dark-factory --resume                                 # Continue after pause or crash
  /dark-factory --retrospective                          # Post-run self-improvement

TELEMETRY
  Run data:    ~/.claude/skills/dark-factory/runs/*.yaml
  Lessons:     ~/.claude/skills/dark-factory/LESSONS.md
  State:       <ticket-folder>/pipeline-state.yaml

Klever-first. Supervisr repos stubbed (gh pr create) but not battle-tested.
```

### Flags

| Flag | Default | Effect |
|------|---------|--------|
| `--dry-run` | off | Parse plan, display tiers and ticket assignments, exit. No Jira, no analyst, no artifacts. |
| `--analyze-only` | off | Run Phase 1 (Analyze) for all tickets, write state file, stop. |
| `--resume` | off | Find nearest `pipeline-state.yaml`, resume from current state per ticket. |
| `--single-session` | off | No sub-agents. Run tickets sequentially in current session. For small lists (2-3 tickets). |
| `--concurrency N` | all | Max parallel sub-agents per tier. Default: all tickets in the tier. |
| `--retrospective` | off | Standalone retrospective. Reads all `runs/*.yaml`, detects cross-run patterns, updates LESSONS.md. No pipeline execution. |

---

## Input Mode Resolution

### Single Ticket

One ticket key. Orchestrator runs all 8 phases directly (no sub-agent dispatch unless `--single-session` is off and parallelism adds value).

### Flat List (dep-checked)

Multiple ticket keys without `--plan`. Before execution:

1. Query Jira for `blocks/is-blocked-by` links between the provided tickets:
   ```bash
   cd ~/.claude/skills/jira && python3 jira_skill.py get <TICKET-KEY> --full --org <ORG>
   ```
   Check `issuelinks` for type `Blocks` where the linked issue is in the provided list.

2. If dependencies found: auto-build tier structure, warn user:
   ```
   Detected dependencies: KTP-500 blocks KTP-501.
   Running as 2 tiers instead of flat. Use --force-flat to override.
   ```

3. If no dependencies: run all tickets in a single tier.

### Plan-File Mode

Reads a markdown file with YAML frontmatter containing the dependency graph. The YAML is the source of truth. Mermaid diagrams are decorative (for human visualization only).

If the plan file has no YAML frontmatter but has a Mermaid graph, warn:
```
No YAML dependency graph found. Add a `tickets:` section with `depends_on` fields.
Mermaid graphs are for humans, not machines.
```

#### Plan File Schema (minimum)

```yaml
---
type: execution-plan
tickets:
  - key: KTP-676
    repo: scripts/local
    depends_on: []
  - key: KTP-679
    repo: dataform
    depends_on: []
  - key: KTP-680
    repo: dataform
    depends_on: [KTP-679]
  - key: KTP-683
    repo: app-front-portal
    depends_on: [KTP-676, KTP-682]
    optional: false
  - key: KTP-685
    repo: app-front-portal
    depends_on: [KTP-683]
    optional: true
gates:
  - between: [tier_1, tier_2]
    custom_checks: []
  - between: [tier_2, tier_3]
    custom_checks:
      - name: "Mapbox tilesets accessible"
        command: "curl -s https://api.mapbox.com/v4/{tileset_id}.json?access_token=$MAPBOX_TOKEN | jq .name"
        pass_condition: "non-empty response"
integration_tests:
  - repo: app-front-portal
    command: "npx playwright test tests/canada-map/"
  - repo: app-proximity-report
    command: "mvn test -pl proximity-report-service -Dtest=CanadaIntegrationTest"
---
```

**Required fields:** `type: execution-plan`, `tickets` (array with `key`, `depends_on`).
**Optional fields:** `repo` (per ticket), `optional` (skip without failing pipeline), `gates` (custom verification commands), `integration_tests` (post-all-tiers suite).

### Resume Mode

On `--resume`:
1. Find nearest `pipeline-state.yaml` (check current ticket folder, then parent directories).
2. Read it. For each ticket with status != `complete` and status != `stuck`:
   - Read its `phase` and `ac_progress`
   - Dispatch sub-agent with instructions to resume from that phase
   - Sub-agent checks `ac_progress` and skips ACs already marked `done`
3. For tickets marked `blocked`: re-check if their blockers are now `complete`. If so, unblock and dispatch.

---

## Org Resolution

Parse the project prefix from the first ticket key. Map to org:

| Prefix | Org | Jira `--org` | PM Root |
|--------|-----|--------------|---------|
| KTP, INS | klever | klever | `~/Developer/grp-beklever-com/project-management` |
| SPV | supervisrai | supervisrai | `~/Developer/supervisr-ai/project-management` |
| PER | personal | n/a | `~/Developer/gabriel-amyot/project-management` |

Unknown prefix: read `~/.claude/library/context/workspace-map.yaml` and ask the user.

**Ticket folder:** `<PM_ROOT>/tickets/<PREFIX>/<TICKET-KEY>/`

---

## Pre-Execution Estimate

Before starting (unless `--dry-run`), display:

```
Dark Factory — execution plan
  Mode: {single | list | plan}
  Tickets: {N} ({M} tiers)
  Tiers: [{tier_1_count}] -> [{tier_2_count}] -> ...
  Sub-agents to spawn: {N} (max {concurrency} concurrent per tier)
  Phases per ticket: 8
  Estimated skill invocations: ~{N*3} ({N}x analyst + {N}x grill-with-docs + {N}x klever-mr). Agent dispatches: ~{N*2} ({N}x review + {N}x QA).
  Proceed? [y/n]
```

Wait for user confirmation before proceeding. Circuit breaker: if any single ticket exceeds 3 hours wall-clock, mark it stuck and move on.

---

## Per-Ticket Lifecycle: 8 Phases

### Phase 1: ANALYZE

**Purpose:** Structured spec analysis. Produces machine-readable AC, repo, and assumption artifacts.

**Dispatch:** Sub-agent via Agent tool (not Skill invocation). Each analyst runs in its own context window to avoid loading the 300-line analyst SKILL.md into the orchestrator N times.

**Sub-agent prompt template:**
```
You are running Phase 1 (ANALYZE) of the Dark Factory pipeline for ticket {TICKET_KEY}.

Read the skill file at ~/.claude/skills/ticket-to-pr-analyst/SKILL.md and execute it
for ticket {TICKET_KEY}. Follow the skill's process exactly.

Write outputs to: {TICKET_FOLDER}/analyst/
Version: {next_version}

When complete, report:
- spec_quality: PASS or FAIL
- ac_count: number of ACs produced
- repo_count: number of affected repos
- assumption_count: number of assumptions
```

**Produces:** `analyst/acceptance_criteria.vN.json`, `analyst/affected_repos.vN.json`, `analyst/assumptions.vN.json`

**Gate:** Read `analyst/acceptance_criteria.vN.json`. If `spec_quality == "FAIL"`:
- Mark ticket `status: blocked` in pipeline-state.yaml with `blocked_reason: "Spec quality FAIL"`
- Orchestrator moves on to next ticket. Does not stop the pipeline.
- Suggest posting a Jira comment requesting clarification (do not post automatically).

**If `--analyze-only`:** After all Phase 1 runs complete, write state file, write partial telemetry to `runs/` (with `final_status: analyze_only` and only Phase 1 data), then stop. Every run mode that executes any phase must produce a telemetry file.

---

### Pre-Run Fitness Prediction (after Phase 1, before Phase 2)

**Purpose:** Calibration signal. After Phase 1 completes, the agent knows the ticket, ACs, tech stack, repo, and dependencies. This is the natural moment to predict how well the run will go. The prediction is logged, not gating. The factory continues regardless of the score.

**Single question:**

> Given this task's requirements, stack, complexity, and the factory's current capabilities, how confident are you (0-100) that this run will succeed?

**Five dimensions** (same dimensions used in the post-run assessment for delta comparison):

| Dimension | What it measures |
|-----------|-----------------|
| **Spec clarity** | Are the ACs unambiguous? Any vague language? Missing edge cases? |
| **Grill readiness** | Does this task have architectural decisions that need stress-testing? |
| **Implementation complexity** | How many files, services, or systems touched? Familiar stack? |
| **Review risk** | Is this the kind of change where bugs hide? (data mutations, multi-caller, cross-service) |
| **Shipping complexity** | Single repo? Multiple MRs? DAC coordination? |

**Process:**
1. Score each dimension 0-100
2. For each dimension below 100: include a `missing` list explaining what the gap points represent
3. For any dimension below 60: note the specific risk
4. Compute overall fitness prediction (weighted average or judgment call)
5. Write 1-2 sentence assessment
6. Log to `pipeline-state.yaml` under `eval.pre_run` (see schema below)

**Output format in pipeline-state.yaml:**

```yaml
eval:
  pre_run:
    fitness_prediction: 75
    dimensions:
      spec_clarity:
        score: 85
        missing:
          - AC-3 edge case for null inputs not specified
      grill_readiness:
        score: 70
        missing:
          - Cross-service data mutation path not fully mapped
          - No existing ADR for adapter null-handling convention
      implementation_complexity:
        score: 80
        missing:
          - 10 adapters need coordination, hard to verify all callers
      review_risk:
        score: 55
        missing:
          - Legacy callers may pass null for new parameters
          - No integration test for multi-adapter null propagation
      shipping_complexity:
        score: 90
        missing:
          - Multi-module build coordination
    assessment: "Straightforward backend ticket but AC-3 touches 10 adapters with no explicit null-handling spec. Review risk is the weak link."
```

**Not a blocker.** The pipeline continues to Phase 2 regardless of the score. The prediction's value emerges when compared against the post-run assessment: systematic over-confidence reveals blind spots, under-confidence reveals unnecessary caution.

---

### Phase 2: DESIGN

**Purpose:** Tactical implementation plan. Not architecture (that's done before Dark Factory runs). Maps ACs to files, functions, and test targets.

**Process:**
1. Read analyst outputs: `acceptance_criteria.vN.json`, `affected_repos.vN.json`, `assumptions.vN.json`
2. For each affected repo:
   - Read CLAUDE.md (if present)
   - Scan code areas referenced by ACs (grep for relevant classes, endpoints, components)
   - Detect technology stack (see Technology Adaptation table)
3. For each AC:
   - Identify files to create/modify
   - Identify functions to add/change
   - Identify test files and test approach
   - **Existing implementation check (brownfield gate):** Before proposing new routes, pages, components, or endpoints, search the codebase for existing implementations serving the same data path or behavior. If Phase 1 (Step 4.5) classified the ticket as `modification`, every assumption about UI placement, routes, nav items, and permissions must be validated against what already exists. Do NOT create parallel artifacts when modifying existing code satisfies the AC. KTP-713 lesson: agent invented a new `/market-research` page when `/proximity-chatbot` already existed.
   - **Write test specifications** (mandatory): For each AC, describe the tests to write before code. Include method signatures, expected assertions, and whether the test is a baseline (existing behavior) or new-behavior test. Example:
     - Baseline: `getStateMetrics(country=null)` returns `COUNTRY='US'` (backward compat)
     - New: `getStateMetrics(country='CA')` returns `COUNTRY='CA'`
     - Adversarial: `getStateMetrics(country='')` — empty string edge case
   These are specifications, not implementations. Phase 4 writes the actual test bodies.
4. For multi-module Maven repos: identify the specific module(s) from file paths, scope all Maven commands to those modules (e.g., `mvn compile -pl proximity-report-service`)

**Prerequisites assessment (mandatory):**

After writing the implementation plan, assess execution prerequisites:

1. **Tool scan:** From the plan's file list and commands, extract required tools:
   - Build tools: maven, npm, tsc, tippecanoe, mapshaper, ogr2ogr, etc.
   - Runtime: Java 17, Node 18+, Python 3.x, Martin, Docker, etc.
   - Data: input files, API keys, database access, BQ datasets

2. **Availability check:** For each tool/data item:
   ```bash
   which {tool} || echo "MISSING: {tool}"
   ```
   For data: check file existence, API key env vars, BQ dataset access.

3. **Write `design/prerequisites.vN.md`:**
   | Prerequisite | Type | Available | Install/Obtain |
   |---|---|---|---|
   | tippecanoe | tool | NO | `brew install tippecanoe` |
   | mapshaper | tool | NO | `npm install -g mapshaper` |
   | us_zip.geojson | data | NO | Download from Google Drive (link in README) |

4. **Gate decision (tools):**
   - All available → proceed
   - Missing items with known install commands → **install them automatically** (tools only, not data), re-check, proceed

5. **Gate decision (data prerequisites) — Escalation Ladder:**

   Data prerequisites (input files, datasets, API responses) that are required by an AC are part of the ticket's definition of done. If you can't obtain the data, you can't complete the ticket.

   **Step 1 — Search locally.** `find` across the org root, check other worktrees, check `/tmp`, check common download directories (`~/Downloads`, `~/Desktop`). The file might already exist somewhere on disk.

   **Step 2 — Attempt automated acquisition.** If the prerequisite has a known URL (documented in scripts, README, or the implementation plan), attempt to download it. Use `curl -Lf` with appropriate timeouts. For authenticated sources (Google Drive, S3), check if credentials are available (gcloud auth, aws cli, etc.). For BQ datasets, attempt `bq query` to verify access. For API keys, check 1Password CLI (`op read`).

   **Step 3 — HALT and ask the user.** If steps 1 and 2 both fail: set `status: blocked_prerequisites` in pipeline-state.yaml. Write the exact steps needed to obtain the data. Present the blocker to the user via `AskUserQuestion`. Do NOT proceed. Do NOT create synthetic data. Do NOT design workarounds. The pipeline stops here until the human resolves the blocker.

   **Anti-pattern: synthetic data workaround (NEVER DO THIS)**

   If a required data file is missing (e.g., us_zip.geojson for a tileset pipeline), the agent must NOT:
   - Create a minimal test file with 2-3 features as a stand-in
   - Run the pipeline with partial data and call downstream phases PASS
   - Report "PARTIAL" buried in a report while the phase summary says PASS
   - Design a `--skip-{thing}` flag to bypass the missing data
   - Rationalize that "partial execution with test data is better than stopping"

   This produces artifacts that look complete but aren't. The user sees 8 green PASSes and assumes the work is done. The incomplete output is indistinguishable from complete output without reading the fine print.

   Instead: search for the file (Step 1) → attempt download (Step 2) → HALT if unavailable (Step 3).

   **Acceptable partial execution:** Only when the user explicitly says "run what you can, I know {data} is missing" AFTER being informed of the blocker. In this case, every downstream phase must carry a `PARTIAL (missing: {filename})` verdict. The final summary must show PARTIAL, not PASS. See Verdict Propagation below.

6. **Human resumes:** After installing/obtaining prerequisites, human confirms. Pipeline resumes from Phase 3 (Grill) with prerequisites verified.

**Produces:** `design/impl-plan.vN.md`, `design/prerequisites.vN.md` (in ticket folder, NOT committed to repo)

**Gate:** Plan file exists and is non-empty. Tool prerequisites either all available or auto-installed. Data prerequisites either all available, auto-acquired (Steps 1-2), or pipeline halted at Step 3.

---

### Verdict Propagation

A phase's verdict is not independent. Upstream constraints flow downstream.

**Taint rules:**
- If Phase 2 sets `blocked_prerequisites` for ANY item (and the user explicitly approves partial execution), every subsequent phase inherits a `tainted: true` flag with the blocker reason.
- A tainted phase cannot report `PASS`. Its maximum verdict is `PARTIAL ({reason})`.
- The pipeline summary uses the WORST verdict across all phases, not the best.
- If any phase is PARTIAL, the pipeline `final_status` is `partial`, not `complete`.

**How taint propagates in pipeline-state.yaml:**
```yaml
tickets:
  KTP-676:
    taint:
      - source: phase_2_prerequisites
        reason: "us_zip.geojson missing — ZIP tilesets use test data"
        affects: [implement, review, qa, ship]
    ac_progress:
      AC-1: done
      AC-2: partial (tainted: us_zip.geojson)
      AC-3: partial (tainted: us_zip.geojson)
      AC-4: partial (tainted: us_zip.geojson)
      AC-5: done
```

**Display in summary:**
```
4. IMPLEMENT:  PARTIAL — ZIP tilesets use test data (us_zip.geojson missing)
5. REVIEW:     PARTIAL — reviewed with incomplete artifacts
6. QA:         PARTIAL — 3/5 ACs fully verified, ZIP/FSA partial
7. SHIP:       PARTIAL — shipped bug fixes only, not production tilesets
```

**When taint does NOT apply:** If Phase 2 halts (Step 3) and the user provides the missing data before resuming, there is no taint. The data is now available. Normal PASS verdicts apply.

---

### Phase 3: GRILL

**Purpose:** Interrogate the implementation plan. Surface gaps, unverified assumptions, and missing edge cases before any code is written. Cheaper to find a bad decision here than in Phase 5 (Review) or Phase 6 (QA).

**Delegates to:** `/grill-with-docs` skill.

**Input:** `design/impl-plan.vN.md` from Phase 2, plus `analyst/acceptance_criteria.vN.json` and `analyst/assumptions.vN.json` for context.

**Execution model (always autonomous, never blocks on human):**
The orchestrator dispatches two sub-agents as a pair:
1. **Questioner agent** runs `/grill-with-docs` against `design/impl-plan.vN.md`. Reads the plan, challenges it against the existing domain model and documentation (CONTEXT.md, ADRs, contracts), and generates the interrogation questions.
2. **Winston answerer agent** (pragmatic architect persona) receives each question and answers it by researching the codebase: reading relevant code, checking ADRs, scanning test files, reviewing the analyst assumptions. Winston's role is to provide grounded, evidence-backed answers. Not theoretical. Not aspirational. What the code actually does today and what the plan proposes to change.

Load Winston persona from: `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/architect.md`

Winston answers pragmatically: if the code already handles a case, he says so with a file reference. If a decision is arbitrary (two approaches are equivalent), he picks one and moves on. If a question exposes a real gap (no code handles this, no spec covers it), he flags it as unresolved.

This keeps Phase 3 fully autonomous and non-blocking. The human never enters the loop. Gaps found by the grill are logged in the report for the human to review at their convenience, but the pipeline continues to Phase 4.

**Produces:**
- `design/grill-report.vN.md` with resolved decisions, parked items, and gaps
- `design/adr-draft.vN.md` — **ADR side product (mandatory).** Every resolved decision from the grill that represents a non-obvious choice (why approach A over B, why this library, why this data flow) gets captured as a draft ADR. The ADR follows the repo's existing format (check `docs/adr/` or `agent-os/architecture/adr/`). This draft is NOT committed automatically. It is placed in the ticket folder for the user to review. If the user approves, Phase 7 (SHIP) commits it to the repo alongside the code.

**Why an ADR from the grill:** The grill forces decisions to be articulated and defended. That articulation IS the ADR content. Capturing it here costs nothing (Winston already produced the reasoning) and prevents the common failure mode where decisions are made, code is written, but nobody records why.

**Gap resolver dispatch (after grill, before gate):**
For each unresolved gap in the grill report, classify it by type and dispatch to the matching BMAD persona for a single-shot resolution. This is a dispatch table, not a committee.

| Gap Type | Resolver | Persona File |
|----------|----------|-------------|
| Product/business tradeoff | John (product manager) | `_bmad/bmm/agents/pm.md` |
| Spec contradiction | Leo (spec coach) | `_bmad/bmm/agents/sm.md` |
| Architecture choice | Winston (already in the grill) | No re-dispatch needed |
| Implementation detail | Amelia (dev) | `_bmad/bmm/agents/dev.md` |
| Risk acceptance | **Human (Gabriel)** | No persona substitutes for accepted risk |

Each resolver gets the specific gap, the relevant context from the grill report, and produces a one-shot answer. The answer is appended to the grill report under the gap it resolves, and if the decision is non-obvious, it feeds into the ADR draft.

Only `risk_acceptance` gaps escalate to the human. All other types are resolved autonomously by the appropriate persona. If a persona cannot resolve the gap (insufficient information), it becomes `risk_acceptance` and escalates.

**Gate:** Grill report exists. ADR draft exists (even if empty, meaning no non-obvious decisions were made). No gate on gap count. Gaps classified as `risk_acceptance` are noted in `pipeline-state.yaml` as snags with `type: spec_ambiguity` and the implementation phase accounts for them. The pipeline continues regardless. Risk gaps don't block, they inform.

**Telemetry:** Log duration, number of branches interrogated, resolved vs. parked vs. gap counts.

---

### Phase 4: IMPLEMENT

**Purpose:** Write code, one AC at a time. Worktree isolation, WIP commits, tech-adapted verification.

**Process:**

1. **Create worktree:**
   ```bash
   git worktree add /tmp/{TICKET-ID} -b {TICKET-ID}-short-desc origin/dev
   ```
   If worktree already exists: check if clean (`git -C /tmp/{TICKET-ID} status --porcelain`). If clean, reuse. If dirty, warn user and ask before cleaning.

2. **Implement AC-by-AC with TDD (sequential):**

   For each AC from `acceptance_criteria.vN.json`:

   **a. Read design plan** — Read the design plan entry for this AC, including test specifications from Phase 2.

   **b. BASELINE (if AC modifies existing behavior):**
   Write test(s) that assert the current behavior before any code changes. Run them. They must PASS, proving the behavior exists today.

   **HARD GATE:** If a baseline test fails, the AC's premise is wrong. The behavior assumed to exist doesn't. Log as `spec_assumption_failure` in pipeline-state.yaml with the failing assertion. Halt this AC. Do NOT proceed to RED. Do NOT rationalize ("the test setup is wrong", "the feature works differently"). The test tells you what the code actually does. Surface to the user.

   **c. RED — Write failing test(s) that specify the AC's new behavior:**
   Write the test body from the Phase 2 test specification. Run it. It must FAIL.

   If the test passes immediately: the test is tautological. It tests existing behavior, not the change this AC introduces. Rewrite with tighter assertions that target the actual new behavior. A passing RED test means the test is weak, not that the code is already correct.

   If the test errors (compile error, missing import): fix the test infrastructure, re-run until it fails on an assertion, not a build error.

   **d. GREEN — Write minimum code to make tests pass:**
   Write the simplest code that makes the RED test pass. Run all tests (not just the new one). All must pass.

   Do NOT add features beyond what the test requires. Do NOT refactor other code. Do NOT "improve" adjacent code. GREEN means the test passes, nothing more.

   **e. REFACTOR (optional):**
   Clean up the code from step d without changing behavior. Tests must stay green. Extract helpers, improve names, remove duplication within the AC's scope.

   **f. WIP commit:** `{TICKET-ID}: AC-{N} — {short what}`

   **g. Run compile/type-check** (technology-adapted, module-scoped)

   **h. Run relevant unit tests** (unit + integration tests for changed validators/DTOs/controllers, see step 6)

   **Test failure recovery (within any TDD step):**
   If tests fail unexpectedly:
   - Attempt fix (max 3 attempts per AC)
   - If fixed: re-commit with amended description
   - If still failing after 3 attempts: mark AC as `stuck` in pipeline-state.yaml

3. **Adversarial edge-case tests (after all ACs are GREEN):**

   For each AC, write one additional test that tries to break the implementation by exploiting edge cases the AC doesn't mention:
   - Null inputs from callers that may not pass new parameters
   - Empty strings, zero values, negative numbers
   - Callers from other services using the old call signature
   - Boundary conditions (max length, overflow, off-by-one)

   Run each test. If it fails: this is a real bug. Fix the code, commit the fix alongside the test with message `{TICKET-ID}: edge-case guard — {what broke}`.

   This is the KTP-682 pattern. The null-country test that every post-hoc test missed.

4. **Update state:**
   After each AC, update `ac_progress` in pipeline-state.yaml:
   ```yaml
   ac_progress: { AC-1: done, AC-2: done, AC-3: in_progress }
   ```

5. **Execution verification checkpoint (unconditional):**

   After all ACs are implemented and tests pass, **attempt to run the artifact.** The attempt is mandatory. The outcome determines the `execution_verified` value in pipeline-state.yaml, which Phase 6 reads as a hard gate.

   | Stack | Verification Command | Success Signal |
   |-------|---------------------|----------------|
   | Java/Maven (Spring) | `mvn spring-boot:run -pl {module} -Dspring-boot.run.profiles=local` | "Started {App}Application in X seconds" in output |
   | Node/NPM | `npm run dev` or `npm start` | Server listening on port, no crash |
   | Python | `python {main}.py` with test input | Expected output, exit code 0 |
   | Shell | `bash {script}.sh` with fixtures | Expected output, exit code 0 |

   **Process:**
   - Run the verification command in the worktree
   - Wait for the success signal (timeout: 120s for Spring, 30s for Node/Python/Shell)
   - If startup succeeds: kill the process, write `execution_verified: true` in pipeline-state.yaml
   - If startup fails with **code errors** (missing import, duplicate bean, circular dependency): fix before proceeding. Re-run until startup succeeds or the error is clearly infra.
   - If startup fails with **infrastructure errors** (missing DB connection, API key not set, BQ credentials unavailable): the attempt happened and proved the failure is not a code bug from this ticket. Write `execution_verified: infra_blocked({specific error message})` in pipeline-state.yaml and proceed.

   **Stack exceptions (explicit match only):**
   - Terraform (`.tf` files, `Local Exec == no`): write `execution_verified: not_applicable(terraform)`, proceed.
   - No other stack qualifies for `not_applicable`. If the Technology Adaptation table says `Local Exec == yes` for the detected stack, the attempt runs.

   **Why this matters:** Unit tests run components in isolation with mocked dependencies. The startup check catches Spring context wiring issues (duplicate beans, missing imports, circular dependencies), missing property bindings, and component scan failures that unit tests miss entirely. These are the bugs that pass CI locally and explode on deploy.

   **Valid `execution_verified` values (pipeline-state.yaml):**

   | Value | Meaning | Phase 6 verdict cap |
   |-------|---------|---------------------|
   | `true` | Startup succeeded | No cap |
   | `infra_blocked({reason})` | Attempt was made, failed on infra, not code | `PARTIAL` |
   | `not_applicable(terraform)` | Stack has no local exec (Terraform only) | No cap |
   | `false` | Attempt was made, failed on code errors not yet fixed | `INCOMPLETE` |
   | *(field missing)* | No attempt was made | `INCOMPLETE` |

   **Anti-pattern: rationalizing skip (NEVER DO THIS)**

   The agent must NOT skip the execution attempt. There are no escape hatches. These are not valid reasons to skip:
   - "BQ credentials aren't available locally" (run the attempt; if it fails on BQ, that's `infra_blocked`, not a skip)
   - "All 384 unit tests pass" (unit tests don't catch wiring issues)
   - "The changes are validators only, not startup-related" (validators are Spring beans)
   - "It would take too long" (startup check is 30-120 seconds)
   - "Pre-existing infrastructure requirements" (the attempt still runs; infra failures are logged, not skipped)

6. **Integration test requirements (mandatory when validators/DTOs/controllers change):**

   Unit tests prove components work in isolation. Integration tests prove the request chain works end-to-end. Both are required.

   | Stack | Test Type | Required When | Minimum Coverage |
   |-------|-----------|---------------|-----------------|
   | Java/Maven (Spring) | MockMvc `@WebMvcTest` | Validator, DTO, or controller changes | (a) Happy path: POST with new input format → 200 + response shape, (b) Rejection path: invalid input → 400 |
   | Node/NPM (Express/Next) | Supertest | Route handler, middleware, or validator changes | Same pattern adapted to JS |
   | Python (Flask/FastAPI) | TestClient | Endpoint or validator changes | Same pattern |

   **Concrete rule:** If Phase 4 creates or modifies a validator, the corresponding controller integration test MUST be updated. These tests count toward the AC's test evidence in Phase 6.

**Produces:** Code on branch, one commit per AC (TDD: RED verified before GREEN), adversarial edge-case tests, integration tests, execution verification result, updated pipeline-state.yaml.

**Artifact placement:** Spec docs, ADRs, or contracts produced during implementation are committed to the respective repo. Session reports, status, impl-plans stay in project-management ticket folder.

---

### Phase 5: REVIEW

**Purpose:** Adversarial code review by an agent that did not write the code.

**Why external review:** The agent that builds code has ownership bias. When reviewing its own work, it assesses "how confident am I that this is safe?" rather than "what breaks if my assumption is wrong?" KTP-682 proved this: the implementing agent's self-review caught the obvious AC-6 geography issue but missed the null-country regression in 10 adapters. Gabriel's "try to break it" from outside the agent's context was more effective than the formal review.

**Dispatch:** A fresh Agent via the Agent tool (not a Skill invocation). The reviewing agent runs in a clean context with no knowledge of the design plan, grill report, or implementation journey.

**What the reviewing agent receives (restricted prompt):**

1. The diff: `git diff origin/dev..HEAD` (from the worktree)
2. The AC list: contents of `analyst/acceptance_criteria.vN.json`
3. The repo's `CLAUDE.md` (for conventions and code style context)

**What the reviewing agent does NOT receive:**
- Design plan (`design/impl-plan.vN.md`)
- Grill report (`design/grill-report.vN.md`)
- ADR drafts, architecture docs, assumption files
- Pipeline-state.yaml or any Phase 1-4 artifacts
- The ticket folder path or any session context

**Prompt template (inline, used verbatim):**

```
You are reviewing code that will ship to production.
Your job: find bugs that would reach users. Not style. Not suggestions. Bugs.

For each finding:
1. Describe the bug and how it manifests
2. Write a test that demonstrates the failure
3. Run the test. If it passes (no bug found), retract the finding

You get credit for bugs caught, not findings filed.
Focus areas: null/missing parameter regressions in existing callers,
data path changes that break downstream consumers, edge cases the
AC doesn't mention but the code must handle.

DIFF:
{git diff origin/dev..HEAD}

ACCEPTANCE CRITERIA:
{contents of acceptance_criteria.vN.json}

REPO CONVENTIONS:
{contents of repo CLAUDE.md}
```

**Post-review processing (Amelia):**

Load Amelia persona from: `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/dev.md`

Amelia receives the external agent's findings and processes them:
1. Fix CRITICAL and HIGH findings (minimal, targeted)
2. Push back on false positives with codebase evidence (the finding's test should have caught it; if the test passed, the finding is retracted)
3. Note MEDIUM and LOW findings as accepted
4. Re-verify after fixes (compile + tests in worktree)

**Produces:** `review/external-adversarial-report.vN.md` (in ticket folder)

**Gate:** Zero CRITICAL remaining. HIGH findings either fixed or accepted with documented reasoning.

### Phase 5b: Convergence Escalation

**Purpose:** Prevent "accepted risk" inertia from carrying findings through the pipeline unchallenged. When independent analyses converge on the same finding, that's a signal to escalate, not to anchor on a prior "accepted" label.

**Process:**

After Phase 5 (Review) completes, the orchestrator MUST cross-reference Phase 3 (Grill) gaps with Phase 5 findings:

1. **Match findings:** For each Phase 5 finding, check if the same risk appears in the Phase 3 grill report (match by affected code, data path, or described failure mode, not just keywords).

2. **Flag convergence:** If a finding appears in BOTH Phase 3 and Phase 5, it is a **convergence signal**. Two independent analyses agree this risk is real. Mark it in pipeline-state.yaml:
   ```yaml
   convergence_signals:
     - finding: "AC-6 'United States'→'US' default change may break /geography/states"
       phase_3_ref: "Gap 4, MEDIUM, accepted"
       phase_5_ref: "Finding 6, HIGH, accepted"
       escalated_severity: HIGH
       resolution: pending
   ```

3. **Invalidate prior acceptance:** The "accepted risk" classification from Phase 3 is NO LONGER VALID. The finding must be re-evaluated as if seen for the first time. "I already acknowledged this in Phase 3, therefore it's handled" is not resolution. Acknowledgment without action is inertia.

4. **Resolve or escalate:** For each convergence signal that affects runtime behavior (not just code quality), the default action is **defer or fix**, not "accept and move on." Resolution requires one of:
   - **Code change** that eliminates the risk
   - **Explicit deferral** to another ticket (with the dependency documented in pipeline-state.yaml and a Jira comment on the downstream ticket)
   - **Human approval** of the risk via `AskUserQuestion` (not silent carry-forward)

5. **Severity escalation:** If Phase 3 said MEDIUM and Phase 5 said HIGH, the escalated severity is the higher of the two. The agent does not get to downgrade severity by averaging.

**Anti-pattern: advocacy bias in self-review (NEVER DO THIS)**

The agent built the code, then reviewed the code. When a finding reappears, the reflex is advocacy (defend the work product and keep the pipeline moving) rather than analysis (genuinely stress-test whether this is safe). The agent must NOT:
- Use a prior "accepted" label as evidence that the risk is handled
- Rate severity based on "how confident am I" instead of "what breaks if I'm wrong"
- Build a case for why merge is safe when the user asks "how safe is this merge?" (that's advocacy, not analysis)
- Stop tracing at "grep found no callers" when the risk involves runtime data paths

**When the user asks "is this safe?" or "what are the regression risks?":**
- Trace the actual data path for each change end-to-end
- Rate severity based on blast radius if the assumption is wrong, not confidence in the assumption
- If a finding was previously "accepted," re-examine it fresh: who accepted? what's the blast radius? what's the recovery path if the assumption fails?

**Produces:** Updated `pipeline-state.yaml` with `convergence_signals` section. If any signals require human approval, the pipeline pauses here.

**Gate:** All convergence signals resolved (fixed, deferred with ticket, or human-approved). Zero unresolved convergence signals may pass to Phase 6.

---

### Phase 6: QA

**Purpose:** AC verification with concrete evidence. This is not test execution (Phase 4 did that). This is proving each AC is met.

**Agent segregation (mandatory):** Phase 6 runs in a **separate agent** from the implementing agent. The QA agent receives: the AC list, affected file paths, the Technology Adaptation table below, and access to the running service (if applicable). It does NOT receive: the implementation plan, the implementor's rationale, the grill report, or any Phase 1-4 artifacts. This prevents the builder from self-certifying its own work.

**QA Technology Adaptation:**

| Stack | QA requirement | Verdict if skipped |
|-------|---------------|-------------------|
| Node/NPM (frontend) | `npm run dev`, navigate to affected routes, capture screenshot per AC | `PARTIAL (no browser verification)`, never `PASS` |
| Java/Maven (backend) | Run integration tests OR curl endpoints with expected response shapes | `PARTIAL (no endpoint verification)`, never `PASS` |
| Dataform/SQL | BQ assertion queries with before/after comparison | `PARTIAL (no BQ assertion)`, never `PASS` |
| Terraform | `terraform plan` output reviewed, resource diff validated | `PARTIAL (plan not reviewed)`, never `PASS` |
| Shell/Python scripts | Run with fixtures, verify output files exist and content matches expected | `PARTIAL (no execution verification)`, never `PASS` |

There is no "if browser tools available" conditional. Frontend QA REQUIRES browser verification. If browser tools are unavailable, the verdict is `PARTIAL`, never `PASS`.

**QA agent dispatch prompt template (inline, used verbatim):**

```
You are performing QA verification for ticket {TICKET_KEY}.
Your job: prove each AC is met with concrete evidence. Not opinions. Evidence.

For each AC:
1. Find the code that implements it (file path + line range)
2. Find the test that proves it works (test name + pass output)
3. If this is a frontend AC: start the dev server, navigate to the affected route, capture a screenshot
4. Render a verdict: PASS (with evidence) or FAIL (with what's missing)

You do NOT have access to the implementation plan or design rationale.
You see only the code and the ACs. Judge by what the code does, not what it intended to do.

ACCEPTANCE CRITERIA:
{contents of acceptance_criteria.vN.json}

AFFECTED FILE PATHS:
{list of files changed in this branch}

TECHNOLOGY ADAPTATION:
{matching row from QA Technology Adaptation table}
```

**Process:**
For each AC from `acceptance_criteria.vN.json`, collect structured evidence:

| Evidence Type | Description |
|---------------|-------------|
| `code_ref` | File path + line range of the code that satisfies this AC |
| `test_ref` | Test name + pass/fail output proving the behavior |
| `screenshot` | (frontend ACs only, mandatory per QA Technology Adaptation table) |
| `validation_method` | How the AC was verified (e.g., "unit test X passes", "endpoint returns expected shape") |

Verdict per AC: `PASS` / `FAIL` / `PARTIAL`

**Bounce-back protocol:**
If any AC is `FAIL`:
1. Write specific failure description
2. Return to Phase 4 with that AC targeted
3. Re-run Phase 6 for that AC
4. Max 2 bounce-backs total. After 2: mark ticket `stuck`, escalate to human.

**Produces:** `qa/qa-report.vN.md` with per-AC evidence table

**QA report template:**
```markdown
# QA Report: {TICKET-KEY} v{N}

**Date:** {YYYY-MM-DD}
**Branch:** {branch_name}
**Verification level:** {EXECUTION_VERIFIED | COMPILE_ONLY}
**Overall verdict:** {ALL_PASS | PARTIAL | FAIL}

## Per-AC Evidence

| AC | Description | Verdict | Code Ref | Test Ref | Validation Method |
|----|-------------|---------|----------|----------|-------------------|
| AC-1 | ... | PASS | src/Main.java:45-72 | MainTest#testFeature | Unit test passes, service starts clean |
| AC-2 | ... | PASS | src/Api.java:100-120 | ApiTest#testEndpoint | Returns 200 with expected shape |

## Notes
- {Any observations, edge cases noted, partial coverage}
```

**Verification level pass criteria:**

| Local Exec | PASS requires |
|------------|---------------|
| yes | Compile + test + execution evidence (exit code 0, output validated) |
| no | Compile + test + explicit banner. Human must verify execution in cloud. |
| configurable (resolved to yes) | Same as yes |
| configurable (resolved to no) | Same as no |

**"Code review" alone is NEVER sufficient for a PASS verdict.** Code review is evidence of understanding, not evidence of function.

**Verification level enforcement (hard gate via pipeline-state.yaml):**

Phase 6 MUST read the `execution_verified` field from pipeline-state.yaml before rendering any AC verdict. This is structural, not advisory. The agent cannot override the cap.

| `execution_verified` value | Phase 6 verdict cap | QA report `Verification level` |
|---|---|---|
| `true` | No cap (PASS allowed) | `EXECUTION_VERIFIED` |
| `not_applicable(terraform)` | No cap (PASS allowed) | `NOT_APPLICABLE (terraform)` |
| `infra_blocked({reason})` | `PARTIAL` (max for any AC) | `INFRA_BLOCKED ({reason})` |
| `false` | `INCOMPLETE` (max for any AC) | `INCOMPLETE (code errors not resolved)` |
| *(field missing)* | `INCOMPLETE` (max for any AC) | `INCOMPLETE (no execution attempt)` |

**How this works:**
1. Phase 6 reads `execution_verified` from pipeline-state.yaml
2. If the value maps to a cap (see table), every AC verdict is clamped to that cap regardless of test evidence
3. The QA report template renders the `Verification level` string from the table. The agent does not choose the string.
4. If `execution_verified` is missing or `false`, Phase 6 MUST return to Phase 4 step 5 and attempt execution before QA can complete. This is not optional.

**Similarly for integration tests:** If Phase 4 step 6 applies (validators/DTOs/controllers changed) and no integration tests were written, Phase 6 must flag `missing_integration_tests: true` and cap the verdict at `PARTIAL` until they are added.

**Gate:** All ACs `PASS`. After 2 bounces for any AC: `STUCK`, escalate to human.

---

### Phase 7: SHIP

**Purpose:** Version bump, push, create MR, update Jira.

**Delegates to:** `/klever-mr` for Klever repos. Supervisr: would use `gh pr create` but not wired in v1.0.

**Step 0: Pre-Ship Artifact Gate (mandatory, non-bypassable)**

Before any shipping action, run the pre-ship gate script. It verifies that every required artifact exists before the pipeline is allowed to ship:

```bash
~/.claude/skills/dark-factory/resources/pre-ship-gate.sh <TICKET_DIR>
```

`<TICKET_DIR>` is the ticket folder holding `pipeline-state.yaml`, `qa/`, `review/`, `analyst/`, and `design/` (e.g. `tickets/KTP/KTP-559/KTP-682`).

**If the exit code is not 0, Phase 7 HALTS.** The script prints exactly which artifacts are missing. Return to the phase that owns each missing artifact, produce it, then re-run the gate. The agent cannot proceed, rationalize, or self-certify past a failed gate.

The script enforces four checks (QA report non-empty, `review/` populated, `execution_verified` present in `pipeline-state.yaml`, frontend screenshots present when a `package.json` repo is affected). A real script that returns exit 1 is harder to rationalize past than inline prose. KTP-713 lesson: "adding more instructional text does not improve compliance" — the agent shipped an MR with 4 unchecked test plan items because no gate verified artifact existence.

This in-pipeline gate is **strong advisory** (the agent runs it and has the last word). The true backstop is the PostToolUse compliance hook, which audits the run after the `dark-factory` Skill call completes — outside agent control. See `resources/compliance-audit.sh`.

**Process:**

1. **Version bump + CHANGELOG:**
   Final commit in worktree: `{TICKET-ID}: version bump + changelog`
   `/klever-mr` handles this via its Gate 4 and Gate 5.

2. **Push branch:**
   Handled by `/klever-mr`.

3. **Create MR:**
   Invoke `/klever-mr` via Skill tool. It enforces pre-flight gates (sync check, version bump, changelog) and creates the MR via GitLab API.

4. **Post Jira comment:**
   Invoke `/post-comment` to draft and post a Jira comment with:
   - MR link
   - AC summary (what was implemented)
   - Evidence highlights from QA report
   - Any assumptions applied

5. **Transition Jira ticket:**
   Move ticket to "In Review" or "In Testing" (ceiling, never higher than review/testing):
   ```bash
   cd ~/.claude/skills/jira && python3 jira_skill.py transition <TICKET-KEY> "In Review" --org <ORG>
   ```

**Produces:** Pushed branch, MR URL, Jira comment, ticket transitioned.

**Auto-merge policy:** Dark-factory invokes `/klever-mr` WITHOUT `--auto-merge`. The MR is created for human review. To enable auto-merge, pass `--auto-merge` to `/dark-factory`.

**Note:** Phase 7 creates the MR. Human merges it. Phase 8 runs after merge.

---

### Phase 8: VALIDATE

**Purpose:** Post-merge dev verification. This makes it "ticket to dev" not "ticket to MR."

**Process:**

1. **Wait for merge:**
   Poll for the MR to be merged (60s interval, max 2 hours):
   ```bash
   git fetch origin
   git branch --contains {pushed_sha} origin/dev
   ```
   If the SHA appears in `origin/dev`, the MR is merged.

2. **Verify on dev (technology-adapted):**

   | Stack | Verification |
   |-------|-------------|
   | Backend (Java) | Curl key endpoints on dev, verify response shape |
   | Frontend (Node) | If Playwright available: smoke test. Otherwise: human gate. |
   | Data (Dataform/SQL) | Run BQ validation query |
   | Infra (Terraform) | Verify resource state via `gcloud` |
   | Script (Shell) | Verify output exists / cron updated |

3. **Human gate for frontend:**
   If the ticket touches frontend code and no automated verification is available:
   ```
   MR merged to dev. Frontend change requires manual verification.
   Please verify on dev and report back.
   ```

4. **If verification fails:**
   Log findings. Do NOT reopen ticket. Write report with what passed and what didn't.

**Produces:** `validate/dev-verification.vN.md`

**Gate:** Human confirmation for frontend changes. Automated smoke for backend/data.

---

## Multi-Ticket Orchestration

### Tier Determination

Topological sort on `depends_on` edges:
- Tier 1: tickets with empty `depends_on`
- Tier N: tickets whose `depends_on` are all in tier < N
- Circular dependencies: fatal error. Report the cycle and stop.

### Execution Loop

```
for each tier (ascending):
    dispatch sub-agents for all tickets in this tier
    (throttled by --concurrency flag, default: all in tier)
    wait for all lanes to report status
    run gate verification:
        for each ticket in this tier:
            git fetch origin
            git branch --contains {merged_sha} origin/dev    # exact SHA check
        run any custom_checks from gate definition
    if gate passes: next tier
    if gate fails: wait (60s interval, 2 hour max), then escalate
```

### Sub-Agent Dispatch

Each sub-agent is dispatched via the Agent tool (not Skill tool). Prompt includes:

- Ticket key, summary, tier number, upstream deps (verified merged), downstream deps
- Path to ticket folder and which files to read first
- The 8-phase lifecycle instructions (full, inline)
- Technology adaptation for this ticket's repo type
- AC progress from state file (for resume: skip ACs marked `done`)
- Completion signal: update `pipeline-state.yaml` with `status: complete` and `merged_sha`
- Escalation signal: update with `status: stuck` and failure description

**Model:** Sub-agents inherit the invoking model. No forced downgrade (implementation tasks need full capability).

### Lane Isolation

Failure in one lane does NOT block other lanes in the same tier. Only downstream tiers are blocked (gate cannot pass with a failed/stuck upstream).

If a ticket is marked `optional: true` in the plan file, its failure does not block the gate.

### Post-All-Tiers

After all tiers complete:
1. Run integration tests from the plan file's `integration_tests` section
2. If no integration tests defined: run standard test suite per affected repo
3. Write final report summarizing all tickets, MR URLs, test results
4. Write pipeline run journal

---

## Technology Adaptation

Detected from repo root files. For multi-module Maven repos, the Design phase identifies target module(s) from AC-referenced file paths. All Maven commands scoped to those modules.

| Detection | Stack | Compile | Test | Version File | Execute | Local Exec |
|-----------|-------|---------|------|-------------|---------|------------|
| `pom.xml` (single) | Java/Maven | `mvn compile` | `mvn test -Dtest={Class}` | `pom.xml` | `mvn spring-boot:run` (verify startup, no crash) | yes |
| `pom.xml` (multi) | Java/Maven | `mvn compile -pl {module}` | `mvn test -pl {module} -Dtest={Class}` | `{module}/pom.xml` | `mvn spring-boot:run -pl {module}` | yes |
| `package.json` | Node/NPM | `tsc --noEmit` or `npm run build` | `npm test -- {file}` | `package.json` | `npm run dev` (verify startup, page loads) | yes |
| `.sqlx` / `dataform.json` | Dataform/SQL | N/A | BQ query assertions | N/A | BQ dry-run query | configurable |
| `.tf` files | Terraform | `terraform validate` | `terraform plan` | N/A | N/A (cloud-only) | **no** |
| `.py` (no package.json) | Python | `python -m py_compile` | `pytest` | N/A | Run script with test input, verify output | yes |
| `.sh` files | Shell | `bash -n` | Script with fixtures | N/A | Run script (dry-run first, then real), verify output | yes |

**`Local Exec` column semantics:**
- `yes`: Phase 4 must execute the artifact and verify it runs. Phase 6 requires execution evidence.
- `no`: Execution requires cloud infra. Phase 2 surfaces this as a known limitation. Phase 6 accepts compile+test evidence but adds banner: `Verification level: COMPILE_ONLY (execution requires cloud infra)`.
- `configurable`: May or may not be possible locally. Phase 2 checks and sets the value for this run.

**Multi-module detection:** If `pom.xml` contains `<modules>`, read `<module>` entries. Match AC file paths against module directories. Scope commands to matching modules only.

---

## State Persistence

File: `<ticket-folder>/pipeline-state.yaml`

```yaml
pipeline: dark-factory
version: 1
started: 2026-05-21T09:00:00Z
last_updated: 2026-05-21T11:30:00Z
input_mode: plan  # single | list | plan
plan_file: reports/architecture/canada-map-execution-pipeline.md

tickets:
  KTP-676:
    tier: 1
    status: complete       # pending | analyzing | designing | implementing | reviewing | qa | shipping | validating | complete | stuck | blocked | blocked_prerequisites
    phase: validate
    branch: KTP-676-canadian-tilesets
    merged_sha: abc1234
    mr_url: https://...
    execution_verified: true    # REQUIRED. Written by Phase 4 step 5, read by Phase 6.
    ac_progress: { AC-1: done, AC-2: done, AC-3: done }
    failures: []
  KTP-679:
    tier: 1
    status: implementing
    phase: implement
    branch: KTP-679-crosswalk-table
    execution_verified: infra_blocked(BQ credentials not available locally)
    ac_progress: { AC-1: done, AC-2: in_progress }
    failures: []
  KTP-680:
    tier: 2
    status: blocked
    blocked_by: [KTP-679]
    phase: null
    execution_verified: null   # Not yet reached Phase 4
    ac_progress: {}

eval:
  pre_run:
    fitness_prediction: 75
    dimensions:
      spec_clarity:
        score: 85
        missing:
          - AC-3 edge case for null inputs not specified
      grill_readiness:
        score: 70
        missing:
          - Cross-service data mutation path not fully mapped
      implementation_complexity:
        score: 80
        missing:
          - 10 adapters need coordination
      review_risk:
        score: 55
        missing:
          - Legacy callers may pass null for new parameters
      shipping_complexity:
        score: 90
        missing:
          - Multi-module build coordination
    assessment: "Straightforward backend ticket but review risk is the weak link."
  post_run:
    task_confidence: 82
    missing:
      - AC-2 deferred to follow-up ticket
    factory_fitness: 72
    dimensions:
      spec_clarity:
        score: 85
        missing:
          - AC-2 referenced non-existent Brand.country field
      grill_effectiveness:
        score: 70
        missing:
          - Grill did not probe async timing between hooks
      implementation_smoothness:
        score: 90
        missing:
          - One retry on MockMvc test setup
      review_quality:
        score: 55
        missing:
          - False positive on hasCenteredRef, missed real timing bug
      shipping_friction:
        score: 80
        missing:
          - GitLab project index empty, needed rebuild
    needs_rerun: false
    handoffs_proposed: 1
    calibration_delta: 6

gates:
  gate_1:
    between: [tier_1, tier_2]
    status: pending         # pending | passed | failed
    checks:
      KTP-676_merged: true
      KTP-679_merged: false
      KTP-681_merged: true

integration:
  status: pending
  test_results: null
```

**Status values per ticket:** `pending`, `analyzing`, `designing`, `grilling`, `implementing`, `reviewing`, `qa`, `shipping`, `validating`, `complete`, `stuck`, `blocked`, `blocked_prerequisites`

**The `failures` array uses the structured snag format** (same as the telemetry protocol). Sub-agents MUST write snags here as they encounter them, not just at the end. This is the crash-safe persistence layer. If the orchestrator dies, telemetry can be reconstructed from these entries.

```yaml
failures:
  - type: compile_failure
    description: "Missing import after AC-2"
    recovery: "Added import, recompiled"
    severity: medium
    phase: implement
    ticket: KTP-679
    time_lost_minutes: 3
```

**State file updates:** The orchestrator and sub-agents both write to this file. Sub-agents update their own ticket entry. The orchestrator updates gates and integration status. File locking is not enforced (sub-agents work on different tickets and write at different times).

---

## Failure Handling

| Failure | Detection | Recovery | Escalation |
|---------|-----------|----------|------------|
| Spec quality FAIL | Phase 1 `spec_quality == "FAIL"` | Skip ticket, report | Suggest Jira comment |
| Compile fails 3x | Non-zero exit after 3 attempts | Mark AC stuck | Ticket stuck in state |
| Tests fail 3x | Test runner fails after 3 fix attempts | Mark AC stuck | Ticket stuck in state |
| Cascade CRITICAL unfixable | Phase 4 finding survives fix attempt | Mark ticket stuck | Human review needed |
| QA fails 2 bounces | Phase 5 retry counter | Mark ticket stuck | Human review needed |
| MR creation fails | `/klever-mr` returns error | Retry once with fresh auth | Report for manual creation |
| Gate check fails (not merged) | SHA not in origin/dev | Wait (60s interval, 2h max) | Escalate to human |
| Data prerequisite missing | Phase 2 data item not on disk | Search locally → attempt download → HALT (escalation ladder) | `blocked_prerequisites`, user must provide data |
| Execution verification missing | `execution_verified` field missing or `false` in pipeline-state.yaml | Phase 6 returns to Phase 4 step 5, attempt is unconditional | Phase 6 verdict capped at `INCOMPLETE` (hard gate, not advisory) |
| Integration tests missing | Validator/DTO changed, no MockMvc tests | Write integration tests before Phase 6 | Phase 6 verdict capped at `PARTIAL` |
| Convergence signal unresolved | Same finding in Phase 3 + Phase 5 | Fix, defer with ticket, or human approval | Phase 5b blocks until resolved |
| Baseline test fails (pre-change) | Phase 4 step 2b baseline assertion fails | Log `spec_assumption_failure`, halt the AC | AC premise is wrong, surface to user |
| RED test passes immediately | Phase 4 step 2c new-behavior test passes without code changes | Rewrite with tighter assertions targeting the actual change | Tautological test, does not specify new behavior |
| Adversarial edge-case test fails | Phase 4 step 3 post-AC edge-case test fails | Fix the code, commit fix alongside test | Real bug caught (KTP-682 pattern) |
| Worktree conflict | `git worktree add` fails | Check for stale worktrees, prune, retry | Report if persistent |
| Sub-agent compaction | Agent loses context | Reads pipeline-state.yaml + ac_progress, resumes from current phase/AC | Built into lifecycle |
| Nightly Klever shutdown | Time > 23:00 ET or registry 503 | Pause pipeline, write state, note in journal | Resume in morning via `--resume` |
| 3-hour circuit breaker | Wall-clock per ticket > 3h | Mark ticket stuck | Move to next ticket |
| Pre-ship artifact gate fails | Phase 7 Step 0 check finds missing artifacts | Phase 7 HALTS with list of missing items. Agent returns to missing phase. | Cannot ship without required artifacts |
| QA agent dispatch fails | Phase 6 Agent tool dispatch returns error | Retry once, then mark QA as `stuck` | Human must run QA manually |

---

## Artifact Placement

| Artifact Type | Location | Committed to repo? |
|---------------|----------|--------------------|
| Analyst outputs (AC JSON, repos JSON, assumptions JSON) | `tickets/{PREFIX}/{TICKET}/analyst/` | No |
| Implementation plan | `tickets/{PREFIX}/{TICKET}/design/` | No |
| Cascade review report | `tickets/{PREFIX}/{TICKET}/review/` | No |
| QA report | `tickets/{PREFIX}/{TICKET}/qa/` | No |
| Dev verification report | `tickets/{PREFIX}/{TICKET}/validate/` | No |
| Pipeline state | `tickets/{PREFIX}/{EPIC-or-TICKET}/pipeline-state.yaml` | No |
| Run journal | `tickets/{PREFIX}/{EPIC-or-TICKET}/pipeline-run-journal.vN.md` | No |
| ADRs | `{repo}/docs/adr/` or `{repo}/agent-os/architecture/adr/` | **Yes** |
| API contracts | `{repo}/docs/contracts/` or `{repo}/agent-os/contracts/` | **Yes** |
| Spec docs | `{repo}/docs/` or `{repo}/agent-os/specs/` | **Yes** |
| Code, tests, configs | `{repo}/src/`, `{repo}/test/`, etc. | **Yes** |

---

## Skill Delegation Map

| Phase | Delegate | Invocation |
|-------|----------|------------|
| 1 (Analyze) | `/ticket-to-pr-analyst` logic | Sub-agent via Agent tool reads the SKILL.md |
| 2 (Design) | **Inline** (new) | Orchestrator or sub-agent executes directly |
| 3 (Grill) | `/grill-with-docs` | Winston sub-agent answers; grounded in docs; never blocks on human |
| 4 (Implement) | **Inline** (new) | Sub-agent executes directly |
| 5 (Review) | **External adversarial agent** | Agent tool dispatch (fresh context, diff + ACs only) |
| 6 (QA) | **External QA agent** | Agent tool dispatch (separate from implementor, AC list + file paths + tech table only) |
| 7 (Ship) | `/klever-mr` + `/post-comment` + `/jira` | Skill tool invocations |
| 8 (Validate) | **Inline** (new) | Sub-agent or orchestrator executes directly |

---

## Dry-Run Output

When `--dry-run` is set, parse the plan file (or build from flat list + Jira dep check), display, and exit:

```
Dark Factory — DRY RUN

Plan file: {path or "auto-generated from flat list"}

Tier 1 (no dependencies):
  KTP-676 — {summary from Jira or "not fetched"}
  KTP-679 — ...
  KTP-681 — ...

Tier 2 (blocked by tier 1):
  KTP-680 — depends on: KTP-679
  KTP-682 — depends on: KTP-681

Tier 3 (blocked by tier 2):
  KTP-683 — depends on: KTP-676, KTP-682

Tier 4 (blocked by tier 3):
  KTP-684 — depends on: KTP-683
  KTP-685 — depends on: KTP-683 [optional]

Gates:
  tier_1 -> tier_2: no custom checks
  tier_2 -> tier_3: 1 custom check (Mapbox tilesets accessible)

Integration tests: 2 defined (app-front-portal, app-proximity-report)

No actions taken. Use without --dry-run to execute.
```

---

## Observability Protocol

Every phase logs telemetry automatically. No user action required. Two outputs per run:
1. **Run telemetry** (YAML) in `~/.claude/skills/dark-factory/runs/` (skill-level, survives ticket archival)
2. **Run journal** (markdown) in `<ticket-folder>/` (ticket-level, context-rich narrative)

The telemetry is structured data for cross-run pattern detection. The journal is human narrative for retrospective review. Both are mandatory.

### Phase-Level Instrumentation

Every phase (1 through 8) must record:

```yaml
{phase_name}:
  started: {ISO 8601}
  ended: {ISO 8601}
  duration_minutes: {float}
  status: pass | fail | skip | stuck
  snags: []                            # array of snag objects, may be empty
  delegations: []                      # skills/agents invoked, with outcome
```

**Snag format:**
```yaml
- type: {compile_failure | test_failure | worktree_conflict | skill_delegation_failed | gate_timeout | auth_expired | registry_down | spec_ambiguity | multi_module_mismatch | pre_existing_bug | other}
  description: "What happened"
  recovery: "What was done to fix it"
  severity: critical | high | medium | low
  phase: {phase where it occurred}
  ticket: {ticket key}
  time_lost_minutes: {estimated minutes spent on recovery}
```

**Delegation format:**
```yaml
- skill: ticket-to-pr-analyst
  outcome: success | failure
  duration_minutes: 12
  notes: "Clean run, 5 ACs extracted"
```

### When to log snags

A snag is anything that required recovery, a workaround, or caused time loss. Examples:
- Compile failed and needed a fix (even if fixed on first attempt)
- Test failure from pre-existing bug
- Worktree already existed and needed cleanup
- Skill delegation returned an error and was retried
- Gate check waited >5 minutes for a merge
- Ambiguous spec required an assumption
- Multi-module detection picked the wrong module initially
- Authentication expired mid-run

Do NOT log: normal operations completing successfully, expected waits (like the standard gate check interval), or user-initiated pauses.

### Run Telemetry File

Written to `~/.claude/skills/dark-factory/runs/run-{YYYY-MM-DD}-{TICKET-or-EPIC}.yaml` at the end of the pipeline (or on pause/failure).

```yaml
run_id: df-{TICKET-or-EPIC}-{ISO-timestamp}
date: 2026-05-21
skill_version: v1.0
input_mode: plan
tickets: [KTP-676, KTP-679, KTP-681, KTP-680, KTP-682, KTP-683, KTP-684, KTP-685]
total_duration_minutes: 180
final_status: complete | partial | stuck | paused

phases:
  KTP-676:
    analyze:
      started: "2026-05-21T09:00:00Z"
      ended: "2026-05-21T09:05:00Z"
      duration_minutes: 5
      status: pass
      snags: []
      delegations:
        - skill: ticket-to-pr-analyst
          outcome: success
          duration_minutes: 5
    design:
      started: "2026-05-21T09:05:00Z"
      ended: "2026-05-21T09:13:00Z"
      duration_minutes: 8
      status: pass
      snags:
        - type: multi_module_mismatch
          description: "Had to scan 3 modules to find the right one"
          recovery: "Matched file paths from AC against module directories"
          severity: low
          phase: design
          ticket: KTP-676
          time_lost_minutes: 2
      delegations: []
    # ... remaining phases

gates:
  gate_1:
    between: [tier_1, tier_2]
    waited_seconds: 120
    custom_checks_passed: true
    snags: []

summary:
  tickets_complete: 7
  tickets_stuck: 1
  tickets_blocked: 0
  total_snags: 12
  snags_by_severity: { critical: 0, high: 1, medium: 4, low: 7 }
  snags_by_type:
    compile_failure: 3
    test_failure: 2
    pre_existing_bug: 2
    multi_module_mismatch: 1
    worktree_conflict: 1
    gate_timeout: 1
    spec_ambiguity: 2
  skill_delegations:
    ticket-to-pr-analyst: { invoked: 8, succeeded: 7, failed: 1 }
    klever-mr: { invoked: 7, succeeded: 6, failed: 1 }
  agent_dispatches:
    external-review-agent: { invoked: 7, succeeded: 7, failed: 0 }
    qa-agent: { invoked: 7, succeeded: 6, failed: 1 }
  phases_with_most_time_lost:
    - phase: implement
      total_time_lost_minutes: 35
      top_snag_type: compile_failure
```

### When to write telemetry

- **End of successful run:** Write complete telemetry after Phase 7 (or Phase 8 retrospective).
- **Pipeline paused (nightly shutdown, circuit breaker):** Write partial telemetry with `final_status: paused`. On `--resume`, append to the existing file.
- **Pipeline stuck (all remaining tickets stuck):** Write with `final_status: stuck`.
- **`--analyze-only` complete:** Write with `final_status: analyze_only`. Only Phase 1 data present.
- **Crash/compaction:** Sub-agents write their phase data and snags to `pipeline-state.yaml` as they go (using the structured snag format in the `failures` array). The orchestrator reconstructs telemetry from the state file if the run ends unexpectedly.

---

## Post-Run Confidence Assessment (after Phase 8 VALIDATE, before RETROSPECTIVE)

**Purpose:** Structured assessment of whether the task is actually done and whether the factory handled it well. Runs after Phase 8 VALIDATE completes (or after Phase 7 SHIP if validate is skipped). Feeds into the RETROSPECTIVE.

**Two mandatory questions, scored and justified:**

### Q1: Task Confidence (0-100)

> How confident are we that the initial task of this factory run is complete?

**Process:**
1. Score each AC individually with reasoning
2. Apply deductions for: missing execution verification, partial verdicts, untested edge cases, infra blockers, skipped phases, unresolved convergence signals
3. Compute overall task confidence (0-100)
4. Include a top-level `missing` list explaining what the gap points represent
5. Explicit recommendation: **Should we re-run the factory with the same input?** (yes/no + reasoning)
6. If score < 70: set `needs_rerun: true` in pipeline-state.yaml. The RETROSPECTIVE highlights this.

### Q2: Factory Fitness (0-100)

> How comfortable are we that the dark-factory will perform well with similar tasks in the future?

**Same 5 dimensions as the pre-run prediction** (for direct delta comparison):

| Dimension | What it measures (post-run) |
|-----------|---------------------------|
| **Spec clarity** | Were the ACs sufficient? Did ambiguity cause rework? |
| **Grill effectiveness** | Did the grill catch real issues? Were the gaps meaningful? |
| **Implementation smoothness** | How many snags, fix attempts, stuck ACs? |
| **Review quality** | Did the external review catch real bugs? False positive rate? |
| **Shipping friction** | Version bump, MR creation, Jira update: smooth or brittle? |

**Process:**
1. Score each dimension 0-100
2. For any dimension below 60: identify the specific low-hanging fruit improvement
3. **Mandatory output:** Propose a `/handoff` for each improvement identified. Standard handoff format. Write to `sessions/active/prompts/`.
4. If no improvements identified (score > 90 across all dimensions): state explicitly "No handoffs proposed. Factory handled this task type well."

### Delta Analysis (the payoff)

Compare pre-run prediction (from `eval.pre_run` in pipeline-state.yaml) vs post-run reality for each dimension:

| Classification | Condition | Signal |
|---------------|-----------|--------|
| **Over-confident** | Pre-run 85, post-run 55 | Blind spot. What was missed in the prediction? |
| **Under-confident** | Pre-run 40, post-run 90 | Unnecessary caution. What went better than expected? |
| **Calibrated** | Within 10 points | Good signal. The factory's self-awareness is accurate for this dimension. |

Over time across runs, systematic deltas reveal patterns: "The factory is always over-confident about review quality" becomes an actionable improvement signal.

### Output

**File:** `<ticket-folder>/reports/eval/post-run-eval.vN.md`

**Template:**
```markdown
# Post-Run Eval: {TICKET-KEY}

**Date:** {YYYY-MM-DD}
**Factory version:** v{X.Y.Z}

## Q1: Task Confidence — {SCORE}/100

| AC | Sub-score | Reasoning |
|----|-----------|-----------|
| AC-1 | 95 | Implemented, tested, execution verified, reviewed |
| AC-2 | 40 | Deferred to KTP-715, BQ permissions blocker |

**Deductions:**
- {-N}: {reason}

**Re-run recommendation:** {YES/NO} — {reasoning}

## Q2: Factory Fitness — {SCORE}/100

| Dimension | Pre-Run | Post-Run | Delta | Classification |
|-----------|---------|----------|-------|----------------|
| Spec clarity | 85 | 85 | 0 | Calibrated |
| Grill effectiveness | 70 | 70 | 0 | Calibrated |
| Implementation smoothness | 80 | 90 | +10 | Under-confident |
| Review quality | 75 | 55 | -20 | **Over-confident** |
| Shipping friction | 80 | 80 | 0 | Calibrated |

**Low-hanging fruit:**
- Review quality (55, delta -20): External adversarial agent needed

**Handoffs proposed:** {count}
- `sessions/active/prompts/{filename}` — {1-line summary}
```

**Pipeline-state.yaml output:**

```yaml
eval:
  post_run:
    task_confidence: 75
    missing:
      - AC-2 deferred to KTP-715, BQ permissions blocker
    factory_fitness: 72
    dimensions:
      spec_clarity:
        score: 85
        missing:
          - AC-2 referenced non-existent data field
      grill_effectiveness:
        score: 70
        missing:
          - Grill did not probe async state timing
      implementation_smoothness:
        score: 90
        missing:
          - One retry on test infrastructure
      review_quality:
        score: 55
        missing:
          - External review produced 1 false positive on ref tracking
      shipping_friction:
        score: 80
        missing:
          - GitLab project index needed manual rebuild
    needs_rerun: false
    handoffs_proposed: 1
    calibration_delta: 6
```

The `calibration_delta` is the average absolute delta across all 5 dimensions. Lower is better calibrated.

---

## RETROSPECTIVE (auto-runs after pipeline completion)

This is not a user-initiated phase. It runs automatically after all tickets complete (or all remaining are stuck/blocked). It produces the run journal AND updates the skill's cross-run intelligence.

### Process

1. **Write run telemetry** to `~/.claude/skills/dark-factory/runs/run-{date}-{ticket}.yaml`

2. **Write run journal** to `<ticket-folder>/pipeline-run-journal.vN.md` using the template below.

3. **Cross-run pattern detection:**
   Read all files in `~/.claude/skills/dark-factory/runs/*.yaml`.
   For each snag type in the current run, check:
   - Has this snag type appeared in 2+ previous runs?
   - Has the same skill delegation failed in 2+ previous runs?
   - Is there a phase that consistently takes >50% of total time?

4. **Write lesson file (if new pattern detected):**
   If a pattern meets the 2+ run threshold, write an individual lesson file:

   **File:** `<PM_ROOT>/documentation/bibliotheque/development/dark-factory/lessons/{NNN}-{kebab-slug}.md`

   ```markdown
   ---
   lesson: {N}
   title: {short title}
   source_ticket: {ticket key}
   source_date: {YYYY-MM-DD}
   status: Open
   tags: [{relevant tags}]
   aliases: [DF-L{NNN}]
   ---

   # Lesson {N}: {title}

   **Source:** {ticket key} ({date})

   ## What happened
   {narrative}

   ## Root cause
   {analysis}

   ## Fix applied
   {what changed in SKILL.md, or "monitoring"}

   ## Pattern
   {generalizable insight}
   ```

   Then update two indexes:
   - Add a row to `~/.claude/skills/dark-factory/LESSONS.md` catalog table
   - Add a row to `<PM_ROOT>/documentation/bibliotheque/development/dark-factory/lessons/INDEX.md`

5. **Update runs/INDEX.md** with a one-line entry for this run.

6. **Print retrospective summary** to user:
   ```
   Dark Factory retrospective complete.
     Run: {run_id}
     Telemetry: ~/.claude/skills/dark-factory/runs/{filename}
     Journal: {ticket-folder}/pipeline-run-journal.vN.md
     New lessons: {count} (see LESSONS.md catalog)
     Lesson files: documentation/bibliotheque/development/dark-factory/lessons/
     Recurring patterns: {list or "none detected yet"}
   ```

### Run Journal Template

Written to `<ticket-folder>/pipeline-run-journal.vN.md`:

```markdown
# Pipeline Run Journal: {TICKET-KEY or EPIC-KEY} v{N}

**Date:** {YYYY-MM-DD}
**Skill version:** v1.0
**Run ID:** {run_id}
**Input mode:** {single | list | plan}
**Duration:** {wall-clock time}
**Final status:** {complete | partial | stuck | paused}

## Ticket Summary

| Ticket | Tier | Final Status | Phases Completed | Duration | MR | Snags |
|--------|------|-------------|-----------------|----------|-----|-------|
| KTP-676 | 1 | complete | 8/8 | 45m | !123 | 1 |
| KTP-679 | 1 | stuck | 3/8 | 2h10m | n/a | 4 |

## Snag Log

| # | Ticket | Phase | Type | Severity | Time Lost | Recovery |
|---|--------|-------|------|----------|-----------|----------|
| 1 | KTP-679 | implement | compile_failure | medium | 8m | Fixed missing import |
| 2 | KTP-679 | implement | pre_existing_bug | medium | 15m | Fixed stale assertion |

## What Worked
- (concrete observations about phases or patterns that ran cleanly)

## What Was Brittle
- (fragile steps, workarounds, near-failures)

## Gate Logic
- (false positives, false negatives, timing issues with merge checks)

## Skill Delegation Report

| Skill / Agent | Type | Invoked | Succeeded | Failed | Avg Duration |
|---------------|------|---------|-----------|--------|-------------|
| ticket-to-pr-analyst | skill | 8 | 7 | 1 | 6m |
| external-review-agent | agent | 7 | 7 | 0 | 12m |
| qa-agent | agent | 7 | 6 | 1 | 10m |
| klever-mr | skill | 7 | 6 | 1 | 8m |

## Proposed Improvements
- (specific, actionable changes to SKILL.md with reasoning)

## Execution Notes
- Sub-agents spawned: {count}
- Worktree conflicts: {details}
- Gate re-checks: {count and reasons}
- Nightly shutdown: {if applicable}
- Circuit breaker triggered: {which tickets, at what phase}
```

**Be brutally honest.** The journal exists to surface friction. Diplomatic vagueness defeats its purpose.

---

## Standalone Retrospective Mode

`/dark-factory --retrospective`

No pipeline execution. Reads all accumulated telemetry and processes it for cross-run intelligence. Run this after completing a batch of work, or anytime you want to check what the factory has learned.

### Process

1. **Read all run telemetry:** `~/.claude/skills/dark-factory/runs/*.yaml`
2. **Read current LESSONS.md:** `~/.claude/skills/dark-factory/LESSONS.md`
3. **Aggregate across all runs:**
   - Total runs, total tickets processed, overall success rate
   - Snag frequency by type (sorted by count)
   - Snag frequency by phase (which phases are most problematic?)
   - Skill delegation success rates
   - Average duration per phase
   - Recurring patterns (snag types appearing in 2+ runs)
4. **Identify new lessons:** Patterns that meet the 2+ run threshold but are not yet in LESSONS.md
5. **Write new lesson files** to `<PM_ROOT>/documentation/bibliotheque/development/dark-factory/lessons/` and update both LESSONS.md catalog and the bibliothèque INDEX.md (status: `Open`)
6. **Review existing lessons:** Check if any `Open` lessons have been addressed by recent runs (fewer occurrences, or the snag type disappeared). Update status to `Monitoring` or `Resolved`.
7. **Print report:**

```
Dark Factory — Retrospective Report

Runs analyzed: {N} (from {earliest_date} to {latest_date})
Tickets processed: {total} ({complete} complete, {stuck} stuck, {blocked} blocked)

Top Snag Types:
  1. compile_failure — {N} occurrences across {M} runs
  2. test_failure — {N} occurrences across {M} runs
  3. spec_ambiguity — {N} occurrences across {M} runs

Slowest Phases (avg):
  1. implement — {N}m avg
  2. review — {N}m avg
  3. analyze — {N}m avg

Skill Delegation Health:
  ticket-to-pr-analyst: {N}/{M} success ({pct}%)
  klever-mr: {N}/{M} success ({pct}%)

Agent Dispatch Health:
  external-review-agent: {N}/{M} success ({pct}%)
  qa-agent: {N}/{M} success ({pct}%)

New Lessons Added: {count}
Existing Lessons Updated: {count}

See: ~/.claude/skills/dark-factory/LESSONS.md
```

---

## Guardrails

1. **No direct push to dev/main.** All code goes through feature branches and MRs.
2. **No destructive git operations.** No `--force`, no `--amend` on pushed commits, no rebase on shared branches.
3. **No IAM/auth changes.** Surface as blocking proposal per CLAUDE.md shipping safeguards.
4. **No Jira writes without `/post-comment`.** All external posts go through the safe pipeline.
5. **Ticket transition ceiling.** Never transition higher than "In Review" or "In Testing."
6. **Pre-existing test failures.** Fix them and attribute clearly: "Fixed pre-existing test bug: [description]."
7. **Spec fidelity.** Never add endpoints, APIs, or interfaces not explicitly covered in the spec. Never modify the spec to justify a code change.
8. **WIP commits at logical boundaries.** Uncommitted code dies with the context window.
9. **DAC repos: dev only.** Never push to `main` or `uat` on DAC repos. Phase 6 targets `dev` exclusively.
10. **Nightly shutdown awareness.** If time > 23:00 ET or registry returns 503, pause the pipeline, write state, resume via `--resume` in the morning.
11. **No phase collapsing.** Each phase (1-8) is a separate task. Never combine phases into a single task (e.g., "Phase 6-7: QA + Ship"). Phase boundaries are where enforcement happens. Merging them removes the enforcement point. KTP-713 lesson: agent collapsed Phases 6-7 and self-certified QA completion.

---

## Edge Cases

- **Single ticket, single repo:** Skip tier/gate logic. Run 8 phases directly.
- **Ticket already has analyst artifacts:** Check version, increment. Phase 1 still runs (fresh analysis may differ from stale artifacts).
- **Worktree from prior run exists:** Check cleanliness. If clean and on the right branch, reuse. If dirty or wrong branch, warn user.
- **MR already exists for branch:** `/klever-mr` handles this (updates existing MR description instead of creating duplicate).
- **Sub-agent compaction mid-phase:** Sub-agent reads `pipeline-state.yaml` on startup. The `ac_progress` field tells it where to resume within Phase 3.
- **Plan file references tickets not in Jira:** Fail fast for that ticket. Other tickets continue.
- **Mixed orgs in ticket list:** Not supported. All tickets must be in the same org. Validate prefix consistency before starting.
- **Supervisr repos (GitHub):** Phase 6 would use `gh pr create` instead of `/klever-mr`. Not battle-tested. The skill will warn: "Supervisr shipping path is experimental. Proceed with caution." and attempt `gh pr create` with standard PR format.

---

## File Map

```
~/.claude/skills/dark-factory/
├── SKILL.md                    # This file (version in frontmatter)
├── CHANGELOG.md                # Version history — every modification adds an entry
├── LESSONS.md                  # Quick-reference catalog (points to bibliothèque)
├── runs/                       # Per-run telemetry YAML files
│   ├── INDEX.md                # Run history summary
│   └── run-YYYY-MM-DD-*.yaml   # One per pipeline execution
└── evals/                      # Test cases for skill validation
    └── evals.json              # Skill-creator compatible test definitions

Bibliothèque (full lesson files, ADRs, specs):
  documentation/bibliotheque/development/dark-factory/
  ├── INDEX.md
  ├── lessons/                  # 1 file per lesson, with YAML frontmatter
  ├── architecture/             # ADRs for skill design decisions
  └── spec/                     # Planned features, deferred items
```

---

## What This Skill Does NOT Do

- Does not deploy to uat or prod (dev only, via MR merge)
- Does not trigger DAC apply jobs (human-only gate, handled by `/klever-mr` if applicable)
- Does not auto-discover epics (`--epic` deferred to v2)
- Does not estimate token cost (`--budget` deferred)
- Does not handle cross-org ticket lists
- Does not run Supervisr shipping pipeline (stubbed, not verified)
