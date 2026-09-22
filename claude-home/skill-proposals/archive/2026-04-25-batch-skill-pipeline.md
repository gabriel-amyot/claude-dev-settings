# Skill Proposal: batch-skill-pipeline
Date: 2026-04-25
Source: Tier 1 skills batch session

## Trigger
When /operationalize-audit approves 3+ skill proposals in a single session. "Build all approved skills", "batch create these skills", "create the Tier N skills."

## Scope
Global

## Draft Steps
1. Read all approved proposals and the reference SKILL.md format
2. Dispatch N parallel Sonnet subagents (one per skill) with proposal + format reference + bundled resource instructions
3. Structural validation gate: each subagent verifies frontmatter, trigger phrases, word count, internal references before returning
4. Dispatch N parallel functional test subagents with real scenario inputs per skill
5. Consolidate results: per-skill structural + functional grades, update AGENT_BRIEFING.md with audit summary
6. Mark proposals as BUILT
