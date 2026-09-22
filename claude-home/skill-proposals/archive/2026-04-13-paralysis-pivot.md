# Skill Proposal: paralysis-pivot

Date: 2026-04-13
Source: SPV-3 / Richard unblock session (2026-04-10), Gab signaled paralysis mid-session
Status: proposal, not yet implemented

## Trigger

User signals decision overload or paralysis. Phrases:
- "I feel paralyzed"
- "there's too much to decide"
- "I'm overwhelmed"
- "I don't know where to start"
- "I need to focus, cut through this"
- "help me, too many things at once"
- Multi-problem messages where the user is thrashing between topics without resolution

## Scope

Global (`~/.claude/skills/paralysis-pivot/`). Also persisted as a rule in global CLAUDE.md or user memory feedback so the behavior triggers automatically even without explicit skill invocation.

## Problem it solves

When a session accumulates too many open decisions, the assistant's natural tendency is to keep listing options and asking more questions. This compounds the user's paralysis. The assistant must instead:
1. Collapse the decision space to ONE mission
2. Explicitly PARK everything else with a named parking list (so nothing feels lost)
3. Return ONE question only
4. Do not present more than one option until the user unblocks

This is a behavioral rule as much as a skill. The skill invocation is optional because the behavior should be automatic.

## Draft behavior (rule)

When the user signals paralysis:

1. **Stop producing optionality.** No new forks, no new "A/B/C" branches, no new discovery questions.
2. **Identify the single highest-priority mission** from the session context. If unclear, use the user's most recent explicit goal statement.
3. **Name the pivot explicitly**: "Your only mission right now is X." Use direct, simple language.
4. **List the parking lot**: every other open item gets a one-line entry under "❌ parked." This prevents the user feeling like anything is lost.
5. **Return ONE question**, and only one, that the user can answer in 10 seconds. The question must unblock the pivot, not explore new space.
6. **Commit to a concrete next action** contingent on the answer. Do not ask for planning input — propose a plan and ask for yes/no.
7. **If the user says "go,"** execute immediately. No additional clarification.

## Draft structure (if formalized as a skill)

```
~/.claude/skills/paralysis-pivot/
├── SKILL.md
└── references/
    ├── triggers.md              # phrase catalog
    ├── response-template.md     # the "only mission / parked / one question" format
    └── anti-patterns.md         # what NOT to do (more questions, more options)
```

## Draft steps (when explicitly invoked)

1. Scan the last ~5 user messages for open decisions, forks, pending questions, contradictions.
2. Collapse to one mission based on: most recent explicit priority, nearest deadline, blast radius.
3. Produce a response in the template shape: header ("Your only mission is X"), parked list, ONE question, proposed action on yes.
4. Do not call any tool before the user responds.

## Non-goals

- Does not override user authority. If the user says "no, I actually want to decide between A and B first," the skill steps back.
- Does not decide the parked items. They are deferred, not resolved.
- Does not replace brainstorming. If the user is in exploration mode (not paralysis), this skill does not apply.

## Source-session evidence

From 2026-04-10 session:

Gab: "I am about to go offline and honestly there's a lot to decide! I feel a bit paralyzed, can you help me?"

Assistant response (successful pattern):
> "Breathe. I'm going to cut this down to one thing. Your only mission right now: get Clarifying data visible in the dev dashboard tomorrow morning. Everything else is parked. [Explicit parking list.] ONE question only, then you go offline: [specific yes/no]."

This worked. Gab answered "go" and execution moved forward without thrashing. Before the pivot, the response quality was declining (options trees getting longer, the user's responses getting more frantic).

## Related to existing feedback

- Global CLAUDE.md already has feedback entries about not overloading the user and not asking too many questions. This skill operationalizes the escape valve for when overload has already happened.
- Related: existing `feedback_epic_vs_story_precision.md` (fix the right level, don't descend into detail prematurely).

## Open questions

- Should this be a skill at all, or just a rule in global CLAUDE.md? Argument for rule-only: it's behavioral, not procedural. Argument for skill: having a catalog of triggers and anti-patterns is reference-able.
- Both? Rule in CLAUDE.md for auto-trigger, skill for deliberate invocation when the user wants to force the pivot.
