# ADR-001: Orchestrate Dark Factory with the Workflow tool, not prose

**Status:** Accepted (2026-06-01, Gabriel)
**Date:** 2026-06-01
**Session:** wise-owl
**Home:** `~/.claude/skills/dark-factory/` (new skill dir; v1 kept intact as working fallback + benchmark baseline)
**Seed ticket:** KTP-728
**Deciders:** Gabriel (lead), assistant (analysis)
**Supersedes:** the prose-orchestration model of `~/.claude/skills/dark-factory/SKILL.md` (v1.6.0)

---

## Context

`/dark-factory` is Gabriel's main development flow. It was authored under Opus 4.6 / Claude Code
2.1.95, when no deterministic multi-agent orchestration primitive existed. Its 8-phase pipeline,
tier logic, gates, state persistence, and polling are all expressed as ~1749 lines of natural
language that a single stochastic agent reads and manually performs.

The skill's own evolution (CHANGELOG 1.0→1.6, LESSONS L1–L12) is a record of *determinism leaks*:
the agent rationalizing past "mandatory" gates (L4, L9, L11). The eventual fixes reached for
mechanical enforcement — a shell pre-ship gate and a PostToolUse hook — because prose enforcement
kept failing.

The current Claude Code harness provides a **Workflow tool**: deterministic JS orchestration
(`phase`/`parallel`/`pipeline`/`agent` with schema-validated output, budget, journaling, resume).
This is the primitive the skill was hand-emulating in prose.

A months-long research corpus (the "Golden Thread" product brief) describes a full enterprise
factory (Temporal.io, Firecracker microVMs, Leash/Cedar governance, Dempster-Shafer scoring). The
harness provides only the orchestration spine of that vision, not the governance/isolation infra.

## Decision

Rebuild the orchestration **skeleton** of Dark Factory as a **Workflow script**, while **harvesting
the current skill's phase contracts, anti-patterns, and 12 lessons** as the prompts handed to the
workflow's agents. Gates become JS conditionals (un-skippable), not prose instructions.

Scope the first build to a **seed**: one workflow spine + one floor + one real ticket, like-for-like
(no added rigor), with the human-in-the-loop concierge gate proven via workflow pause/resume.
(See `reports/02-seed-spec-onepager.md`.)

### Primary rationale

**Ensure no pipeline step is ever skipped.** Because the skeleton is a script, the gates execute
deterministically and the agent cannot rationalize past them. This is the decisive reason, above
token cost or speed.

## Consequences

### Positive
- Compliance-class failures (skipped gates, self-certified QA) become structurally impossible.
- Substrate is token-neutral-to-cheaper (deterministic skeleton burns ~0 model tokens; clean
  short-lived agent contexts beat one growing orchestrator context).
- Phase handoffs become schema-validated objects, not parsed free text.
- Native resume/journaling replaces the hand-rolled `--resume` + pipeline-state.yaml backbone.

### Negative / accepted gaps
- **Reasoning-class failures are NOT addressed** (hallucinated fields, false-positive reviews, bad
  assumptions). Accepted as a known gap; tracked separately; future Supervisr.ai integration to
  plug it. The substrate fixes compliance, not reasoning.
- **No true "dark" / auto-merge.** The governance + isolation infra (Leash/Cedar, microVMs, Vault,
  confidence math) is out of reach. Responsible ceiling = Cautious/Hold, human at the bookends.
  (Consistent with Gabriel's intent to remain the deciding engineer.)
- **Human gates need a new shape.** Background workflows cannot call `AskUserQuestion`; gates must
  pause→surface→resume. This is the seed's highest-risk unknown.
- **Token cost unsettled.** Added rigor (blind-impl, deliberation, multi-gate) costs more; it is a
  per-floor/per-tier dial, opt-in, and must be measured (prediction #3).
- Betting the main dev flow on a young primitive; mitigated by keeping the v1 prose skill as the
  working fallback until v2 earns the title.

### Neutral
- Git versions both; v1 is not deleted. v2 grows seed-first per the governing principle
  ("seed, ship, build on — no monument").

## Validation

This ADR is provisional until the seed runs one real ticket and reports against the three
pre-registered predictions in `reports/01-grounding-and-decisions.md`. A failed prediction reopens
this decision.

## Promotion

If accepted and validated, promote to the dark-factory skill's own ADR location
(`~/.claude/skills/dark-factory/docs/adr/` or the bibliothèque dark-factory architecture folder).
