# Dark Factory v2 — Grounding & Decisions Record

**Session:** wise-owl
**Date:** 2026-06-01
**Status:** Discussion record. No code written. No skill modified.

This file exists to protect against hype (including the assistant's own optimism bias).
Every design claim is tiered; every accepted trade-off is recorded; the assistant's
predictions are pre-registered so the *outcome* judges, not the persuasiveness.

---

## 1. The thesis (agreed)

The current `/dark-factory` skill is a **deterministic orchestration engine written in prose**
(a 1749-line SKILL.md interpreted by a stochastic agent). Almost every hard-won lesson
(L4, L9, L11) is a "the agent talked its way past a gate" failure — a determinism leak.

The Claude Code **Workflow tool** is a real deterministic orchestration primitive that did
not exist when the skill was authored (Opus 4.6 / Claude Code 2.1.95). Moving the
orchestration *skeleton* out of prose and into a workflow script makes gates **code, not
sentences** — physically un-skippable.

**Primary reason for the rebuild (user-confirmed):** ensure no step is ever skipped, because
the skeleton is a script. This is the #1 driver, above any token or speed consideration.

---

## 2. Claim tiers

- **[VERIFIABLE]** — confirmed against the actual tool/file surface in-session.
- **[JUDGMENT]** — design opinion, could be wrong.
- **[SPECULATIVE]** — unproven payoff; must be measured.

### What the harness actually gives us (Golden Thread mapping)

| Golden Thread component | Harness provides it? |
|---|---|
| Agent Runtime / orchestration (Temporal role) | **[VERIFIABLE] Mostly yes** — Workflow tool, single-operator scale |
| Spec Engine + interrogation | **[JUDGMENT] Buildable now** as prompting/orchestration |
| Verification Harness (multi-gate, blind tests, segregation) | **[JUDGMENT] Partially** — can sequence/segregate; external gate tools still need wiring |
| Confidence Scorer (Dempster-Shafer, routing) | **[VERIFIABLE] No** — hand-build the math; workflow only provides the routing `if` |
| Governance Layer (Leash/Cedar, Vault, microVM, audit) | **[VERIFIABLE] No — none of it** |

**Deflation (accepted):** the update unlocks ~2 of 5 boxes — the orchestration spine and
segregation patterns — and **not** the two that make true "dark" (auto-merge, no human) safe.
Responsible ceiling stays **Cautious/Hold = human at the bookends.** This matches user intent.

---

## 3. Accepted trade-offs (consciously decided)

1. **Reasoning-class failures are NOT caught by this rebuild.** The workflow substrate fixes
   *compliance* (un-skippable gates), not *reasoning* (hallucinated fields, false-positive
   reviews, bad assumptions — lessons L8, L10, KTP-680 grill). **Decision:** accept as a known
   gap. Track reasoning-class failures *separately*. **Future improvement:** plug this tracking
   into Supervisr.ai (design note only; not in scope for the seed). Each reasoning-class failure
   type gets tracked as its own line item.

2. **Token cost is unsettled and must be measured.** Earlier "2-3x" claim was imprecise — it
   conflated substrate (neutral-to-cheaper) with added rigor (the real cost driver). See §4.
   **Decision:** proceed; measure substrate cost and rigor cost separately before scaling.

3. **Validation is mandatory.** We do not trust the rebuild on assertion. We build a seed, run
   one real ticket, and measure against the predictions in §5.

---

## 4. Token-cost rationale (corrected)

Two changes with opposite token effects were conflated:

- **Substrate (prose orchestration → workflow):** token-**neutral, genuinely uncertain**, NOT
  reliably cheaper (corrected per Gabriel's caching caveat). The JS skeleton burns ~0 model tokens
  and control-flow reasoning disappears — that part is free. BUT moving from *one cached growing
  context* to *many fresh sub-agent contexts* loses cross-agent cache reuse: each fresh sub-agent
  pays FULL input price for its prompt (no hit on the parent's cache), so overlapping material
  (diff/ACs/conventions) is re-paid per agent. Net could go either way; depends on overlap. Measure,
  don't assert. (Nuance: *identical sibling* agents share cache because the prefix matches —
  templated uniform prompts cache better than bespoke ones. A lever for later.)
- **Rigor (blind-impl, design deliberation + judge, multi-gate segregation, model diversity):**
  token-**positive.** More independent agents re-loading shared context (diff/ACs/conventions)
  with no shared cache. This is where any multiplier lives.

**Conclusion:** substrate ≈ flat/cheaper; rigor is a **dial, tunable per floor and per autonomy
tier.** "Go fast" floors run low rigor (cheap); "I decide" floors run high rigor (more tokens,
spent where wanted). Net effect unknown → measure (prediction #3).

---

## 5. Pre-registered, falsifiable predictions

Recorded BEFORE any build. If a prediction fails, the corresponding claim is wrong.

1. **[compliance]** Moving verdict-cap + pre-ship gate from prose into workflow code drives
   "shipped past a missing artifact / self-certified QA" to ~zero across N real runs.
   *Falsifier:* it still happens → core thesis wrong.
2. **[honest limit]** The workflow substrate does **not** reduce reasoning-class failures. If
   those drop, credit blind-test segregation, **not** orchestration.
   *Falsifier:* reasoning failures drop with no segregation change → I misattributed the cause.
3. **[cost, reframed + caching]** A *like-for-like port* (same single-pass phases on the workflow)
   costs **within ~±20%** per ticket vs. the prose skill — measured as: cache-read tokens + fresh
   input tokens + output tokens, NOT just raw totals. The open question is whether fresh sub-agent
   contexts (no parent-cache reuse) outweigh the saved orchestration-reasoning + smaller per-agent
   contexts. Added rigor (R1–R3, roadmap) costs more, proportional to rigor, opt-in per floor.
   *Falsifier:* like-for-like port costs materially more (>20%) with cache accounted for → fresh-
   context overhead dominates and the substrate is not free as claimed.

---

## 6. Governing principle (hard constraint)

**Seed, ship, build on. No monument.** User's stated failure mode: big systems built
non-incrementally become museum pieces he can't trust or use. The previous sprint succeeded
*because* it grew small and shipped (that produced the current working skill). The rebuild
inherits this constraint absolutely.

---

## 7. New beast vs. modify (resolved)

- **Form = new.** Cannot refactor a prose markdown file into a workflow script. The current
  skill's orchestration prose is replaced, not edited.
- **Knowledge = inherited.** The current skill is *tested scar tissue* (8 real tickets, 12
  lessons, hardened phase contracts, anti-patterns, tech-adaptation table). The research/brief
  is *untested vision.* The new beast = research's STRUCTURE + skill's CONTRACTS + workflow's
  DETERMINISM. **Do not discard the skill — harvest it.**
- Git versions everything; the old skill stays as the working fallback until the new one earns
  the title.
