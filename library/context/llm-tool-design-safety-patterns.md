# LLM Tool Design: Safety Patterns for Side-Effecting Tools

Cross-project design patterns for any CLI or tool an LLM will drive on a human's behalf.
Learned 2026-08-03 building a Claude Code session-recovery tool that simulates keystrokes.

---

## 1. Separate read-only discovery from the one action with side effects

When the "do it" action has a real side effect (here, simulating keystrokes into whatever app
is frontmost), split the tool into at least two subcommands:

- A `find` or discovery command that is always safe to call, has no side effects, and an LLM
  can invoke freely to show the user options.
- An `open` or act command that requires explicit, named targets from the caller, for example
  a repeatable `--session <id>` flag, and refuses to run with none. No "do everything found"
  shortcut. No auto-selection heuristic standing in for a human decision.

**How to apply:** this split directly prevents an LLM from deciding which thing to act on and
executing that decision in the same step. The human, or the LLM relaying an explicit answer
the human already gave, always supplies the target explicitly.

## 2. Never silently collapse multiple real candidates into "the one" — list all of them

A discovery heuristic that picks "the largest matching group" out of several candidates in a
search window silently hides the others. Concretely: an older crash event from about a month
earlier was invisible behind today's larger 21-session cluster, because the tool only surfaced
the biggest cluster in the lookback window.

**How to apply:** list every distinct cluster or candidate group found, with enough summary to
disambiguate: time range, size, a couple of sample identifiers. Let the caller, human or LLM
relaying a human choice, pick which one to drill into for full detail. Do not have the tool
decide which candidate the user meant.
