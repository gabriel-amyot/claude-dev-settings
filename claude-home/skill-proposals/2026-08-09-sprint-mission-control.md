# Skill Proposal: sprint-mission-control
Date: 2026-08-09
Source: tireless-owl — sprint close-out mission control run

## Trigger
"I'm drowning in carried-over tickets", "help me close everything from last sprint", "mission
control for the sprint close", or a recurring weekly close-out. Distinct from klever-sprint-exit
(validation+promotion) — this is the human-bandwidth optimizer: minimize Gabriel's minutes per closure.

## Scope
org (Klever), potentially global later

## Draft Steps
1. Board-vs-disk reconciliation: pull assigned open tickets, scaffold missing folders, classify
   by status; flag tickets with no parseable AC (they are unclosable by definition).
2. Parallel verification agents per ticket cluster (frontend/data/docs/blocked), per-ticket
   reports with verdict + % + minutes-of-human-time; assumption-audit every Blocked flag.
3. Build one CLOSE-OUT board (sections: close-now ranked by human-minutes, decisions, blocked
   with verbatim questions, no-definition-of-done, everything-else index) + per-ticket closing-path
   files (mermaid, colour legend: orange=agent-completable, blue=human, red=external/absent-env,
   cyan=codex-approved) + ready-to-fire gated agent prompts.
4. Adversarial gates: fresh-agent reviews of the paths, codex passes on anything leaving the team;
   adjudicate non-converging REJECTs in writing on the verdict.
5. Crit loop on the whole directory as the human's review surface; evidence bundles end every
   flow; human keeps decisions, merges, posts, destructive confirms.
