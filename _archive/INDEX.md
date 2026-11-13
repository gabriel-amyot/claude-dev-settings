# Harness archive

One archive for the whole harness. Items here are switched off: Claude Code does not load them, and they cost no context. They are kept in git, so you can bring any item back.

## Restore an item

```sh
git -C ~/.claude-shared-config mv _archive/agents/<name>.md agents/<name>.md
git -C ~/.claude-shared-config mv _archive/skills/<name> skills/<name>
git -C ~/.claude-shared-config mv _archive/commands/<name>.md commands/<name>.md
```

Then restore any index or routing lines named in the commit that archived it (`git log -- _archive/<path>`).

## Layout

- `agents/`: agent definitions.
- `skills/`: skill folders, and old eval workspaces.
- `commands/`: slash commands.

## 2026-11-13: harness prune (session measuring-otter)

Evidence: 90-day transcript scan (real coverage 2026-09-01 to 2026-11-12) and a reference check. Proposal and decisions: `~/Developer/grp-beklever-com/project-management/sessions/active/measuring-otter/prune-proposal.md`.

| Item | Kind | Reason |
|---|---|---|
| dev-crawl, supervisr-autopilot (+ autopilot-config.yaml), supervisr-ship, colleague-review, pr-response-sweep, review-responder, mother-base-housekeeper | agents | Supervisr work is paused. Kept for a possible return. 0 use in the window. |
| create-prd, generate-tasks, process-task-list, update-ai-dev-tasks | commands | 2025 ai-dev-tasks set, not used. `/to-prd` and `/to-issues` replace it. |
| session-check-workspace, ui-probe-workspace | skills folder | Eval output leftovers, not skills. |
| everything else in `skills/` | skills | Moved from the old `skills/_archive/` (archived before 2026-11-13). |
