# Shared skills in Claude and Codex

One source serves both agents. Skill links share instructions and resources, not runtime tools or hook enforcement.

## Native tools

In Claude, use its registered Skill/Agent/question/task tools. In Codex, read a named companion SKILL.md when no Skill tool exists.
Use available native delegation and follow-up messaging. A custom agent name is a role, not a Codex tool identifier.
Read that role's existing ~/.claude-shared-config/agents/<name>.md body and pass it to a native subagent with the current org, task, paths and constraints. Do not copy the agent into a second implementation.
Use supported host models. Claude labels such as sonnet/haiku/opus and bypassPermissions do not authorize model or permission overrides on another host.
Use the available question UI or a concise question followed by a real user response. Persist tasks in the current session state if native task tools are unavailable.
Use available web retrieval and image-viewing tools for WebFetch and multimodal Read instructions.

## Knowledge and continuity

Gabriel prioritizes session continuity, the knowledge library and durable memory above other skill packages.
Before investigating an org mechanism, consult that org's bibliothèque INDEX.md and ALIASES.md. Use ~/.claude-shared-config/library for shared operational knowledge.
Write durable knowledge to the existing org/library store with indexes. Do not create a parallel Codex knowledge store or treat Claude private auto-memory as the shared source of truth.
Claude transcript/auto-memory maintenance remains explicitly Claude-history maintenance when run from Codex.
Use only this conversation's known session slug. Never select the newest active session on disk.

## Boundaries

Read a dependency's instructions before using it. If its required executor is unavailable, report the concrete missing capability before mutations in that dependent phase.
Workflow is a real orchestration dependency. Never replace its gates, cache, independent review or resume behavior with a prose imitation.
Linked skills do not install Claude SessionStart, PreCompact, browser or per-edit guard hooks. Do not claim equivalent enforcement.
Respect repo-specific ticket paths, AC-LOCAL.md, architecture ownership and status ceilings over stale examples.
Skill selection notes and the current installed set live in [harness-skill-selection.md](harness-skill-selection.md).

## BMAD dependencies

An explicitly invoked workflow may load its declared BMAD personas through `~/.claude-shared-config/bmad/bmad.py agent NAME`.
Read subsequent BMAD resources through `read PATH` so runtime and active-project config roots stay distinct.
The registry reports missing custom source explicitly. Stop a phase whose required persona is unavailable; never replace its gates or persona from memory.
Generic role-related work does not activate BMAD.
