# Skill Proposal: sprint-dispatch
Date: 2026-05-01
Source: Mission Control agent comms build session

## Trigger
When user has a sprint plan with multiple tickets to distribute across autonomous agents. Phrases: "dispatch the sprint", "scaffold agents for sprint", "set up the autonomous run", "distribute tickets to agents".

## Scope
Global (works across orgs, reads from mission-control config)

## Draft Steps
1. Read sprint plan (from conversation or ticket folder) to identify agent names and ticket assignments
2. Scaffold agent inboxes via Mission Control API (`POST /api/orgs/{org}/agent-inboxes/scaffold`)
3. Write initial dispatch messages to each agent's pending inbox with ticket context, AC summary, and execution instructions
4. Generate a sprint manifest file in the ticket folder listing all agents, their assignments, and inbox paths
5. Output summary: "N agents scaffolded, N messages dispatched. Monitor via Comms tab."

## Notes
- Depends on Mission Control backend running (port 8765)
- Each agent's dispatch message should include: ticket key, AC summary (from ac.yaml if available), repo mapping, and execution mode (worktree recommended)
- Could integrate with `/sprint-crawl` agent for end-to-end autonomous execution
