# Real-World Eval: feedback-to-spec skill vs actual May 4-5 session

## Methodology

Instead of synthetic test prompts, this eval compares what the skill WOULD produce against what Gabriel's manual workflow ACTUALLY produced on May 4-5, 2026. The manual session is ground truth.

## Source Data

| Artifact | Path | What it contains |
|----------|------|------------------|
| Master extraction | `reports/sbe-extraction-2026-05-04.md` | 13 SBEs from 9 screenshots |
| Leo review | `reports/reviews/leo-adversarial-sbe-review-2026-05-04.md` | Per-SBE PASS/WARN verdicts |
| Amal response | `reports/drafts/jira-comments-2026-05-04/amal-response-v2.md` | Real acceptance/rejection of stakeholder requests |
| Day 2 follow-up | `reports/drafts/feedback-extraction-2026-05-05.md` | 6 more findings with Gabriel's exact words |
| Screenshots | `design/screenshots/ux-feedback-2026-05-04/` | 11 PNGs |

## Eval 1: Discipline — Did the manual session inflate findings?

**Ground truth:** 13 SBEs from 9 screenshots. That's ~1.4 SBEs per screenshot.
**Skill's counting guard says:** finding count should be ±1 of user observation count.

**Verdict:** The manual session DID inflate slightly. SBE-4 ("Incremental Lift Status") was marked "CONFIRMED OK" — not a problem, just verifying working behavior. SBE-5 (column tooltips) was an implied need, not stated by the user. Leo flagged SBE-2's positive scenario as "a feature concept, not a testable spec."

**Score:** The skill's discipline guard would have caught 2-3 of these (SBE-4 non-issue, SBE-2 draft masquerading as spec, SBE-5 inferred need). **Skill improvement: +2-3 tighter SBEs.**

## Eval 2: Severity Calibration

**Ground truth (May 5 session):**
- "this is ugly AF" → P2_MEDIUM (correct — strong language but not a blocker)
- "I already flagged this before, but it's still broken" → P1_HIGH (correct — regression)
- "What is missing in order to expose this data?" → P1_HIGH (correct — asking about a blocker)
- "the data for a location should be cached" → P2_MEDIUM (correct — performance, not urgent)

**Verdict:** Gabriel's natural severity assignments match the skill's tone-to-severity mapping exactly. The skill would produce identical severity ratings.

## Eval 3: [CLARIFY] Tag Usage

**Ground truth:** Leo's review flagged 3 items needing decisions:
- SBE-2: "Where does the button log? What triggers the queue? Who consumes it?" → would be [CLARIFY]
- SBE-5: "Respect filter vs document total in tooltip" → would be [CLARIFY]
- SBE-6: Spec conflict with KTP-482 AC-1 → would be [CLARIFY] or CONFLICT

**Amal response also shows 2 clarification needs:**
- Item 3 (date selection): "Do you want a date range picker?" → [CLARIFY]
- Item 6 (zoomed out view): "Can you tell us more?" → [CLARIFY]

**Verdict:** The skill's [CLARIFY] mechanism maps 1:1 to what Leo and Gabriel naturally did. The difference: the skill would flag these BEFORE drafting specs, not after. **Time saved: one review cycle.**

## Eval 4: Handoff Mode

**Ground truth:** The May 4 session produced:
- Immediate ticket comments (Batch A, B) → equivalent to "Full auto"
- Deferred features (Batch F) → equivalent to "Park it"
- PO questions (Amal items 3, 6) → equivalent to "Comment only"

Gabriel naturally used 3 of the 4 modes in a single session. The skill's mode selection at Step 4c would have let him pre-select per-SBE.

**Verdict:** The 4-mode handoff design is validated by real usage. Gabriel already operates this way manually.

## Eval 5: Quote Fidelity

**Ground truth (May 5):** Gabriel said "this is ugly AF" → Finding preserved exact words.

**Skill requirement:** "User's exact words are quoted or precisely paraphrased."

**Verdict:** The manual session preserved exact quotes. The skill would too (iter-2 evals showed 100% fidelity pass rate).

## Summary

| Dimension | Manual Session | Skill Would Do | Delta |
|-----------|---------------|----------------|-------|
| Finding count discipline | 13 SBEs, 2-3 inflated | Would catch inflation via Mary's audit | +tighter |
| Severity calibration | Matches user tone | Same mapping | neutral |
| Ambiguity handling | Caught by Leo in review (after drafting) | Caught by [CLARIFY] during drafting | +1 cycle faster |
| Handoff modes | 3 modes used organically | 4 modes offered upfront | +explicit choice |
| Quote fidelity | Preserved | Preserved | neutral |
| Code trace | Present in all SBEs | Same capability | neutral |
| agent-os persistence | NOT done (specs only in ticket reports) | Would persist to agent-os/sbe/ | +durability |
| Time | ~2-3 hours manual (spread across conversation) | ~5 min interactive + autonomous | +significant |

## Conclusion

The skill automates what Gabriel already does well, while adding three things the manual process lacks:
1. **Discipline checkpoint before drafting** (Mary's audit catches inflation earlier)
2. **Explicit mode selection** (no ambiguity about what gets touched in Jira)
3. **agent-os persistence** (specs survive session boundaries)

The skill does NOT improve: code tracing, severity calibration, or quote fidelity. Those were already good in the manual workflow.
