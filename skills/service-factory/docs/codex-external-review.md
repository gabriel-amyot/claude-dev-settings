# Codex external adversarial review — the pre-WALL refutation gate (NEW in 0.3.0)

A named, reproducible protocol. It runs as **Phase 4b**, after the agent's own
falsification bursts and its own two-context adversarial pass, and **before** the
Phase 5 WALL. It is **additive** — it does not replace the agent's own adversarial
pass; it adds fresh, out-of-context refuters who never saw the investigation form.

## Why

The agent that built the theory map is the worst judge of it: every re-read re-anchors
on the story it already believes. A challenge is a falsification trigger, not a prompt
to gather more confirming evidence. The Codex reviewers exist to **prove the RCA wrong**
from a clean context, so a load-bearing claim that survives is one no fresh reader could
break — and one that breaks goes back to the board instead of past the human WALL.

## The protocol (reproducible)

1. **Freeze the candidate RCA.** The board is at a stable state (≥1 CONFIRMED cause, or
   the no-cause package). `stamp_check.py` has NOT yet run; that is Phase 5.
2. **Dispatch 2+ fresh-context Codex CLI reviewers, each read-only, each with a DISTINCT
   lens.** Every reviewer is mandated to **PROVE THE RCA WRONG**, not to bless it.
   Minimum two lenses (add more for a multi-cause or cross-env RCA):
   - **Lens A — mechanism + timeline math.** Attack the "how introduced" theory and the
     anchor timeline: does the first-error time actually precede/coincide with the named
     change? Does the mechanism physically produce the reproduced signature? Is any
     causal step hand-waved?
   - **Lens B — ruled-out items + fix framing.** Attack the elimination log and the fix:
     is any REFUTED card actually only SHELVED? Is a layer silently uncarded? Does the
     proposed fix address the confirmed cause or a symptom? Does one cause really explain
     the anchor in EVERY reported env?
3. **Invocation** (one per lens; write output to `gate-reports/`):
   ```
   codex exec --sandbox read-only \
     "<refutation prompt for this lens>. Read rca.md and board.yaml in
      <service-area-dir>. Your job is to PROVE THIS RCA WRONG. For each
      load-bearing claim, state whether you can break it and with what evidence.
      Output a verdict per claim: BROKEN | SURVIVES | CANT-TELL." \
     > <service-area-dir>/gate-reports/codex-review-<lens>.md
   ```
4. **Merge the verdicts.** Any load-bearing claim a reviewer marks **BROKEN** (with a
   real refutation, not a vibe) **blocks the WALL**. The broken claim → back to the board
   (new/REVIVED card + falsify-test), not forward to the human. `CANT-TELL` is not a
   block but is recorded. A claim is WALL-eligible only when it SURVIVES every lens.
5. **The WALL cannot be crossed on any load-bearing claim a Codex reviewer broke.** This
   is a hard precondition of Phase 5, alongside `stamp_check.py`.

## Relationship to the other adversarial layers

| Layer | Who | Context | When |
|---|---|---|---|
| Falsification bursts | agent probes | in-run | Phase 4 |
| Two-context adversarial pass | agent, second context | re-read | Phase 4 (agent's own) |
| **Codex external review** | **2+ Codex CLI, read-only** | **fresh, never saw the form** | **Phase 4b (NEW)** |
| The WALL | the human | — | Phase 5 |

All four stack. The Codex layer is the last machine gate before the one guaranteed human
touch, and its whole value is that it is out-of-context: it cannot rubber-stamp the
anchor because it never held it.
