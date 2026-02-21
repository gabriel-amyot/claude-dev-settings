---
name: supervisr-autopilot-guide
description: "Complete guide to the Supervisr Autopilot v0.2 — autonomous development orchestrator. Covers architecture, configuration, usage, customization, known limitations, and roadmap."
---

# Supervisr Autopilot — Complete Guide

## What Is It?

The Supervisr Autopilot is an autonomous orchestrator agent that takes a **Jira ticket ID** and drives it through the entire development lifecycle — from intake analysis to deployed code — with minimal human intervention.

It doesn't write code, design architecture, or make product decisions. It **spawns specialized agents** (BMAD personas) who do the work, coordinates their output through **handoff files** and **`SendMessage`** at runtime, and posts consolidated summaries to **Jira ticket comments** as a write-only audit trail.

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│  Jira Ticket │────▶│              SUPERVISR AUTOPILOT                 │
│   SPV-42     │     │                                                  │
└─────────────┘     │  Phase 0: Intake (Mary, Winston, Amelia)         │
                    │  Phase 1: PRD (Mary leads)                       │
                    │  Phase 2: Architecture (Winston leads)           │
                    │  Phase 3: Task Breakdown (Bob leads)             │
                    │  Phase 4: Implementation (dev agents, parallel)  │
                    │  Phase 5: Quality Gates (Quinn, Paige)           │
                    │  Phase 6: Tag & Ship (/supervisr-release)        │
                    │  Phase 7: Integration Check (Winston)            │
                    │  Phase 8: Deploy (HUMAN GATE)                    │
                    │  Phase 9: Closeout (promote ADRs, cleanup)       │
                    │                                                  │
                    │  ┌────────────┐                                  │
                    │  │  Observer   │ (passive, sonnet, full timeline) │
                    │  └────────────┘                                  │
                    └──────────────────────────────────────────────────┘
                                        │
                                        ▼
                              Deployed to dev
                              Jira updated
                              ADRs promoted
                              Reports archived
```

---

## Files

| File | Path | Purpose |
|------|------|---------|
| Agent definition | `~/.claude-shared-config/agents/supervisr-autopilot.md` | The orchestrator instructions (~1000 lines) |
| Configuration | `~/.claude-shared-config/agents/autopilot-config.yaml` | Tunable settings (models, personas, retry, Jira format) |
| This guide | `~/.claude-shared-config/docs/superpowers/agents/supervisr-autopilot/GUIDE.md` | Documentation and roadmap |

---

## Quick Start

### 1. Invoke the agent

From any project-management context:

```
Run the supervisr-autopilot agent on SPV-42
```

Or from a ticket folder:
```
cd ~/Developer/supervisr-ai/project-management/tickets/SPV-3/
Run supervisr-autopilot on SPV-42
```

The agent reads the Jira ticket, scaffolds the ticket folder, and begins the 10-phase pipeline.

### 2. What happens next

You don't need to do anything until **Phase 8 (Deployment)**, where the agent pauses for your explicit approval. The rest is autonomous.

If the analysis team finds **gaps in the Jira ticket** (incomplete specs, contradictory requirements, nonsensical requests), they will pause at Phase 0 and ask you to clarify before proceeding.

### 3. Monitor progress

All agent activity is posted as **Jira comments** on the ticket. You can follow along in Jira without being in the terminal. Comments use the format:

```
[autopilot:analyst] Phase 0 complete. Scope: feature. 2 services affected.
```

---

## Architecture

### Phase Overview

| # | Phase | Lead Agent | Team | Key Output |
|---|-------|-----------|------|------------|
| 0 | Intake | Mary (analyst) | analysis | Scope determination, affected services |
| 1 | PRD | Mary (analyst) | analysis | Product requirements, testable ACs |
| 2 | Architecture | Winston (architect) | analysis | Design doc, ADRs |
| 3 | Task Breakdown | Bob (scrum master) | planning | Jira sub-tickets, wave plan |
| 4 | Implementation | Dev agents | impl | Code, tests, branches |
| 5 | Quality Gates | Quinn (QA), Paige (spec) | impl | Review reports, gate verdicts |
| 6 | Tag & Ship | — (skill-driven) | ship | Tags, Docker images |
| 7 | Integration | Winston (architect) | ship | Cross-service validation |
| 8 | Deploy | — | ship | GitLab MRs, pipeline triggers |
| 9 | Closeout | — | — | ADR promotion, cleanup |

### Team Lifecycle

Teams are created and destroyed as phases progress:

```
Phase 0 ─────── Phase 2: autopilot-{TKT}-analysis  (Mary, Winston, Amelia)
                         ↓ shutdown
Phase 3: ────────────── autopilot-{TKT}-planning    (Bob)
                         ↓ shutdown
Phase 4 ─────── Phase 5: autopilot-{TKT}-impl       (Dev agents + Winston on-demand + Bob on-demand)
                         ↓ shutdown
Phase 6 ─────── Phase 8: autopilot-{TKT}-ship       (Ship agents + Winston, created at Phase 6 start)
                         ↓ shutdown
Phase 0 ─────── Phase 9: autopilot-{TKT}-observer   (passive, sonnet)
                         ↓ shutdown
```

### State Transfer

Each phase writes a `handoff-phase{N}.yaml` under `reports/status/`. This is the **contract** between phases — the next phase reads the handoff to understand what was decided and what to do.

```
handoff-phase0.yaml → scope, services, risks
handoff-phase1.yaml → PRD path, ACs
handoff-phase2.yaml → design doc, ADRs, API changes
handoff-phase3.yaml → sub-tickets, wave plan, dependencies
handoff-phase4-5.yaml → per-ticket impl status, gate results
handoff-phase6.yaml → tags, image references per service
handoff-phase7.yaml → integration validation, deploy order
handoff-phase8.yaml → deploy status, pipeline URLs
handoff-phase9.yaml → final summary, stats
```

### Scope-Based Phase Skipping

Not every ticket needs all 10 phases:

| Scope | Path | Phases Used |
|-------|------|-------------|
| **Bug** | Lean path | 0 → 1 (lean PRD) → 4-5 → 6 → 8 → 9 |
| **Feature** | Standard path | 0 → 1 → 2 → 3 → 4-5 → 6 → 7 → 8 → 9 |
| **Epic** | Full path | All phases, multiple waves in 4-5 |

---

## Human Interaction Points

The autopilot is designed for minimal human interaction. There are **two planned** pause points, plus an escalation path for blockers:

### 1. Phase 0: Intake Gaps (conditional)

If the analysis team identifies:
- **Incomplete specs** — missing acceptance criteria, unclear requirements
- **Contradictory requirements** — conflicting statements in the ticket
- **Nonsensical requests** — scope that doesn't make sense technically or business-wise
- **Insufficient context** — can't determine affected services or scope

The agent pauses and presents findings via `AskUserQuestion` (a Claude Code tool that pauses agent execution and presents a question to the user with selectable options; the agent resumes when the user responds):
```
The analysis team identified gaps in SPV-42:

1. AC #3 contradicts AC #1 (updating a field that AC #1 says should be immutable)
2. No mention of which service handles the scheduling logic
3. "Real-time" is mentioned but no latency requirements specified

How should we proceed?
- Provide clarification (you answer the gaps)
- Proceed with assumptions (agent will document assumptions and continue)
- Abort (stop the pipeline)
```

If the ticket is clear and complete, Phase 0 proceeds without asking.

### 2. Phase 8: Deployment Gate (always)

Before triggering any deployment pipeline, the agent always pauses:
```
DEPLOYMENT APPROVAL REQUIRED

Services to deploy:
| Service | Tag | Current Tag |
|---------|-----|-------------|
| lead-lifecycle-service | 0.0.9-dev | 0.0.8-dev |
| supervisor-query-service | 0.0.18-dev | 0.0.17-dev |

Type "go" to proceed.
```

### 3. Blockers (any phase, unplanned)

If an agent encounters an unrecoverable issue (git conflict, missing credentials, infrastructure failure), it:
1. Posts a Jira comment describing the blocker
2. Halts that sub-ticket (other sub-tickets continue)
3. The human reviews on their schedule — no terminal prompt, no blocking wait

This is NOT a "third human gate." It is an escalation path for genuinely stuck situations. The pipeline degrades gracefully rather than stopping entirely.

---

## Jira Communication

All runtime agent-to-agent communication uses `SendMessage`. The orchestrator posts consolidated summaries to Jira as a **write-only audit trail**. Agents never read Jira comments for coordination. This provides:
- **Observability** — you see everything in Jira without checking the terminal
- **Audit trail** — every decision is documented
- **Future-proofing** — when deployed to cloud, Jira becomes the primary interface

### Comment Frequency

The autopilot posts **consolidated, phase-level summaries** — not per-agent chatter. Expected volume:

| Scope | Estimated Comments | On Which Tickets |
|-------|--------------------|-----------------|
| Bug | 4-6 | Parent ticket only |
| Feature (3 sub-tickets) | 8-12 | Parent + sub-tickets |
| Epic (8 sub-tickets) | 15-20 | Parent + sub-tickets |

Comments are consolidated:
- **Phase summaries** on the parent ticket (one comment per phase)
- **Gate results** batched per sub-ticket (one comment with all gate verdicts, not 3 separate ones)
- **Escalations** remain granular (one comment per question/answer — these are valuable context)

### Comment Format

```
[autopilot:{role}] {message}

cc: @{recipient} (only for escalations)
```

---

## Configuration Reference

File: `~/.claude-shared-config/agents/autopilot-config.yaml`

### Models

```yaml
models:
  orchestrator: opus     # The autopilot itself
  workers: opus          # All specialized agents (Mary, Winston, Amelia, Bob, Quinn, Paige)
  observer: sonnet       # Passive process observer (cost-effective, read-only)
```

**Why opus for workers?** Autonomous development requires strong reasoning. Sonnet is fine for observation but not for making architecture decisions or writing production code.

**Cost consideration:** An autopilot run spawns multiple agents across the pipeline. Cost varies by ticket complexity, number of sub-tickets, retry cycles, and current model pricing. The observer on sonnet is cheaper than opus workers. There is no programmatic cost tracking in Claude Code — monitor usage through your API dashboard.

### Personas

```yaml
personas:
  analyst:
    name: Mary
    role: "Business Analyst — requirements, domain analysis, intake lead"
  architect:
    name: Winston
    role: "System Architect — design, ADRs, technical feasibility"
  dev:
    name: Amelia
    role: "Senior Developer — implementation, effort estimation"
  sm:
    name: Bob
    role: "Scrum Master — task breakdown, wave planning"
  qa:
    name: Quinn
    role: "QA Engineer — code review, spec validation"
  tech-writer:
    name: Paige
    role: "Spec Engineer — agent-os alignment, documentation"
```

Mary also covers the stakeholder/business perspective during Phase 0 analysis. These map to BMAD agent personas. Each agent receives their persona identity when spawned, which affects their communication style and focus areas.

**Customizing personas:** You can change the `role` description to adjust what each agent focuses on. The `name` is the BMAD persona name — changing it breaks the mapping to BMAD agent definitions.

### Phase Configuration

```yaml
phases:
  phase_0_intake:
    lead: analyst
    members: [architect, dev]
    debate_rounds: 3                          # How many rounds of cross-challenge
    human_gate_on_gaps: true                  # Pause for human if gaps found
```

`debate_rounds` controls how many rounds of cross-challenge happen during intake. More rounds = more thorough analysis, but more API cost. 2-3 is the sweet spot.

`human_gate_on_gaps` (default: true) — when the analysis team finds gaps, pause and ask the human. Set to false to always proceed with documented assumptions (not recommended for production tickets).

### Implementation Agents

```yaml
phases:
  phase_4_implementation:
    per_ticket: dev                  # Agent persona for implementers
    on_demand: [architect, sm]       # On-demand responders (not persistent listeners)
    use_bmad_dev_workflow: true      # Use BMAD dev-story workflow for implementation
```

**`use_bmad_dev_workflow`** — When true, implementation agents follow the BMAD dev-story workflow pattern from `_bmad/bmm/workflows/4-implementation/dev-story/`. This gives implementers:
- Structured task execution (tasks in order, mark complete only when tests pass)
- Built-in self-check and adversarial review steps
- File list tracking and change log updates

When false, implementers use direct code work (branch → code → test → commit).

**Note on BMAD dev agent:** The BMAD "dev" persona (Amelia) and "quick-flow-solo-dev" persona (Barry) are agent personas defined in the BMAD method (`_bmad/bmm/agents/dev.md` and `quick-flow-solo-dev.md`). They are NOT standalone skills. The autopilot spawns general-purpose agents with these personas' identity and instructions. For tactical/quick changes, Barry's quick-dev workflow is more appropriate; for feature work, Amelia's dev-story workflow is more thorough. The config controls which pattern is used.

### Retry Settings

```yaml
retry:
  impl_gate_max_cycles: 3       # Max impl→gate retries per sub-ticket
  halt_on_failure: true          # Halt ticket after max cycles (vs. force-pass)
```

The retry loop: `implement → gates → fail → re-implement → gates → fail → re-implement → gates → fail → HALT`.

After halting, the orchestrator posts a Jira comment tagging `@architect` and `@scrum-master` asking for human review. Other sub-tickets continue.

### Jira Settings

```yaml
jira:
  comment_prefix: "[autopilot"
  comment_suffix: "]"
  tag_format: "@{role}"
  consolidate_gates: true        # Batch all gate results into one comment
  phase_summaries_only: true     # Only post phase-level summaries on parent ticket
```

`consolidate_gates` — when true, all 3 gate results (code review, spec validation, spec engineer) are posted as **one** Jira comment per sub-ticket instead of 3 separate ones.

`phase_summaries_only` — when true, the parent ticket only gets one comment per phase (not per-agent activity). Sub-tickets still get detailed comments for escalations and gate results.

### Deployment

```yaml
deployment:
  human_gate: true          # ALWAYS true — deployment requires human approval
  auto_deploy: false        # Future: auto-deploy when confidence is high
```

`human_gate` should always be true in the current version. `auto_deploy` is a future flag for when the pipeline has been proven reliable enough to skip the human gate.

---

## Skill & Workflow Composition

The autopilot reuses existing skills and workflows — it never reinvents them.

| Phase | Tool Used | Type | Purpose |
|-------|----------|------|---------|
| 0, 3, 4, 5, 6, 8, 9 | `/jira` | Skill | Fetch/create tickets, post comments |
| 1 | `/create-prd` | Workflow | PRD creation |
| 2 | agent-os reads | Direct | Load specs, ADRs, contracts |
| 4 | BMAD dev-story / quick-dev | Workflow | Structured implementation (when `use_bmad_dev_workflow: true`) |
| 4 | Direct code work | Direct | Branch, code, test (when `use_bmad_dev_workflow: false`) |
| 5 | `/supervisr-review` | Skill | Standards-driven code review |
| 5 | `/supervisr-validate` | Skill | Spec and AC validation |
| 6 | `/supervisr-release` | Skill | Tag, JIB build, push |
| 6, 9 | `/push-adr` | Agent | Update agent-os specs |
| 6, 9 | `/status-index` | Skill | Completion tracking |
| 7 | Cross-service validation | Direct | Schema compat, contract alignment |
| 8 | `/gitlab` | Skill | MR creation, CI/CD vars, pipelines |

### BMAD Integration

The autopilot's personas (Mary, Winston, Amelia, Bob, Quinn, Paige) are the same BMAD personas defined in `_bmad/_config/agent-manifest.csv`. The autopilot spawns them as general-purpose agents with BMAD persona instructions.

Key BMAD workflows available to implementation agents:
- **dev-story** (`_bmad/bmm/workflows/4-implementation/dev-story/`) — structured task execution with testing gates
- **quick-dev** (`_bmad/bmm/workflows/bmad-quick-flow/quick-dev/`) — lean implementation with self-check and adversarial review
- **code-review** (`_bmad/bmm/workflows/4-implementation/code-review/`) — adversarial code review (used by Quinn in Phase 5)

---

## Escalation Protocol (Phases 4-5)

During implementation, agents communicate via `SendMessage` through the orchestrator (which posts exchanges to Jira for the audit trail):

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│ Implementer │──Jira──▶ │ Orchestrator │──Send──▶ │  Architect   │
│  (Amelia)   │         │   (relay)    │         │  (Winston)   │
│             │◀─Jira───│              │◀─Send───│  [on-demand] │
└─────────────┘         └──────────────┘         └─────────────┘
```

**How it works:**
1. Implementer sends a message to the orchestrator via `SendMessage`, tagging `@architect` or `@scrum-master`
2. Orchestrator relays the question to Winston/Bob via `SendMessage`
3. Winston/Bob responds via `SendMessage` back to orchestrator (they go idle between questions — Claude agents do NOT have event loops or background polling)
4. Orchestrator relays the response to the implementer via `SendMessage`, and posts the exchange as a Jira comment for the audit trail

**Note:** This is sequential, not concurrent. If multiple implementers need architect input at the same time, the orchestrator processes them one at a time. This is a known limitation of running in a single Claude Code session (see Known Limitations in agent definition).

**When to tag whom:**
- `@architect` — architecture question, need an ADR decision, design change
- `@scrum-master` — scope issue, need new tickets, re-prioritization
- `@peer-dev` — question for another implementer working in parallel

---

## Reports Generated

Every autopilot run produces a set of reports in the ticket folder:

```
tickets/{EPIC}/{TICKET}/
├── architecture/
│   └── adr/                              # Draft ADRs (promoted to documentation/ at Phase 9)
├── jira/
│   └── ac.yaml                           # Acceptance criteria tracking
└── reports/
    ├── architecture/
    │   ├── intake-analysis-{TICKET}-{DATE}.md
    │   ├── prd-{TICKET}.md
    │   └── design-{TICKET}.md
    ├── reviews/
    │   ├── code-review-{SUB-TICKET}-{DATE}.md
    │   ├── spec-validation-{SUB-TICKET}-{DATE}.md
    │   ├── spec-engineer-{SUB-TICKET}-{DATE}.md
    │   └── integration-gate-{DATE}.md
    ├── ship/
    │   ├── release-{SERVICE}-{TAG}-{DATE}.md
    │   └── deploy-{TAG}-{DATE}.md
    └── status/
        ├── handoff-phase0.yaml           # Handoff files live under reports/status/
        ├── handoff-phase1.yaml
        ├── handoff-phase2.yaml
        ├── handoff-phase3.yaml
        ├── handoff-phase4-5.yaml
        ├── handoff-phase6.yaml
        ├── handoff-phase7.yaml
        ├── handoff-phase8.yaml
        ├── handoff-phase9.yaml
        ├── closeout-{DATE}.md
        └── process-observations-{DATE}.md
```

---

## Customizing the Autopilot

### Adding a Custom Persona

If your team has a domain expert (e.g., a compliance specialist), add them to the config:

```yaml
personas:
  compliance:
    name: Clara
    role: "Compliance Specialist — regulatory requirements, data privacy, audit readiness"
```

Then reference them in the phase config:

```yaml
phases:
  phase_0_intake:
    members: [architect, dev, compliance]
```

The autopilot will spawn Clara as an additional analysis team member.

### Changing the Implementation Strategy

To switch from BMAD dev-story workflow to direct coding:

```yaml
phases:
  phase_4_implementation:
    use_bmad_dev_workflow: false    # Direct branch → code → test → commit
```

To use the BMAD quick-dev workflow (Barry's lean approach) instead of dev-story:

```yaml
phases:
  phase_4_implementation:
    use_bmad_dev_workflow: true
    bmad_workflow: "quick-dev"     # "dev-story" (default) or "quick-dev"
```

### Adjusting Debate Depth

For faster intake (less thorough):
```yaml
phases:
  phase_0_intake:
    debate_rounds: 1
```

For more thorough intake (slower, more expensive):
```yaml
phases:
  phase_0_intake:
    debate_rounds: 5
```

### Phase Skipping

Certain phases are skipped automatically based on scope (configured via `skip_for_scopes` in config):

```yaml
phases:
  phase_2_architecture:
    skip_for_scopes: [bug]         # Bugs skip architecture
  phase_3_task_breakdown:
    skip_for_scopes: [bug]         # Bugs skip task breakdown (single ticket)
  phase_7_integration:
    skip_for_scopes: [bug]         # Bugs skip integration (single service)
```

When Phase 3 is skipped, the orchestrator generates a **synthetic handoff** so Phase 4 can proceed (see agent definition for the schema).

### Changing Models

To run workers on sonnet (cheaper but lower quality):
```yaml
models:
  workers: sonnet
```

Not recommended for production tickets. The quality drop in architecture decisions and code generation is significant.

---

## Roadmap

### v0.1 — MVP

- [x] Agent definition with 10-phase pipeline
- [x] Configuration file with tunable settings
- [x] Jira as communication bus
- [x] Human gates at intake (conditional) and deploy (always)
- [x] 3-cycle retry loop for quality gates
- [x] Process observer (passive, sonnet)
- [x] Documentation guide

### v0.2 — Adversarial Hardening (Current)

- [x] **Config honesty** — documented that config is read as structured text (no YAML parser needed)
- [x] **Observer context budget** — explicit rule: handoff YAMLs only, never full reports
- [x] **Jira relay acknowledged** — documented as known limitation of single-session design
- [x] **skip_for_scopes added to config** — Phase 2, 3, 7 skip for bugs
- [x] **Advisory limits** — token budget guidelines in config (not enforced, no mechanism)
- [x] **Listener pattern fixed** — changed from "persistent listener" to "on-demand responder" (agents go idle between questions)
- [x] **Abort cleanup** — sub-ticket Jira comments + handoff-abort.yaml on pipeline abort
- [x] **Handoff file placement** — moved from ticket root to `reports/status/` per CLAUDE.md rules
- [x] **Bug fix path fixed** — synthetic Phase 3 handoff generated when Phase 3 is skipped
- [x] **Skill validation** — startup check for required skills, fallback path documented
- [x] **Build system detection** — config-driven build commands (Maven, Gradle, Node, Python), not hardcoded `mvn`
- [x] **Fabricated costs removed** — no more made-up dollar amounts
- [x] **Error handling aligned with Rule #1** — Rule #1 rewritten as "minimal interaction with defined escalation paths" instead of hard "2 gates"

### v0.3 — Installer & Ergonomics

- [ ] **Ticket installer skill** — `/autopilot-init {TICKET-ID}` scaffolds the ticket folder, runs Phase 0, and presents scope for approval before continuing
- [ ] **Resume from any phase** — `Run autopilot on SPV-42 from phase 4` to restart from a specific phase
- [ ] **Dry-run mode** — `Run autopilot on SPV-42 --dry-run` executes Phases 0-3 without implementation, producing a plan for review
- [ ] **Progress dashboard** — a STATUS_SNAPSHOT.yaml updater that shows real-time pipeline progress

### v0.4 — Quality & Reliability

- [ ] **Pre-existing test detection** — distinguish repo-level test failures from autopilot-introduced failures
- [ ] **Rollback protocol** — if deployment fails, automatically revert to previous tag
- [ ] **Cross-ticket dependency awareness** — when sub-ticket A depends on sub-ticket B, validate B's output before starting A
- [ ] **Gate result caching** — if a sub-ticket passes all gates and code hasn't changed, skip re-gating on resume

### v0.5 — Observability & Metrics

- [ ] **Process observer v2** — active observer that can flag anomalies in real-time (e.g., "implementer has been stuck for 10 minutes")
- [ ] **Cost tracking** — track API token usage per phase, per agent, per ticket
- [ ] **Pipeline analytics** — which phases fail most? Which agents produce the most gate failures?
- [ ] **Jira dashboard integration** — custom fields for autopilot status, phase, gate results

### v0.6 — Advanced Orchestration

- [ ] **Multi-ticket pipelines** — run autopilot on multiple tickets simultaneously with cross-ticket dependency management
- [ ] **Auto-deploy mode** — `deployment.auto_deploy: true` skips the human gate for dev environment (keep gate for uat/prod)
- [ ] **Agent memory** — persistent agent knowledge across autopilot runs (e.g., "last time Winston made this decision, here's what happened")
- [ ] **Cloud deployment** — run autopilot as a cloud service triggered by Jira webhooks

### v1.0 — Full Autonomy

- [ ] **Self-improving pipeline** — process observer analyzes patterns across runs and suggests config changes
- [ ] **Predictive scoping** — based on historical data, predict story points and wave count
- [ ] **Autonomous UAT promotion** — after dev deployment succeeds, automatically promote to UAT with appropriate gates
- [ ] **Human-free bug fixes** — for bugs with clear reproduction steps and test failures, run the full pipeline without any human gates

---

## Troubleshooting

### "The agent keeps asking me questions"

Check that `phases.phase_0_intake.human_gate_on_gaps` is `true` (not `false`). When true, the agent only asks if it finds genuine gaps. If the ticket is well-written, it proceeds silently.

If the agent is asking at Phase 8, that's expected — the deploy gate always requires approval.

### "Too many Jira comments"

Set in config:
```yaml
jira:
  consolidate_gates: true
  phase_summaries_only: true
```

### "Sub-ticket halted but I want to continue"

Re-run the autopilot on the parent ticket. It reads existing handoff files and resumes from the last incomplete phase. Halted sub-tickets can be retried.

### "Agent crashed mid-phase"

Handoff files persist the state. Re-invoke the autopilot — it detects existing handoffs and resumes.

### "I want to change the design after Phase 3"

Currently requires manual intervention: update the design doc, then re-run from Phase 4. Future versions will support `from phase N` syntax.

---

## Glossary

| Term | Meaning |
|------|---------|
| **Handoff file** | `handoff-phase{N}.yaml` — structured YAML that transfers context between phases |
| **Wave** | A group of sub-tickets that can execute in parallel (no inter-dependencies) |
| **Gate** | A quality checkpoint that must pass before proceeding (code review, spec validation, spec engineer) |
| **On-demand responder** | An agent (e.g., Winston) that the orchestrator wakes via SendMessage when tagged. Goes idle between questions — Claude agents do not have event loops. |
| **Escalation** | When an implementer needs help from the architect or scrum master — communicated via Jira comments |
| **Halt** | When a sub-ticket fails 3 gate cycles — it stops but others continue |
| **Phase skipping** | Bugs skip architecture and task breakdown phases |
| **Consolidation** | Batching multiple Jira comments into one (e.g., all gate results in one comment) |
