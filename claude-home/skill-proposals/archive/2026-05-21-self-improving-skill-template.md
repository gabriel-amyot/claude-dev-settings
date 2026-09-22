# Skill Proposal: self-improving-skill-template
Date: 2026-05-21
Source: Dark Factory skill creation session

## Trigger
When creating a new skill that will run repeatedly on different inputs and benefits from cross-run learning (e.g., pipeline skills, audit skills, crawl wrappers).

## Scope
global (harness-level template)

## Draft Steps
1. Scaffold `runs/` directory with INDEX.md in the skill folder
2. Scaffold `LESSONS.md` with cross-run pattern detection rules
3. Add observability protocol section to SKILL.md (phase-level snag logging format, delegation tracking)
4. Add auto-retrospective as the final phase (writes telemetry, compares against previous runs, updates LESSONS.md)
5. Add `--retrospective` standalone flag for on-demand pattern detection

## Notes
Dark Factory is the first skill using this pattern. Let it run for 3-5 real executions before templating. The pattern may need refinement based on what the retrospective actually surfaces vs what's noise. The snag type taxonomy (11 types currently) is Dark Factory specific and would need generalization.
