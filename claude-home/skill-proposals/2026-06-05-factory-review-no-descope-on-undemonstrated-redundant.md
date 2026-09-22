# Skill Proposal: dark-factory review-gate — don't descope on undemonstrated "redundant"

Date: 2026-06-05
Source: wise-raven (KTP-779 Canada province NAME fix)

## Trigger
During a dark-factory review phase (or any adversarial code review feeding a scope
decision), when a finding marks an AC-listed sub-item as "redundant" / "unnecessary"
AND that finding is tagged `demonstrated: false` (or otherwise unproven).

## Scope
Harness — dark-factory review gate (`contracts/5-review.md` / `review/findings.json`
handling), plus a general reviewer-discipline rule.

## Problem it prevents
In KTP-779 the ticket AC explicitly listed "state boundary AND state centers tilesets."
The factory review produced a LOW finding: "NAME added to state_boundaries is redundant
(consumer reads centers, not boundaries)" with `demonstrated: false`. That undemonstrated
claim was propagated into a decision to re-upload only the centers tileset. The live
click-test later falsified it — the demographics header reads the clicked boundary
feature's NAME, so the boundary tileset was required. Half the ticket shipped; the gap was
only caught by live UI verification.

## Draft Steps / Rule
1. When a review finding would CUT scope that an AC explicitly enumerates, require it to be
   `demonstrated: true` with a concrete trace (the consumer code path that proves the
   sub-item is unused). An undemonstrated "redundant" claim is non-actionable for descoping.
2. Prefer to VERIFY against the live consumer (ui-probe / runtime) before cutting an
   AC-listed sub-item, not a static code read alone.
3. Optionally: surface `demonstrated:false` "redundant/unnecessary" findings as
   "needs-proof" rather than actionable, so the implement/ship phases don't act on them.

## Notes
Captured as nugget #9 in inbox `2026-06-05-ktp779-canada-province-name-tilesets.md`.
Borderline skill vs. CLAUDE.md rule — may be better as a dark-factory contract tweak than a
standalone skill. Pitch during /operationalize-audit.
