# Skill Proposal: sally-dogfood
Date: 2026-04-24
Source: Mission Control Phase 4 UX review session

## Trigger
After shipping UI changes to any web application. "dogfood the UI", "have Sally look at this", "UX review", "run the dogfood". Also proactively suggested after completing frontend work.

## Scope
Global (any project with a web frontend running locally)

## Draft Steps
1. Verify dev server is running (check localhost port)
2. Launch subagent as Sally BMAD persona with browser automation tools (Claude in Chrome)
3. Follow exploration checklist: first impressions, navigation, each major view, cross-cutting (responsive, errors, accessibility)
4. Capture screenshots at each step
5. Write severity-rated report (Blocker/Major/Minor/Cosmetic) to `docs/` or project-specific location
6. Summarize top 5 fixes prioritized by impact

## Value
This session proved that a visual UX audit catches issues invisible to code review: NaN rendering bugs, duplicate UI elements, information density problems, jargon in labels, false affordances (buttons that do nothing). The user explicitly said "a lot of what I said, Sally could have found by looking."
