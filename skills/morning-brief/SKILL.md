# Morning Brief Skill

## Invocation

```
/morning-brief [optional-date-override]
```

**Examples:**
- `/morning-brief` — processes today's brief
- `/morning-brief feb 21` — processes Feb 21's brief

## Implementation

Run the script via Bash:

```bash
~/work-assistant/bin/morning-brief.sh [date-arg]
```

### Dry Run

```bash
~/work-assistant/bin/morning-brief.sh --status
```

## Prompt Templates

All processing prompts are editable at `~/.work-assistant/prompts/morning-brief/`:

| Template | Controls |
|----------|----------|
| `orchestrator.md` | Top-level sequencing, org splitting, constraints |
| `brief.md` | Transcript cleanup, agent commentary style |
| `tasks.md` | Task extraction, tagging rules, spec.md format |
| `standup.md` | Standup script format, tone, length |
| `plan.md` | Execution plan format, dependency analysis |
| `steering.md` | Coach-mode assessment, momentum/quality/pace, focus directive |
| `dispatch.md` | How dispatch-task.sh prompts Claude for task execution |

Edit any template to change how that output is generated. Changes take effect on the next run.

## Output Structure Per Org

```
{vault}/Work Assistant/Daily/{date}/
├── brief.md
├── standup.md
├── plan.md
├── steering.md
└── tasks/
    ├── _overview.md
    ├── {task-slug}/
    │   ├── spec.md
    │   └── runs/
    └── ...
```

## Model Selection

- **Orchestrator:** Opus
- **Org agents:** Sonnet (brief.md, tasks/, standup.md)
- **Planner (per org):** Opus (plan.md, steering.md)
