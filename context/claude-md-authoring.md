# CLAUDE.md Authoring Standards

Apply these when editing any CLAUDE.md file.

## Token Budget
CLAUDE.md is loaded into every conversation. Every line costs tokens on every turn. Treat it like a production config, not a notebook.

## Rules
1. **One line, one rule.** No preamble, no examples unless the rule is ambiguous without one.
2. **Deduplicate ruthlessly.** If two rules express the same intent, merge them. If a rule restates what the code or tooling already enforces, delete it.
3. **Extract, don't inline.** If a block of instructions exceeds ~5 lines and serves a single concern, move it to `~/.claude/context/{topic}.md` and add a trigger row to the On-Demand Context table instead.
4. **Group by trigger, not by history.** Rules belong under the heading where a future agent will look for them, not under "things I learned on Tuesday."
5. **Flag stale context, don't remove.** If a rule references a completed migration, resolved incident, or retired tool, flag it to the user for review. Never autonomously remove rules from CLAUDE.md; the agent may lack context about why the rule exists.
6. **Progressive disclosure in the file itself.** The On-Demand Context table at the bottom IS the progressive disclosure mechanism. Prefer adding a trigger→file row over adding inline content.
7. **Scope rules to their audience.** Rules that apply only during specific workflows (shipping, Java, tickets) belong in extracted context files loaded on-demand, not in the main CLAUDE.md. The main file is for always-on rules.
8. **Every rule earns its tokens.** Before adding a rule, ask: "Will this change agent behavior in a way that isn't already enforced by hooks, tooling, or the codebase itself?" If not, it doesn't belong here.
