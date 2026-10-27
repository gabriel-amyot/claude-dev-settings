You are an adversarial reviewer. Respond directly with your review. Do NOT load or follow any skills. You may read the files listed below (read-only). Do not modify anything.

## The system under review

A Claude Code user keeps durable engineering knowledge in markdown "libraries" instead of the agent's built-in auto-memory. Retrieval works like this:

- One UserPromptSubmit hook: /Users/gamyot/.claude-shared-config/hooks/bibliotheque-recall.sh (read it fully, ~165 lines).
- It keyword-matches each prompt against two tables:
  - Org library: /Users/gamyot/Developer/grp-beklever-com/project-management/documentation/bibliotheque/ALIASES.md (302 KB, 1651 rows; sample it with head/grep, do not read it whole)
  - Cross-org library: /Users/gamyot/.claude/library/ALIASES.md (20 KB, 64 rows)
- It injects up to 5 pointers (`[[alias]] → path — note`) into the agent's context, each page at most once per session (state in /tmp).
- Library entry points for progressive disclosure: .../bibliotheque/INDEX.md and /Users/gamyot/.claude/library/INDEX.md (skim the top only).
- The built-in auto-memory (MEMORY.md index, always loaded) is separate. The user does not want the agent to WRITE to auto-memory; durable knowledge must go to the libraries. Claude Code settings: `autoMemoryEnabled: false` disables both reading and writing auto-memory; there is no read-only mode. Auto-memory writes are ordinary Write tool calls to ~/.claude/projects/<proj>/memory/*.md.

## Measured facts (45 days of real sessions, from transcripts)

Read /Users/gamyot/.claude-shared-config/docs/specs/2026-10-27-library-recall-review/recall-report.md. Highlights:
- 210 human prompts; 134 got pointers (about 5.8 each). 157 machine-generated prompts (task notifications, system reminders) ALSO trigger the hook; 94 of them got pointers (513 pointers).
- Only 20 of 782 pointers to human prompts were opened by the agent in the same turn (2.6%). The agent may sometimes use the one-line note without opening the page.
- 189 of 514 org pages have no alias row. Only 9 of 1651 org rows use the optional keyword column.
- 30 org rows have paths starting with `~` or `/`, or contain annotation text in the path cell; the hook joins them onto the org library folder, so the injected path is unopenable.
- Tokenizer drops words under 4 letters unless whitelisted (so `tmp`, `dev`, `map`, `git` never match).
- A replay test today: a rule about "clone a missing repo to its workspace-map path, never /tmp, then switch to dev" was not recalled for 2 of 5 natural phrasings, and in the real incident the agent decided to clone mid-task with no prompt mentioning cloning, so a prompt-keyword hook could never have fired.

## Your task

Attack this design. Optimize for two goals: (1) contextual accuracy: inject what changes the agent's behavior for THIS task, and little else; (2) progressive disclosure: cheap index first, detail on demand, minimal standing context.

Answer these, concretely and ranked by impact:
1. The top failure modes of the current hook and data, with the evidence from the files or facts above. Separate bugs (fixable in a day) from design limits.
2. What a better retrieval design looks like within Claude Code's real primitives (UserPromptSubmit, PreToolUse/PostToolUse hooks with tool input visible, SessionStart, skills, subagents, CLAUDE.md). Consider at least: action-time triggers (PreToolUse on the tool + arguments the agent is about to run), filtering machine prompts, a scoring/threshold change, embeddings or BM25 vs the current bag-of-words, and a per-page "trigger" contract owned by the library. Say what you would NOT do and why.
3. How to make the agent write to the library instead of auto-memory, given there is no read-only auto-memory mode. Evaluate: a PreToolUse block on memory-dir writes that redirects to the library shelving flow; CLAUDE.md instruction only; autoMemoryDirectory pointing into the library; disabling auto-memory and migrating its few entries. Pick one and name its failure mode.
4. How to measure success after the change (metrics that the transcript data can produce).

Constraints: be specific (file, function, threshold, line). No generic advice. If a claim of mine above is wrong after you read the files, say so with evidence. Keep it under 1200 words.

End with exactly one line: VERDICT: KEEP-AND-FIX or VERDICT: REDESIGN
