# Triage mode: adversarial review of the skill-proposal backlog

Decide, for every pending proposal in `~/.claude/skill-proposals/`, one verdict: `BUILD`, `UPDATE:<skill>`, `MERGE:<proposal>`, `SOP`, or `ARCHIVE`. Claude reviews first, Codex attacks that review, the human decides on one HTML page, then agents apply the decisions with evals.

Cost: about 10 Claude agents and 11 Codex runs for 100 proposals. Run it only when the user asks.

Scripts: `S=~/.claude/skills/batch-skill-pipeline/scripts/triage`. Every script takes `--run-dir`. Run Python with `uv run --quiet python3 ...` (the system python3 may lack modules).

## Rules for the whole run

- **State lives on disk.** The run directory is the only state. After each step, update `STATE.json` with `$S/state.py`. A crashed session resumes from the first phase that is not `done`.
- **No Bash heredocs.** They hang the Bash tool. Write prompts and files with the Write tool.
- **Never `cd`.** Use absolute paths.
- **Subagents do not commit.** The orchestrator commits, one commit per package, with a why and a what.
- **Investigation prompts carry a `Library:` line.** Name the knowledge-library pages that apply, or write `Library: silent (checked INDEX/ALIASES for <topic>)`. A hook blocks dispatch prompts without it.
- **Org scope.** Read only the active org and the personal harness. Org knowledge (vendor facts, domain SOPs) never goes into the harness repo.
- **Human gates.** Stop and wait at the end of P0, P5 and P8. Silence is not approval.

## P0. Preflight (gate)

1. Count installed skills: `ls ~/.claude/skills/*/SKILL.md | wc -l` (exclude `_archive`). Compare with the drift alarm (120 unless the REJECTION-LOG says otherwise). Report the headroom.
2. Create the run directory: `RUN=~/.claude/skill-proposals/.triage/<YYYY-MM-DD>/`. Not `/tmp`: it must survive a reboot. If it exists and has `STATE.json`, this is a resume. Read the state and go to the first phase that is not `done`.
3. Codex smoke test: `$S/run_codex.sh $RUN smoke`. Exit 0 means Codex answers. If it fails, read `$RUN/codex/run-smoke.log`. Without Codex, P3 and P4 run as fresh-context `general-purpose` agents with the same prompts, and the page labels that pass "second pass (Claude)".
4. Clean-repo gate on the harness repo: `git -C ~/.claude-shared-config fetch origin`, then `git status --short`. A dirty tree stops the run until the user decides.
5. Ask for the scope: all proposals, or `--since YYYY-MM-DD`. Ask which transcript directories and knowledge libraries the reviewers may search (default: the active org's `.specstory/history/` and its knowledge library `INDEX.md`). Get the user's "go".

Outputs: `$RUN/STATE.json`, `$RUN/codex/smoke.txt`.

## P1. Inventory and split

```
uv run --quiet python3 $S/split_batches.py --run-dir $RUN [--since YYYY-MM-DD] --size 13 \
  --transcript-dir <dir> [--transcript-dir <dir>] --knowledge-dir <dir> --org-scope "<text>"
```

The script sorts proposals newest first, writes 13 per batch, renders the rubric to `$RUN/brief.md`, and records P1 `done`.

Then cluster the proposals by topic. Read only the trigger column of `$RUN/inventory.tsv`. Write `$RUN/groups.json` as `{"<group name>": ["<proposal name>", ...]}`. Leave doubtful items out (they show as "Ungrouped"). Name one group "Possibly covered already" for proposals that an installed skill may cover.

Outputs: `inventory.tsv`, `batches/batch-*.txt`, `brief.md`, `groups.json`.

## P2. Claude first pass

Dispatch one `general-purpose` agent per batch, all in parallel, in the background. Prompt:

```
Read <RUN>/brief.md and follow it exactly. Your batch: <batch-id>, file list <RUN>/batches/<batch-id>.txt.
Write <RUN>/results/<batch-id>.json. Do not commit. No Bash heredocs. Never cd.
Library: <pages that apply, or "silent (checked INDEX/ALIASES for skill proposals)">
```

As each agent completes, validate its JSON (`uv run --quiet python3 -m json.tool`) and run `$S/state.py --run-dir $RUN --batch <id> --pass claude`. Render the page now and open it (`open $RUN/triage.html`): it refreshes every 30 s while `status` is `running`, so the user can watch.

Evidence discipline (also in the brief): keyword counts are inflated. Prefer incident-level evidence. Discount the triage session itself, audit sessions that quote proposals, and recalled SOP text.

Outputs: `results/batch-*.json`.

## P3. Codex second pass, per batch

For each batch with a Claude result: `$S/run_codex.sh $RUN batch <batch-id>`. Run up to 9 in parallel as background Bash jobs. The launcher uses a read-only sandbox, a neutral empty cwd, a positional prompt, `< /dev/null`, and `--output-last-message`.

A non-zero exit is a failure, also when Codex itself exited 0: exit 3 (no output file) and exit 4 (empty output) are the known silent-failure signatures. Retry a failed batch once. If it fails again, record `--mark failed` and continue: the Claude verdict stands for that batch, and the page shows it as Codex "pending".

Mark each success: `$S/state.py --run-dir $RUN --batch <id> --pass codex`.

Outputs: `codex/out-batch-*.json`, `codex/run-*.log`, `codex/run.log`.

## P4. Codex groups and overall review

1. `$S/run_codex.sh $RUN groups`: misattributions, new clusters, coverage of the "possibly covered" group, merge designs.
2. After P3 and step 1 finish: `$S/run_codex.sh $RUN overall`: bias, conflicts, evidence method, top 15 actions, safe archives, invocation corrections, and one `OVERALL: SOUND | NEEDS REWORK` line.

If the overall verdict is NEEDS REWORK, show its reasons to the user in P5 before any decision.

Outputs: `codex/out-groups.json`, `codex/out-overall.md`.

## P5. Render and decide (gate)

```
uv run --quiet python3 $S/final_verdicts.py --run-dir $RUN
uv run --quiet python3 $S/render.py --run-dir $RUN
open $RUN/triage.html
```

Final verdict rule: the Codex verdict wins on conflict; the Claude verdict stands when Codex is missing. Final score = mean of both scores.

The page has summary cards, search, verdict and group filters, a "disagreements only" toggle, sort by final score, date or eval ease, verdict chips for both passes, expandable evidence, the Codex groups and overall panels, and a Top actions panel. Each row has a decision: Accept (default), Override verdict, or Hold, plus a note. Decisions persist in the browser. "Export decisions" downloads `decisions.json` and copies it to the clipboard.

Ask the user to save `decisions.json` into `$RUN/` or paste it into the chat (then write it to `$RUN/decisions.json`). Run `final_verdicts.py` again: overrides replace the verdict, holds become `HOLD`. Set status `waiting` while the user reviews. Do not start P6 without an explicit approval.

## P6. Apply

1. **Archive.** `uv run --quiet python3 $S/archive.py --run-dir $RUN` is a dry run. Show the list. Then `--apply`: it writes a tarball backup to `$RUN/backups/`, moves only final `ARCHIVE` proposals to `archive/`, and appends one audit section to `archive/REJECTION-LOG.md`. `HOLD` proposals never move.
2. **Packages.** Group the BUILD, UPDATE and MERGE verdicts by target skill into packages (one package per target skill or a small set of related skills). Create one harness worktree for the run (`using-git-worktrees`, branch `<ticket-or-issue>-skill-proposal-triage`). Dispatch one `general-purpose` agent per package with an apply brief that says:
   - edit only the assigned skills, in the worktree, never in the live checkout;
   - verify every defect claim against the current file before changing it, and report false claims;
   - size discipline: an UPDATE is not free. New procedure goes to `references/<topic>.md` or `scripts/`, with one pointer line in SKILL.md. Report SKILL.md bytes before and after. Do not broaden a description unless the trigger changed;
   - follow the final invocation mode; destructive, outward-facing or prod-touching modes stay manual;
   - evals are required: extend a Layer A suite (prefer a case that fails on the old code), or add one for a deterministic change, or add a Layer B or B' case for prose. Run every Layer A runner touched. Write manifest blocks to `$RUN/apply/manifest-additions/<package>.yaml`. Never edit `evals/manifest.yaml`;
   - do not commit, push, or run git mutations; write a report to `$RUN/apply/reports/<package>.md`.
3. **SOP verdicts.** Org knowledge goes to the active org's knowledge library, never the harness. Follow the Librarian Protocol: check `CATALOG.md` or `INDEX.md` first, name the page by domain and purpose, place it in the correct section, update that section's `INDEX.md`, and add an `ALIASES.md` row. Prefer `bibliotheque-librarian shelve`. Cross-org harness knowledge goes to `~/.claude/library/` with the same protocol.
4. After each package report, review the diff, then commit that package in the worktree with a why-and-what message.

## P7. Manifest and sweep

```
uv run --quiet python3 $S/merge_manifest.py --run-dir $RUN --worktree <W>
uv run --quiet python3 $S/sweep.py --run-dir $RUN --worktree <W> --baseline ~/.claude-shared-config
```

`merge_manifest.py` inserts the new suite blocks before `exclusions:`, skips existing targets, runs the added Layer A suites against the worktree, and writes `$RUN/apply/eval-run.md`.

`sweep.py` runs every Layer A suite on the branch and on the baseline (main). Some runners resolve live paths internally, so a red suite on the branch is not a regression by default. Only `REGRESSION` (PASS on main, red on the branch) blocks. Report `PRE-EXISTING` failures, do not fix them in this run.

Outputs: `apply/eval-run.md`, `apply/sweep.md`.

## P8. Merge, push and report (gate)

1. Show the user: archived count, packages applied, SKILL.md byte changes, eval table, sweep classes, open items.
2. On approval, push the branch and open the pull request (or merge, as the user says). Never rewrite history.
3. `touch ~/.claude/skill-proposals/.last-audit` so the backlog hook resets its clock.
4. Re-render the page with status `done`. Write `$RUN/REPORT.md`. Mark P8 `done`.

## Resume

Read `$RUN/STATE.json`. `phases` lists the finished phases. `batches.<id>.claude` and `.codex` list the finished batches. Re-run only the missing work. Every script is safe to re-run: `run_codex.sh` moves an old output to `.prev` first, and `archive.py` skips proposals that already moved.

## Files in the run directory

| File | Phase | Written by |
|---|---|---|
| `STATE.json` | all | `split_batches.py`, `state.py` |
| `inventory.tsv`, `batches/*.txt`, `brief.md` | P1 | `split_batches.py` |
| `groups.json` | P1 | orchestrator |
| `results/batch-*.json` | P2 | Claude agents |
| `codex/out-batch-*.json`, `codex/run.log` | P3 | `run_codex.sh` |
| `codex/out-groups.json`, `codex/out-overall.md` | P4 | `run_codex.sh` |
| `final-verdicts.json`, `triage.html` | P5 | `final_verdicts.py`, `render.py` |
| `decisions.json` | P5 | the user, from the page |
| `backups/*.tgz` | P6 | `archive.py` |
| `apply/manifest-additions/*.yaml`, `apply/reports/*.md` | P6 | apply agents |
| `apply/eval-run.md`, `apply/sweep.md` | P7 | `merge_manifest.py`, `sweep.py` |
| `REPORT.md` | P8 | orchestrator |
