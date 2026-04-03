# Agentic Harness Evolution Roadmap

## Phase 1: Ralph-Loop Primitive + Observability (2-4 weeks)
Goal: Make ralph-loop THE execution model. Add automated observability. Wire pre-flight. Add human escape hatch.

### 1.1 Ralph-Loop as THE Primitive
- Create crawl profiles (night-crawl.yaml, dev-crawl.yaml)
- Refactor agent definitions (strip iteration logic)
- Update ralph-loop plugin to read profiles
- Invocation: `/ralph-loop --profile night-crawl --ticket SPV-3 --max-iterations 7`

### 1.2 Human Escape Hatch (SIGINT Protocol)
- SIGINT trap -> RECOVERY.md dump
- Cleanup routine (graceful child termination, lockfile cleanup)
- Resume options: resume, edit, skip-gate, abort
- API history serialization for conversation trajectory preservation

### 1.3 Automated Scorecard
- `write-scorecard.sh` validates JSON, appends YAML safely (flock)
- Schema versioned from day 1 (`schema_version: "1.0"`)
- Agent produces JSON payload, script writes safely
- Run manifest per crawl in `tickets/{ID}/reports/status/`

### 1.4 Pre-flight Curator (Quartermaster)
- `curator.sh` fetches task-relevant files via search-symbol.sh and ticket AC
- Builds minimal context payload for workers
- Dynamically provides task-relevant tools only

### 1.5 3-Strike Hard Cap
- Script-tracked attempt counter, not LLM-tracked
- Escalation per crawl profile on cap hit
- Sub-agent metrics in scorecard

### 1.6 Universal Pre-Flight Skill
- Repo cleanliness, Docker health, credentials, disk space, network, agent definitions
- Severity levels derived from crawl profile (not static)
- Fallback matrix integration

### 1.7 Fallback Matrix + Failure Catalog
- failure-catalog.yaml with detection/fallback/affects
- Crawl profiles reference catalog entries with severity overrides

### 1.8 Agent Responsibility Boundaries
- Owns / Delegates to / Escalates to / Must not sections on all orchestrators

### Dependencies

```
1.1 Ralph-Loop Primitive
 |
 +---> 1.3 Automated Scorecard (needs loop events)
 |      |
 |      +---> 1.5 3-Strike Hard Cap (needs scorecard writes)
 |
 +---> 1.2 SIGINT Protocol (needs loop control)
 |
 +---> 1.4 Pre-flight Curator (needs profile definitions)
        |
        +---> 1.6 Universal Pre-Flight (extends curator)
               |
               +---> 1.7 Fallback Matrix (extends pre-flight)

1.8 Responsibility Boundaries --- independent, can start immediately
```

### Verification Criteria
1. `ralph-loop --profile night-crawl` launches through primitive
2. Scorecard entry written automatically after each sub-agent completes
3. Ctrl+C drops to terminal with RECOVERY.md written
4. `/pre-flight` catches simulated failure (e.g., Docker down, stale credentials)
5. GitLab-down scenario pivots to local-only mode per fallback matrix
6. All orchestrators have a Responsibility Boundary section

## Phase 2: Semantic Tools + Data-Driven Improvement (4-8 weeks)
Goal: Replace brute-force context loading with semantic retrieval. Use crawl telemetry to drive harness improvements automatically.

### 2.1 Semantic Code Search
- Replace grep-based code discovery with AST-aware symbol search
- Index repos on first use, incremental updates on file change
- Expose as a tool primitive: `search-symbol --type function --name handleDisposition`

### 2.2 Dynamic Context Discovery
- Agent pulls relevant CLAUDE.md rules, ADRs, and contracts only when triggered by task domain
- Replaces static bulk-loading of all project instructions
- Measured by: context tokens consumed per successful task (target: 40% reduction)

### 2.3 Crawl Telemetry Pipeline
- Structured event stream from ralph-loop (task start/end, token usage, tool calls, errors)
- Persisted to `tickets/{ID}/reports/status/telemetry/` per crawl
- Dashboard-ready YAML/JSON format

### 2.4 Meta-Agent Synthesis
- Async meta-agent ingests telemetry after each crawl
- Identifies repeated failure patterns, token waste hotspots, tool selection errors
- Outputs proposed rule updates to a staging area for human review

### 2.5 Selective CI Integration
- Map changed files to affected test suites automatically
- Run only impacted tests during self-healing loops
- Reduces CI round time from full-suite to targeted subset

### 2.6 Large-Result Eviction
- Intercept tool outputs exceeding token threshold
- Write full payload to artifact file, return summary + file handle + search tools
- Agent uses grep/jq against artifact file for surgical extraction

### 2.7 Programmatic Tool Calling (Tier 2)
- For bulk data manipulation, agent generates transformation logic
- Harness executes in sandboxed container, returns structured result
- Keeps intermediate data outside context window entirely

## Phase 3: Cloud + Multi-Model (8+ weeks, vision only)
Goal: Break free from single-machine, single-model constraints. Enable cloud-hosted sandboxes and model routing.

### 3.1 Cloud Sandbox Environments
- Disposable, pre-warmed devboxes (target: 10-second spin-up)
- Full isolation: filesystem roots, CPU/memory limits, no-network modes
- Cattle-not-pets: standardized, reproducible, ephemeral

### 3.2 Model Routing
- Route sub-tasks to optimal model based on task type and cost profile
- Haiku for summarization and triage, Sonnet for code generation, Opus for architecture
- Routing rules defined in crawl profiles

### 3.3 Secret Management Layer
- Secrets injected at tool execution layer only, never in model context
- Aggressive redaction from tool return payloads
- Cryptographic approval gates for CRITICAL operations

### 3.4 Continuous Active Learning
- Log all human overrides, failed heuristics, preference signals
- Synthesize into persistent architectural rules automatically
- Staleness detection: flag when code commits drift from recorded intent

### 3.5 Latent Space Monitoring (Experimental)
- Monitor attention patterns for cognitive drift during long contexts
- Detect attention collapse before it causes execution failures
- Trigger context refresh or sub-agent delegation proactively

### 3.6 Cross-Organization Harness Sharing
- Portable crawl profiles and failure catalogs across orgs
- Shared tool libraries with org-specific overrides
- Federated telemetry for cross-project pattern detection

## Execution Sequence

Start with these steps in order. Each step unlocks the next.

1. **Crawl profiles** (1.1) — define night-crawl.yaml and dev-crawl.yaml with task lists, model assignments, severity overrides
2. **Ralph-loop reads profiles** (1.1) — refactor plugin to consume profile format
3. **SIGINT protocol** (1.2) — trap, dump, cleanup, resume
4. **Automated scorecard** (1.3) — write-scorecard.sh, schema v1.0, flock safety
5. **3-strike hard cap** (1.5) — script-tracked counter wired to scorecard
6. **Pre-flight + curator** (1.4, 1.6) — quartermaster builds context, pre-flight validates environment
7. **Fallback matrix** (1.7) — failure-catalog.yaml wired to crawl profiles with severity overrides
