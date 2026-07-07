# Eval authoring note — operationalize (Layer B, behavioral)

**Date:** 2026-07-07
**Suite:** `evals/evals.json` (5 evals, skill_name `operationalize`)
**Runner:** skill-creator benchmark — see `/skill-evals` SKILL.md
**Threshold:** default pass-rate >= 0.75

## What's covered

| id | Behavior under test | Grounded in |
|----|--------------------|-------------|
| 1 | End-of-session extraction with a pre-populated manifest: only the NEW nugget is extracted, the already-listed one is skipped, `last_run`/`run_count`/`runs[]` are all stamped even though only one nugget was added, and the agent does not ask which nuggets to persist. | SKILL.md "Session Manifest" + Phase 1 dedup-by-subject + operationalize-defaults |
| 2 | Zero-new-knowledge session: no nugget written, none fabricated, but `last_run` still stamped and a `runs[]` entry appended with empty `nuggets_added`. | SKILL.md "The last_run stamp is mandatory even on a zero-nugget run" |
| 3 | `[+SKILL]` path: repeatable procedure tagged `[+SKILL]`, proposal file written to `~/.claude/skill-proposals/`, procedure ALSO written to inbox, no auto-invoke of skill-creator. | SKILL.md Phase 2 "For [+SKILL] nuggets" + "Accumulate to backlog by default" |
| 4 | Default routing (legacy/no-session): single gotcha to one dated inbox file, `inbox/INDEX.md` row added, classified `[KNOWLEDGE]`, one file per session. | SKILL.md Phase 2 "Default target: Bibliothèque inbox" |
| 5 | `--update <target>` mode: locate + read existing skill, show before/after diff, apply only on approval, no fresh inbox nugget. | SKILL.md "Update Mode" |

## Fixtures

- `files/knowledge-manifest-eval-a.yaml` — manifest with 1 nugget already captured (Cloud Run --no-traffic). Eval 1 asserts the second, un-listed nugget is the only new extraction.
- `files/knowledge-manifest-eval-b.yaml` — manifest already covering the only knowledge point discussed. Eval 2 asserts a clean zero-new run still stamps.

## Notes / caveats

- Evals 3 and 4 write to real targets (`~/.claude/skill-proposals/` and the Klever `documentation/bibliotheque/inbox/`). When the lead runs these, do it against a scratch checkout or `git stash`/reset the inbox afterward — the executor genuinely creates files.
- Eval 1/2 assert manifest mutations. Because the fixture manifest lives under `evals/files/`, the executor should edit that copy (or a working copy), not a live session manifest. Grading reads the transcript, so the mutation intent is observable even if the write path differs.
- Eval 5's "apply only on approval" is graded as "shows the diff and does not blind-write"; in a headless run with no human, the pass condition is that the agent proposes the diff and pauses/asks, not that a human clicks approve.
