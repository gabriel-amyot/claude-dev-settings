# Architect Lens handoff (Winston menu item AL)

Winston hands this request to the shared `architect-lens` skill. One method, two entry points. Do not re-implement the method here.

1. Load the skill with the host's native mechanism:
   - Claude Code: the Skill tool, `architect-lens`.
   - Codex: `$architect-lens`.
   - Any other host: read `~/.claude-shared-config/skills/architect-lens/SKILL.md` with the native file Read tool. This path is outside the BMAD payload, so do not use `bmad.py read` for it.
2. Pass along what the user already told Winston: the problem, any business drivers, and the step they want (characteristics, governance, quanta, components, styles, tradeoffs, worksheet or review).
3. Follow the skill. Winston keeps his voice, the skill owns the steps and the output.
4. When the skill finishes, return to Winston's menu.
