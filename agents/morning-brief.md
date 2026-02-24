---
name: morning-brief
description: Processes daily voice briefs into structured org plans. Splits by org, checks yesterday's task completion, produces brief/tasks/standup/plan/steering per org.
tools: Bash, Read, Write, Edit, Glob, Grep, Task
model: opus
---

# Morning Brief Agent

This agent processes a raw morning voice brief into structured daily plans for each org.

## Invocation

Called by `~/work-assistant/bin/morning-brief.sh` with runtime variables injected into the orchestrator prompt.

## Processing

1. Read the orchestrator prompt template at `~/.work-assistant/prompts/morning-brief/orchestrator.md`
2. The shell script has already substituted `{{VARIABLE}}` placeholders with runtime values
3. Follow the orchestrator instructions to split by org, check yesterday's tasks, spawn sub-agents, and produce output

## Prompt Templates

All processing prompts live at `~/.work-assistant/prompts/morning-brief/`:

| Template | Produces |
|----------|----------|
| `orchestrator.md` | Top-level sequencing and constraints |
| `brief.md` | Cleaned/structured transcript per org |
| `tasks.md` | Task specs with dispatch buttons |
| `standup.md` | 5-minute standup script |
| `plan.md` | Sequenced execution plan |
| `steering.md` | Coach-mode assessment and focus directive |
| `dispatch.md` | Task execution prompt (used by dispatch-task.sh) |

Edit any template to change how that output is generated. Changes take effect on the next run.
