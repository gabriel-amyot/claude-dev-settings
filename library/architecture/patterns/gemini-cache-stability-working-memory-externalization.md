Architectural Blueprint: Custom Agentic Harness
1. Executive Summary
This document outlines the architecture for a production-grade agentic harness. The core philosophy is that the model-tool loop itself is a commodity; the system's value, performance, and reliability stem entirely from context engineering, durable state management, deterministic policy enforcement, and externalized memory. The harness must treat the Large Language Model strictly as a reasoning control plane while managing all state, execution boundaries, and safety protocols internally.

2. Core Architectural Principles
Cache Stability First: The architecture must prioritize prompt caching by maintaining stable prompt prefixes, append-only conversation histories, and fixed tool catalogs per execution session.

Working Memory Externalization: To prevent the model from drowning in its own history, large tool outputs, intermediate plans, and recovered states must reside in the local filesystem or artifact store and be referenced by the model strictly via file handles.

Small Action Space: The built-in capability surface should be restricted to high-leverage primitives (e.g., file operations, search, isolated code execution, and subagent delegation).

Deterministic Governance: Operational guardrails must be enforced in the runtime environment through deterministic code gates, not probabilistic system prompts.

3. System Layers & Components
3.1. Context & Memory Management
Dynamic Context Discovery: Instead of statically injecting all instructions, the system should allow the agent to pull relevant instructions, schemas, or domain knowledge dynamically when triggered by specific tasks.

Large-Result Eviction (Tier 1 Execution): When a tool returns a massive payload (e.g., heavy JSON responses or large terminal traces), the harness must write the full output to an artifact file and return only a truncated summary, a stable file path, and search tools (like grep or jq) to the agent.

Programmatic Tool Calling (Tier 2 Execution): For tasks that involve looping over many entities or transforming large datasets, use sandboxed code execution. This keeps the intermediate data transformations strictly inside the container, bypassing the model's context window entirely.

3.2. Capability Surface (Tools & Skills)
Primitives vs. Skills: Core primitives (read, write, search, shell) are built into the baseline harness. High-level domain capabilities (e.g., specific framework configurations or deployment workflows) are structured as isolated "Skills" (files bundling instructions and scripts) that are retrieved via deferred loading only when necessary.

Namespacing & Structured Outputs: Tools must be explicitly namespaced to prevent the model from hallucinating overlapping parameters. Tool results must default to structured, strictly typed outputs (Tier 0 execution) to reduce downstream cognitive load on the agent.

3.3. Intent Governance Layer
Context Resonance Enforcement Protocol (CR-EP): Maintain a version-controlled CONTEXT.md file at the root of the project to define the operational "Why" and absolute "Hard Lines" (e.g., security policies, schema immutability).

Deterministic Code Gates: Implement hard-coded checkpoints such as schema validation algorithms, pre-commit hooks, and static security scans that automatically block execution if constraints are violated.

Pre-Flight Checklist: Before initiating unattended outloop tasks, the harness must run a deterministic checklist. This includes scanning for Personally Identifiable Information (PII), verifying network connectivity to management environments, and confirming required credentials to catch setup errors before tokens are consumed.

3.4. Multi-Agent Orchestration
Context Isolation: Subagents should not be used arbitrarily; they should be spawned exclusively to provide pristine, isolated context windows for parallel exploration or specialized tooling, mitigating attention collapse.

Planner-Worker-Judge Topology: For hierarchical tasks, use a Planner to decompose the overarching objective, deploy isolated Workers to execute narrowly scoped sub-tasks, and utilize a deterministic Judge to evaluate the final outputs against the Planner's exact criteria.

3.5. Outloop Performance & Reliability
Execution Sandboxing: Tools must execute in environments with strict filesystem roots, CPU/memory limits, and optional no-network isolation modes. Secrets must never enter the model's context; they should be securely injected during tool execution and aggressively redacted from the resulting payloads.

Capped Self-Healing: Implement Selective Continuous Integration (CI) that only runs tests relevant to the specifically changed files. If tests fail, feed terminal traces back to the agent for self-healing, but enforce a strict, hard-coded cap (e.g., a maximum of two CI retry rounds) to prevent token waste from hallucinated, cascading fixes. If the threshold is breached, the harness must suspend operations and surface the state to a human engineer.

Let me know if your team needs further clarification on specific architectural patterns or implementation details for any of these layers.