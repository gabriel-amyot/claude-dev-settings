# Swarm Diagnostics Pattern

Use when a complex blocker spans multiple services with several potential root causes.

## Protocol

1. **Map the failure chain.** Trace backwards from symptom to root cause, identifying every link (e.g., tick → partner config → EQS → ERS MV → DateTime type → ComplianceErsClient).
2. **Spawn parallel haiku agents.** One agent per investigation angle. Each is single-minded: one question, one answer. Examples: "trace the code path from tick to partner config", "check what libraries handle DateTime conversion", "find all PRs with unresolved comments."
3. **Never duplicate research.** If an agent is investigating a file or topic, no other agent (or the orchestrator) touches it.
4. **Synthesize with Opus.** After all agents report, synthesize into an ordered blocker list. Order by dependency (fix X before Y can work).
5. **Prioritize:** code fixes → config changes → data cleanup → manual steps. Code can be committed and deployed. Config needs env var updates. Data cleanup needs console access.
6. **Implement in worktrees.** Use `isolation: "worktree"` for code changes so multiple branches can be worked simultaneously.

## Agent Design Rules

- **Haiku for research, Opus for synthesis and implementation.** Don't waste Opus tokens reading files.
- **10 agents max per swarm.** Beyond that, synthesis becomes unwieldy.
- **Run in background.** Launch all research agents with `run_in_background: true`, then wait for notifications.
- **Each agent gets one deliverable.** "Summarize: X, Y, Z" at the end of every prompt so the agent knows what to return.

## When NOT to Use

- Single-service bugs with obvious root cause. Just read the code.
- Questions answerable by 2-3 grep/glob calls. Use direct tools.
- When the user already told you the root cause. Just implement.
