# Session skills across hosts

Gabriel's priority, 2026-10-26: session continuity and durable knowledge are the highest-priority shared workflows.
This plugin is canonical under ~/.claude-shared-config/plugins/session. Claude's original plugin path links here.

## Tool mapping

The entrypoints retain Claude command examples. In Claude, use its native Skill, Agent, AskUserQuestion and task tools.
In Codex, read a named companion SKILL.md directly when no Skill tool exists. Use available native delegation and messaging, with the same source instructions and org scope.
Use the host's available question UI. If unavailable, ask a concise question and wait. Never treat a pending question or elapsed time as approval.
When native TaskCreate/TaskList tools are absent, persist tasks in this session's state.yaml. Do not call unavailable tools or invent tool results.
Claude-specific model labels do not select a model on another host. Use the host's configured model unless a supported selection was explicitly requested.
The /clear instruction means start a fresh conversation in the current host.

## Identity and ledger

Use only the session slug established for this conversation or explicitly supplied by its handoff.
Never adopt the newest active folder, another conversation's session, or an ambiguous ticket match.
If no session is associated, follow init/retroactive-init for this conversation. Check slug collisions against the whole ledger.
All ledger writes use the existing ledger helper. Its global --org flag precedes the verb. Read bin/LEDGER_WRITES.md before writing.

Resolve an existing handoff from its ledger file key and source_session. Preserve a full relative file key exactly.
For a basename, locate it within its source session's prompts/, including sessions/archive/done/<slug>/ and sessions/archive/abandoned/<slug>/.
Read legacy bare-directory entries when recorded, but never create new bare sessions/active/prompts/ or checkpoints/ entries.
Do not guess between multiple matches.
New handoffs and checkpoints belong to the current session's prompts/ and checkpoints/ directories.
Ledger handoff matching uses ticket. related_ticket is the Markdown frontmatter field, not the ledger field.

## Capture before close

Sharing skills does not install Claude's SessionStart, PreCompact or close hooks in Codex.
Before closing, run operationalize for this exact session. Require a readable knowledge-manifest.yaml and verify its capture evidence.
A missing/unparseable manifest or failed capture blocks close. Do not rely on the ledger helper's fail-open manifest handling.
Keep the session active until capture succeeds. Do not mark active intents complete merely to close.
Keep pending handoffs in their session folder when archiving; pickup must resolve archived source sessions.

## Autopilot boundary

Status, triage and revoke can use native tools. Actual unattended approvals still require a human answer.
Before run mode performs any reap, claim or mutation, verify that its required Workflow executor is available.
If unavailable, report the missing executor and stop with the ledger unchanged. A symlink does not provide an executor.
Do not change schedulers, approve work or launch a handoff as part of installing these skills.
