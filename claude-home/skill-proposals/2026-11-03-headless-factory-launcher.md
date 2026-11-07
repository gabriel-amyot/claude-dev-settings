# Skill Proposal: headless-factory-launcher
Date: 2026-11-03
Source: KTP-1216 Targeting factory restart (session amber-heron); four build attempts, two lost to launcher faults

## Trigger
Launching one or more /dark-factory builds unattended (overnight, scheduled window, supervisor) as separate
headless `claude -p` sessions started inside the code repo. Also: "run the builds at 05:15", "start the supervisor".

## Scope
Global (any org that runs the Workflow-based dark-factory headless). Today the launcher lives as ticket-local
scripts: tickets/KTP/KTP-1258/KTP-1216/spike/overnight/tools/{launch_dark_factory_v2.sh,build_supervisor_v2.py,make_plan_v2.py}.

## Draft Steps
1. Preflight at launch time (not hours earlier): `claude -p` auth smoke test, repo fetch, clean main checkout,
   no hook manager (core.hooksPath/husky); stop the batch on any failure.
2. Install a TEMPORARY shared pre-push guard (protected refs, prototype branches, tags, non-fast-forward) and
   attach `caffeinate -w <supervisor pid>`.
3. Launch each child with a prompt that keeps its turn open (repeated `sleep 540`) until the Workflow's
   task-notification arrives; write run_id early; pass human answers as {id: {question, answer}}.
4. Derive the plan from saved concierge results only; gate dependents on verified merge evidence (repo, branch,
   reviewed tip, new-since-baseline, ancestor of origin/dev); keep live validation separate; enforce a launch date.
5. After the run: Codex branch review per build, main-loop merge checklist, remove the guard, record outcomes.
