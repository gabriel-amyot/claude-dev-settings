# STE Anti-Slop — Design Spec

- **Date:** 2026-07-30
- **Owner:** Gabriel Amyot
- **Scope:** User-level harness (`~/.claude-shared-config/`)
- **Status:** Implemented 2026-07-30 (both layers live). The hard gate shipped as **slop-subset, zero tolerance** (not the phased advisory-first plan) per the calibration finding — see `2026-07-30-ste-calibration.md`. Grammar/voice checks are advisory; the six AI-slop patterns block. Tune via `evals/ste/gate_benchmark.py`.
- **Source material:** woosal1337/blog `videos/ep01-the-cure-for-ai-slop` — ships `ste-lint.py` (deterministic linter) and `ste-writing-skill.md` (ASD-STE100 subset, strict + flavored modes). Published result: −74% violations on Claude.

## Problem

AI text drifts into six recurring slop patterns: synonym rotation, hedging, frozen verbs (nominalizations), marketing adjectives, run-ons, and phrasal verbs. Two costs:

1. Every response to Gab carries the drift.
2. External artifacts (Jira/PR/Slack comments, MR descriptions, 3Ps) publish the drift where teammates and vendors read it.

The fix is a controlled subset of ASD-STE100 Simplified Technical English, applied as two layers: a behavioral rule for all output, and a deterministic linter that gates on-disk external drafts.

## Goals

- Reduce slop measurably (target: reproduce woosal's ~−74% on Gab's own corpus).
- Enforce, not hope: a hard gate on sensitive external artifacts.
- Zero false-positive blocks on legitimate software/adtech vocabulary.
- A test suite and a per-post improvement metric.

## Non-goals

- Certified ASD-STE100 compliance (judgment-call rules need a human; the linter covers only the mechanical subset).
- Linting every conversational token in real time (not cheap, not needed — Layer 1 handles conversation behaviorally).
- Replacing `caveman`. STE and caveman are opposite tools (see below).

## Two layers

| Layer | What | Where | Enforcement |
|---|---|---|---|
| 1. Behavioral | "How to talk to Gab": the 6 anti-patterns + STE sentence discipline | Append to `~/.claude-shared-config/CLAUDE.md` (= global user CLAUDE.md via symlink) | Prose guidance, every response, no tooling |
| 2. Programmatic | `ste-lint.py` shared linter + software allowlist | `tools/`, called by external-text skills | Hard gate on threshold |

### caveman vs STE (why both exist)

- **caveman** drops articles and filler to cut tokens (~75%). Job: compress internal/agent output.
- **STE** keeps articles and full grammar to remove ambiguity. Job: clarify human/external output.

Opposite treatments of the same tokens. They coexist; STE does not replace caveman. A future `/ste` pull skill (on-demand strict mode) is deferred — Layer 1 always-on covers the need; add the skill only if an on-demand toggle is later wanted.

## Layer 1 — behavioral rule block (user level)

A ~12-line block appended to global `CLAUDE.md`. Content:

- One idea per sentence. Max 20 words for procedures, 25 for prose.
- Active voice. Use a verb for an action, not a nominalization ("analyze", not "perform an analysis of").
- One name for one thing — no synonym rotation.
- No phrasal verbs ("start", not "spin up"; "contact", not "reach out").
- No marketing adjectives (seamless, robust, cutting-edge, powerful).
- No hedges ("it is important to note that this may potentially…").
- No semicolons or run-ons — write two sentences.
- Keep articles (a, an, the). This is where STE and caveman diverge.

Reconciliation with existing rules:

- Aligns with `feedback_human_voice_external_messages` (fewest words) and the "Caveman, Not Prose" step-list rule.
- Em-dash: Gab's global rule bans dashes as separators but allows em-dash as heading labels. The linter treats em-dash as a **soft marker**, never a hard fail, to preserve the heading-label exception.

## Layer 2 — the linter

### Component

Port woosal's `ste-lint.py` verbatim into `tools/ste-lint.py`. Pure Python stdlib. Eleven checks:

`long_sentence(>20w)`, `long_paragraph(>6s)`, `semicolon`, `contraction`, `passive_voice`, `ing_main_verb`, `nominalization`, `phrasal_verb`, `banned_word`, `marketing_adjective`, `modal_hedge`. Plus em-dash frequency as a soft marker and longest-sentence length.

Score = `round(total_violations * 100.0 / words, 2)` — violations per 100 words. Lower is cleaner.

CLI: `python ste-lint.py [files...]`, stdin, and glob. Output: filename, word count, total violations, per-100-word score, and the offending spans per check.

### Software-dictionary amendment (hard prerequisite to the gate)

STE's approved dictionary (~900 words) is far too small for software. `banned_word` and `nominalization` will fire on legitimate terms ("deploy", "endpoint", "repo", "schema", "adapter", "pipeline", "backfill", "commit", "config").

Build `tools/ste-software-allowlist.txt`: curated exemptions for eng/adtech/Klever vocabulary. Seed from the Klever GLOSSARY (107 terms) plus common software vocab. Documented grow-path for new terms. The linter loads this file and exempts listed terms from `banned_word` and `nominalization`.

**Gate blocker:** the hard gate stays advisory until the false-positive rate on a software corpus is ~0. An unseeded allowlist would block every MR.

### Skill integration (automatic trigger)

Upgrade three skills to run the linter on the draft before preview — the same shape as `post-comment` already running `verify-causal-claims.py`:

- `skills/post-comment`
- `skills/klever-mr`
- `skills/klever-3ps`

The in-skill step is behavioral (holds while the agent follows the skill). For a real hard gate, the linter also writes a pass-marker and a PreToolUse hook blocks the irreversible publish unless the marker is fresh. Enforcement therefore differs per surface:

| Skill | In-skill trigger | Mechanical backstop | Result |
|---|---|---|---|
| post-comment | yes | yes — extend `external-post-gate.sh` to also require a fresh lint marker | truly hard |
| klever-mr | yes | extend the hook to require a lint marker before an MR POST that carries a description (hook currently ignores MR creation, only comment endpoints) | hard, needs small hook change |
| klever-3ps | yes | none possible — 3Ps output is a file pasted into Slack, no interceptable publish call | in-skill gate only |

### Hard-gate mechanics + safety valve

- Threshold **N** (violations per 100 words) — calibrated, not guessed.
- The linter writes a marker (e.g. `/tmp/.ste-lint-pass`) on pass, mirroring `verify-causal-claims.py`'s `/tmp/.pce-gate-pass`.
- Human override at preview: an explicit `Lint-ack: <reason>` line in the draft (quoted error text, vendor name, unavoidable term), logged to the post-comment audit. **The agent cannot self-override** — mirrors the never-force-resolve rule.

### Calibration (mandatory before flipping the block)

1. Lint ~30–50 of Gab's real past external posts (post-comment `*.posted` files / `global-post-log.yaml`).
2. Read the score distribution of the posts Gab considers good.
3. Set N from that distribution (e.g. the 75th percentile of good posts). Document N and the rationale.
4. Confirm the software-corpus false-positive rate is ~0. If not, grow the allowlist and repeat.

## Test suite + measurement

- `evals/ste/` registered in `evals/manifest.yaml`. Fixtures: pairs of (slop input → clean expected). Assertions: the right checks fire on the slop input, and the score drops after revision. Same pattern as `post-comment/evals/run_causal_evals.py`.
- **Metric — lint-delta:** score before the skill vs score after the skill, logged per post. Aggregate = the improvement number, replicating woosal's −74% on Gab's corpus.
- **Metric — false-positive rate:** violations on a curated software corpus that should score ~0. This metric blocks the gate flip until it reaches ~0.

## Rollout

1. Land `tools/ste-lint.py` + `tools/ste-software-allowlist.txt` seed. Append Layer 1 block to `CLAUDE.md`.
2. Wire the linter into the three skills as **advisory** (score shown at preview, no block). Collect scores.
3. Calibrate N. Drive the software-corpus false-positive rate to ~0.
4. **Flip the hard gate.** Add the marker check to `external-post-gate.sh` (post-comment + klever-mr). Wire the override + audit.

## Feasibility / impact / risk

- **Feasibility: high.** The linter and skill exist upstream (pure stdlib). The choke-point pattern (disk verifier → marker → PreToolUse gate) is already proven for KTP-907.
- **Effort:** linter port + allowlist = small; wiring three skills + hook change = medium; calibration + evals = small.
- **Impact:** measurable, enforced slop reduction on every external artifact; a single consistent voice.
- **Main risk:** false-positive blocks on legitimate vocabulary → contained by the allowlist, calibration, and the human `Lint-ack:` override. Secondary risk: STE's article/grammar requirement fighting caveman brevity → resolved by keeping them separate tools and using STE's flavored mode for prose surfaces.

## Open items

- Exact value of N — output of calibration, not decided here.
- Whether klever-mr's hook change is worth the small complexity, or klever-mr stays in-skill-only like 3ps — decide during implementation once the advisory scores are in.
