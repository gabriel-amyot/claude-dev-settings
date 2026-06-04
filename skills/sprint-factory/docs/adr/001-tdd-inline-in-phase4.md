# ADR-001: TDD as Inline Steps in Phase 4, Not Sub-Phases

**Status:** Accepted
**Date:** 2026-05-27
**Source:** KTP-682 post-implementation test gap analysis
**Deciders:** Gabriel Amyot

## Context

KTP-682 (adding a `country` parameter to 7 BQ adapters) exposed a fundamental weakness in the Dark Factory's code-first Phase 4. Tests written after implementation confirmed the code's behavior rather than specifying it. A deliberately adversarial test ("what happens when country is null?") failed immediately, exposing a regression that every post-hoc test missed. TDD would have caught it at RED.

The decision was to integrate TDD into Phase 4. Two structural options were considered.

## Options

### Option A: Inline replacement (chosen)

Replace Phase 4's per-AC implementation step with a RED-GREEN-REFACTOR loop. The existing AC-by-AC sequential structure stays. Baseline tests, RED-GREEN, and adversarial tests are steps within the same loop or follow it. Phase numbering (5, 6, 7, 8) does not change.

### Option B: Sub-phases (4a, 4b, 4c, 4d)

Split Phase 4 into sub-phases: 4a = baseline tests, 4b = RED-GREEN per AC, 4c = adversarial edge-case tests, 4d = execution verification. Each sub-phase has its own purpose, gate, and instructions.

## Decision

Option A: inline replacement.

## Rationale

The deciding factor was the **baseline interleaving constraint**. Baseline tests (verifying current behavior before changing it) must run immediately before each AC's implementation, not as a batch. If AC-1's code changes break AC-2's baseline, a batch approach (all baselines in 4a, then all implementations in 4b) loses the guarantee that each baseline reflects the true pre-change state.

Baseline and RED-GREEN are interleaved per AC:

```
baseline(AC-1) -> red-green(AC-1) -> baseline(AC-2) -> red-green(AC-2) -> ...
```

Calling them separate sub-phases misrepresents the execution order. The adversarial tests (post-loop) and execution verification (post-loop) could genuinely be separate stages, but splitting only those creates an inconsistent structure: some sub-phases are per-AC, others are post-loop.

Additional factors:
- No disruption to pipeline-state.yaml, resume logic, or downstream phase references.
- TDD is not a separate activity from implementation. It IS implementation. The structure should reflect this.
- Phase 4 gets longer (~120 lines) but the complexity is linear (more steps in the same loop), not structural (new state model, new resume points, new phase references).

## Consequences

- Phase 4 is the longest section in SKILL.md. Mitigated by clear section headers within the phase.
- No granular resume point within the TDD cycle (RED vs GREEN). If the agent dies mid-AC, resume restarts that AC. Acceptable because one AC's TDD cycle is minutes, not hours.
- Downstream phases (5, 6, 7, 8) reference "Phase 4" without ambiguity.
