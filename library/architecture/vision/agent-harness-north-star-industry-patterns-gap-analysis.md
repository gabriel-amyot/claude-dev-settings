# Agentic Harness Architecture

Living document consolidating research, vision, current state, and gap analysis for the agentic harness.

---

## Part 1: Industry Best Practices (Distilled)

Nine actionable patterns drawn from production agentic systems (Stripe, Vercel, Cursor, Claude Code internals, academic survey literature).

### 1. Planner-Worker-Judge Architecture

Decompose into specialized roles. The Planner scopes subtasks with acceptance criteria. The Worker executes in isolation with curated context. The Judge evaluates output against criteria. Never give one agent both implementation and verification. This separation is the single highest-leverage pattern for output quality.

### 2. Dynamic Context Discovery

Three tiers of context, each with distinct lifecycle:

- **Static:** Immutable system prompt. Ruthlessly minimized. Only identity, safety rails, and tool schemas.
- **Dynamic:** Retrieved on demand via search, grep, file reads. Assembled per-task by a curator (not the worker).
- **Persistent:** Version-controlled project intent docs (CLAUDE.md, agent-os specs, ADRs). Survives across sessions via filesystem.

Static context must be the smallest possible. Every byte has opportunity cost.

### 3. Deterministic Gates over Probabilistic Prompts

Hard-coded checkpoints (schema validation, linter runs, security scans) enforced in runtime, not system prompts. The LLM is probabilistic and cannot guarantee compliance. Code gates block unauthorized changes. Phase transitions gated by scripts, not by asking the LLM "did you check everything?"

### 4. Surgical Tool Curation

10 to 15 primitives max per agent context. Curated subsets reduce token waste and improve tool selection accuracy. Domain capabilities abstracted as Skills retrieved via dynamic discovery. Agents should not see tools they will never use for their assigned task.

### 5. Pre-flight Heuristics

Fast local checks before expensive LLM inference: repo cleanliness, credential freshness, network reachability, disk space, Docker daemon status. Catches setup errors before tokens are consumed. Pre-flight is a script, not a prompt instruction.

### 6. Self-healing with Hard Caps

Stripe's 2-retry model: if the model cannot fix it in 2 to 3 attempts, a third is statistically unlikely to succeed. Capped self-healing prevents token burn. Escalate to human on cap breach. Retry counts must be script-tracked, never LLM-tracked.

### 7. Tiered Execution

- **Tier 0:** Structured output. Concise, typed, schema-validated.
- **Tier 1:** Large-result eviction. Write to file, return handle. Keeps context window clean.
- **Tier 2:** Programmatic tool calling. Sandboxed code execution bypasses context window entirely.

### 8. Evolutionary Harnesses

Meta-agent synthesis: a secondary agent ingests execution metrics (scorecards, error logs, timing data) and synthesizes architectural rules. Active learning captures human overrides and execution preferences. The harness improves itself based on data, not intuition.

### 9. External Working Memory

Filesystem as primary working memory. Large outputs go to artifact files, referenced by handles. Context summaries written to disk before compaction. Agents search history files for specific details rather than carrying raw material across phases.

---

## Part 2: Gab's Theoretical Vision (Distilled)

Seven principles that shape the harness design, drawn from hands-on experience across 5 night-crawls, 3 dev-crawls, and daily interactive sessions.

### 1. Semantic Code Intelligence

Universal-ctags combined with ripgrep for cross-file symbol navigation. Tree-sitter for single-file structural editing. JDT.LS only when type resolution is needed. A `search-symbol.sh` wrapper formats output as condensed indexed lists that fit agent context windows. The goal: agents navigate codebases like senior engineers, not keyword searchers.

### 2. Linters as Architecture Guardrails

ArchUnit tests encode architectural boundaries as executable code. PMD and SpotBugs produce machine-readable JSON/SARIF. Linter results feed directly into agent context with no human interpretation needed. Architecture rules are physical barriers, not guidelines that can be ignored.

### 3. Multi-model Routing

Route sub-tasks to cost-optimal model. Opus for architecture decisions and adversarial review. Sonnet for code fixes and implementation. Haiku for summarization and context compression. Already partially implemented in dev-crawl's model assignment table. The routing decision is made by the orchestrator, not the worker.

### 4. BMAD Multi-agent Workflows

Battle-tested personas produce higher-quality output than solo execution:

| Persona | Role | Strength |
|---------|------|----------|
| Winston | Architect | System design, spike analysis, ADR authoring |
| Amelia | Developer | Implementation, harness scripts, code quality |
| Quinn | QA | Adversarial review, gap detection, test coverage |
| Murat | Test Architect | Service code changes, integration testing |

Structured debate across personas surfaces blind spots that solo agents miss consistently.

### 5. Token Economics

Context is a first-class constraint. Every byte in the context window has opportunity cost. Delegate deep work to subagents that return condensed summaries (1 to 2k tokens). Progressive disclosure: read the index first, then selectively load only what the task requires. Never bulk-load.

### 6. Guardrails Encode Architecture

Physical barriers, not guidelines. The write-scorecard script validates JSON before touching YAML. The ralph-loop script tracks retries, not the LLM. Pre-flight is a script, not a prompt instruction. If a rule matters, it is enforced by code. If it is only in a prompt, it will eventually be violated.

### 7. The State Machine Philosophy

LLMs are for probabilistic thinking and routing. Scripts are for deterministic execution. Phase transitions are script-triggered. The harness operates as a state machine where transitions automatically trigger deterministic scripts (linters, pre-flight, closeout). LLMs must never be relied upon to remember to run standard processes. If the LLM has to remember it, it will eventually forget it.

---

## Part 3: Current State Inventory

### Agent Inventory (15 agents)

**Orchestrators (5):**

| Agent | Purpose | Maturity |
|-------|---------|----------|
| night-crawl | Autonomous overnight execution with BMAD team | Most mature. 5 runs. |
| dev-crawl | ASSESS through VERIFY state machine, handles GCP deployment | 3 runs. Escalation gaps. |
| supervisr-autopilot | Full ticket lifecycle: intake through shipping | Early. |
| bmad-party-autopilot | Autonomous multi-persona structured debate | Functional. |
| supervisr-ship | Shipping pipeline orchestration | Functional. |

**Executors (10):**

| Agent | Purpose |
|-------|---------|
| test-harness-driver | Boot harness, run tests, gap diff |
| pickup-ticket | Ticket intake and initialization |
| push-adr | Promote ADRs from ticket to global docs |
| post-comment | External post pipeline with templates |
| review-responder | Research and draft PR review responses |
| pr-response-sweep | Autonomous sweep of all open PR comments |
| supervisr-github-review | GitHub PR review automation |
| bmad-party | Interactive multi-persona debate |
| mother-base-housekeeper | Documentation and index maintenance |
| night-crawl | Also acts as executor in non-autonomous mode |

### Skill Inventory (40+ skills)

| Category | Skills |
|----------|--------|
| Workflow orchestration | ralph-loop-preflight, pre-ship-check, supervisr-release, supervisr-review, supervisr-validate |
| Knowledge management | index-context, status-index, tribal-knowledge, archive, ticket-init |
| External integrations | jira, gitlab, gcloud, slack-*, post-comment |
| Code quality | adversarial-review, pr-review, push-adr |
| BMAD | bmad-debrief, gab-operationalize |
| Utilities | morning-brief, estimate, location-scraper, peon-ping-* |

### Execution Patterns (5)

1. **Ralph-loop:** Iterative self-referential loop via stop hook. The most primitive iteration mechanism. Reliable.
2. **Night-crawl:** Interactive planning phase followed by autonomous execution with BMAD team. Most mature pattern.
3. **Dev-crawl:** ASSESS, PLAN, EXECUTE, DEPLOY, VERIFY, DIAGNOSE state machine. Handles GCP deployment well but has escalation gaps.
4. **Supervisr-autopilot:** Full ticket lifecycle from intake through PRD, architecture, implementation, QA, and shipping.
5. **BMAD party:** Multi-persona structured debate, available in both interactive and autonomous modes.

### Battle-test Status

5 night-crawls, 3 dev-crawls, 3 ralph-loops completed. Night-crawl is the most mature pattern.

### What Works

- BMAD team composition produces consistently better output than solo agents.
- Ralph-loop stop hook is reliable for iteration control.
- State files on disk survive context compaction.
- WIP commits preserve work across session boundaries.
- Pre-flight catches configuration issues before token waste.

### What's Broken or Missing

| Issue | Impact |
|-------|--------|
| No automated observability | Scorecard is manual or nonexistent. No trend data. |
| No fallback matrix | GitLab down equals dead stop. No degraded-mode operation. |
| Night-crawl and dev-crawl duplicate iteration logic | Should be ralph-loop profiles, not separate engines. |
| No context eviction mechanism | Agents self-monitor for context size. Unreliable. |
| No hard caps on sub-agent retries | LLM-tracked retry counts. Unreliable. |
| No curator role | Workers curate their own context. Wasteful and inconsistent. |
| No responsibility boundaries on agents | Unclear ownership leads to overlap and gaps. |
| No human escape hatch | Ctrl+C kills everything with no recovery. No graceful degradation. |

---

## Part 4: North Star

Seven dimensions that define the target state for the agentic harness.

### A. Orchestration Fidelity

Every crawl runs through ralph-loop as THE primitive. Night-crawl and dev-crawl are profiles (configuration), not separate iteration engines. Single state machine, single closeout path. Adding a new crawl type means adding a profile file, not writing a new orchestrator.

### B. Observability

Every crawl automatically produces a scorecard entry. The scorecard captures: tasks attempted, tasks completed, tokens consumed, errors encountered, escalations triggered, wall-clock time. Trend analysis triggers after 5 entries. Zero manual data entry. Schema versioned from day 1.

### C. Resilience

Known failures have documented fallbacks. Pre-flight detects conditions; the crawl profile declares severity per condition.

| Condition | Night (autonomous) | Day (interactive) |
|-----------|-------------------|-------------------|
| GitLab down | WARN. Fall back to local commits. | WARN. Notify user. |
| Docker down | FATAL. Abort. | FATAL. Abort. |
| Jira unreachable | WARN. Skip updates. | WARN. Notify user. |
| Disk space low | FATAL. Abort. | FATAL. Abort. |

No dead stops on recoverable failures.

### D. Context Intelligence

A Curator agent assembles task-specific context before worker assignment. Workers never curate their own initial context. Context eviction is a physical boundary: a script-triggered Haiku summarizer compresses context when token count exceeds threshold. Eviction is deterministic (triggered by measured token count), not probabilistic (triggered by the LLM noticing it is running out of space).

### E. Deterministic Gates

Phase transitions trigger deterministic scripts. Linters, pre-flight, closeout, and scorecard writes are all scripts executed by the harness runtime. LLMs think and route; scripts execute. If a gate fails, the phase transition is blocked. The LLM cannot override a gate.

### F. Agent Boundaries

Every orchestrator has an explicit Responsibility Boundary document:

- **Owns:** what this agent is solely responsible for.
- **Delegates to:** which agents it spawns and for what.
- **Escalates to:** when and how it hands off to a human or higher-level orchestrator.
- **Must not:** explicit prohibitions (e.g., "must not modify production config").

Sub-agent retries are hard-capped at 3 strikes, tracked by script. On cap breach, the orchestrator escalates rather than retrying.

### G. Improvement Loop

Scorecard data feeds meta-analysis. After every 5 crawls, a meta-agent reviews scorecards and proposes harness changes. The loop: Scorecard (automatic) then trend analysis (meta-agent) then harness change proposal (human-approved) then implementation. The harness improves itself based on data, not intuition. Schema versioned from day 1 so historical data remains comparable.

---

## Part 5: Gap Analysis

| Dimension | Current State | North Star | Gap Severity | Phase |
|-----------|--------------|------------|-------------|-------|
| **A. Orchestration Fidelity** | Night-crawl and dev-crawl are separate engines with duplicated iteration logic. Ralph-loop exists but is not the universal primitive. | All crawls are ralph-loop profiles. Single state machine, single closeout path. | CRITICAL | 1 |
| **B. Observability** | No automated scorecard. Manual or nonexistent. No trend data. | Every crawl produces a scorecard entry automatically. Trend analysis after 5 entries. Zero manual data entry. | CRITICAL | 1 |
| **C. Resilience** | No fallback matrix. GitLab down equals dead stop. No degraded-mode operation. | Known failures have documented fallbacks with severity per crawl profile. No dead stops on recoverable failures. | HIGH | 2 |
| **D. Context Intelligence** | Workers curate their own context. No eviction mechanism. Self-monitoring is unreliable. | Curator assembles context before worker assignment. Script-triggered eviction based on measured token count. | HIGH | 2 |
| **E. Deterministic Gates** | Pre-flight exists and works. Phase transitions are partially script-gated. Linter integration is conceptual. | All phase transitions gated by deterministic scripts. Linters, closeout, scorecard are all script-enforced. LLMs cannot override gates. | MEDIUM | 2 |
| **F. Agent Boundaries** | No explicit responsibility boundaries. No hard caps on retries. LLM-tracked retry counts. Unclear agent ownership. | Every orchestrator has Owns/Delegates/Escalates/Must-not. 3-strike hard cap, script-tracked. | HIGH | 1 |
| **G. Improvement Loop** | No scorecard data to analyze. No meta-agent. Harness changes driven by intuition and post-mortems. | Scorecard feeds meta-analysis every 5 crawls. Schema versioned. Data-driven harness evolution. | MEDIUM | 3 |

### Phase Summary

- **Phase 1 (Foundation):** Orchestration fidelity, observability, agent boundaries. These are prerequisites for everything else. Without scorecard data, no improvement loop. Without ralph-loop unification, no consistent closeout. Without agent boundaries, no reliable delegation.
- **Phase 2 (Intelligence):** Resilience, context intelligence, deterministic gates. These make the harness robust and efficient. Fallback matrix prevents dead stops. Curator prevents context waste. Script gates prevent compliance drift.
- **Phase 3 (Evolution):** Improvement loop. Requires Phase 1 (scorecard data exists) and Phase 2 (harness is stable enough to evolve). Meta-agent synthesizes rules from execution history.
