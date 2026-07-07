# Eval authoring note — jira (Layer B, behavioral) — EXTENSION

**Date:** 2026-07-07
**Suite:** `evals/evals.json` (extended from 9 to 11 evals, skill_name `jira`)
**Runner:** skill-creator benchmark — see `/skill-evals` SKILL.md
**Threshold:** default pass-rate >= 0.75

## What this extension adds

Evals 1-9 (pre-existing, untouched) cover fetch, ticket creation + AC gate, list, comment-status check, linking, link-types, retype, and hierarchy constraints. Two evals appended, continuing the id sequence:

| id | Behavior under test | Grounded in |
|----|--------------------|-------------|
| 10 | Generated Jira comment carries the `[automated]` attribution header (own line + blank line before the body), uses wiki markup not Markdown, and adding a comment does not transition the ticket. | `jira-skill-gotchas.md` "Comment formatting rules" + `JIRA_AGENT_RULES.md` |
| 11 | When invoked from outside an org path (cwd = the skill dir), the agent always passes `--org klever` to `jira_skill.py` rather than relying on cwd auto-detection. | `jira-skill-gotchas.md` "Org slug detection" |

## Exact [automated] rule wording (from jira-skill-gotchas.md)

> All comments posted via `add-comment` must include the `[automated]` attribution header. Format: `[automated]`, blank line, then the comment body. Never skip it, even under deadline pressure.

Eval 10's expectations check for the header on its own line followed by a blank line, matching that format exactly.

## Notes / caveats

- Eval 10 posts a real comment to KTP-115 if run without mocking. When the lead runs it, either mock `add-comment`, target a scratch ticket, or delete the comment afterward. The gradeable behavior (header present, `--comment` flag, no transition) is observable from the transcript regardless.
- Eval 11 asserts `--org klever` specifically. The valid slugs are `klever` and `supervisrai`; `supervisr` / `supervisr-ai` are invalid and error. The expectation rejects those variants.
- Style consistency: evals 1-4 use the `expectations` array (schema-canonical); evals 5-9 use the older `assertions` array. The two new evals use `expectations` to match the schema and the newer skill-creator format.
