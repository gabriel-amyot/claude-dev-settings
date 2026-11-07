# Headless launch (unattended dark-factory builds)

**Invocation: manual only.** Use this when Gabriel explicitly asks to start dark-factory builds
unattended (overnight, at a set time, or under a supervisor). It starts long runs that push branches.
Never start it on your own initiative.

Source: KTP-1216 (2026-11-02/03). Four build attempts ran. Two were lost to launcher faults: a child
session that ended its turn and killed its own workflow, and a launch from the wrong directory.

## Ownership

- **dark-factory** owns one build: launch-time preflight, the child session, the guard lifecycle.
- **sprint-factory** owns dependency order between builds. A build whose prerequisite is not merged
  into `origin/dev` waits. Do not rebuild that scheduling here.

## Procedure

1. **Preflight at launch time, not hours earlier.** For each target repo:
   `python3 ~/.claude/skills/dark-factory/scripts/headless_launch_guard.py preflight --repo <repo> --auth-smoke`
   It checks: `claude` on PATH, a `claude -p` auth smoke test, the path is a git repo and is not
   project-management, `git fetch origin` works, the main checkout is clean, no hook manager
   (`core.hooksPath`, `.husky/`), and free disk on the repo volume. Any failure stops the whole batch.
   Copy its `workflow_args` (`cwd`, `free_disk_gb`, `min_free_gb`) into the Workflow args.
2. **Install the temporary pre-push guard** in each target repo:
   `... headless_launch_guard.py install-guard --repo <repo> [--protect-prefix <prototype-branch-prefix>]`
   It refuses pushes to `dev`, `uat`, `main`, `master`, any tag, any branch delete, any
   non-fast-forward push, and any branch with a protected prefix. A pre-existing hook is backed up.
3. **Keep the Mac awake** for the supervisor: `caffeinate -w <supervisor pid>`.
4. **Start each child inside the code repo**, not inside project-management:
   `claude -p "<prompt>" --permission-mode bypassPermissions --output-format json < /dev/null` with the
   repo as the working directory. The prompt must:
   - invoke the Workflow tool with the dark-factory script and explicit args
     (`ticket`, `org`, `headless: true`, `now`, `cwd`, `free_disk_gb`, and `decision_file` /
     `humanDecisions` when the human has answered a gate);
   - write the workflow `run_id` to the output folder as soon as it exists;
   - **keep its turn open** until the workflow's completion notification arrives. Repeat
     `sleep 540` (Bash timeout 600000 ms). A headless print session that ends its turn kills the
     background workflow. Cap the polls (for example 30) and write a `CHILD_POLL_TIMEOUT` terminal;
   - on `GATE_REQUIRED`, write the gate packet and record a `type: gate` ledger handoff with the
     `ledger` helper, then stop;
   - on any terminal, write `terminal.json` and a short summary, then stop.
   Pass human answers as `{ "<id>": { "question": "...", "answer": "..." } }`, so the concierge can
   match both the id and the question text.
5. **Supervise.** One build at a time per repo (shared ports and main checkout), repos in parallel.
   A deadline per build (4 h worked). Stop every further launch after the first `HALT_AGENT_SKIPPED`.
   Launch only inside a window that ends before the nightly GitLab outage (about 23:00-05:00 ET) and
   never roll a missed window forward to the next day.
6. **After the run.** For each build that pushed a branch: run a Codex review of the branch diff
   (`/adversarial-cascade`, explicit request), then the main-loop merge checklist from SKILL.md
   (`tdd_red_audit`, MR, tracker close-out). Live validation stays separate from the build.
7. **Remove the guard**, always, including after an interrupted run:
   `... headless_launch_guard.py remove-guard --repo <repo>`. It restores a backed-up hook and refuses
   when the backup's sha256 changed. `status --repo <repo>` shows what is still installed.
8. Record each outcome in the ticket folder.

## Reference implementation

The KTP-1216 supervisor and launcher are ticket-specific (vendor guardrails, repo map, plan format):
`project-management/tickets/KTP/KTP-1258/KTP-1216/spike/overnight/tools/`
(`launch_dark_factory_v2.sh`, `build_supervisor_v2.py`, `make_plan_v2.py`). Copy their structure, not
their guardrail text. Only the preflight and the guard are generic, and only they live in this skill.

## Guard

`tests/headless_launch_guard_test.py`: 23 cases with real `git push` through the installed hook,
including byte-identical restore, a double install after an interruption, and a tampered backup.
