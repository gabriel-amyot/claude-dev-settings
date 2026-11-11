# klever-mr conditional gates 7 and 8

Each script exits 0 (pass or skipped), 1 (needs a human answer), 3 (CANT_VERIFY: the check did not run). Exit 3 is never a pass and never a fail. Report "Gate N not run" with the reason and continue.

## Gate 7: Repo CLAUDE.md schema

Trigger: the MR touches the root `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, or any path under `docs/`. The script checks the trigger itself.

```bash
python3 ~/.claude/skills/klever-mr/scripts/claude-md-gate.py --repo . --base origin/dev
```

- It lints the base ref and the head ref with the schema v1 linter and reports only the violations this MR adds. Rule IDs: S (structure), C (content), P (pointers), B (size), M (AGENTS.md/GEMINI.md mirror).
- Exit 1: show the `NEW` lines to the human. Ask: fix them, or record the reason in the MR description. Never edit `CLAUDE.md` without approval (a hook protects it).
- The linter path: `--linter`, then `$KLEVER_CLAUDE_MD_LINT`, then the prototype under `project-management/general/harness/2026-11-04-portal-claude-md-index/`.
- Out of scope for the script: whether a pointer's destination doc contradicts the rule that points to it. That is a reviewer check.

## Gate 8: Portal DAC env parity

Trigger: the repo is `dac-gcp-front-klv1ai` (804), `dac-gcp-front-portal` (514) or `app-front-portal`. Both DACs deploy the same portal image, each with its own CI variable, and share no git history. Local paths: `~/.claude/library/context/workspace-map.yaml`. Run `git fetch origin` in every checkout you pass, because the script reads `origin/*` refs.

DAC MR:

```bash
python3 ~/.claude/skills/klever-mr/scripts/dac-env-gate.py parity --dac . --sibling <sibling DAC checkout> [--app <portal checkout>]
```

- `BLOCK` (exit 1): the MR adds an env name the sibling DAC does not set. Ask the human if the app treats it as required. Required: open the sibling MR first. Optional: re-run with `--ack NAME` and record why in the MR.
- `ADVISORY`: the MR removes a name the sibling still sets.
- `CLEANUP CANDIDATE` (with `--app`): a name with zero readers in the portal at `origin/main` and `origin/dev`. Launchers and build scripts outside the repo can still read it. Check them before you propose a removal. A positive control (`KLEVER_USER_MANAGEMENT_URL`) must have readers, or the script returns CANT_VERIFY.
- `REMINDER`: a prod image tag bump goes in both projects' `TF_VAR_build_docker_tag_version`.

app-front-portal MR:

```bash
python3 ~/.claude/skills/klever-mr/scripts/dac-env-gate.py app-removal --app . --dac <klv1ai> --dac <portal DAC> [--dac <demo DAC>]
```

- `ACTION`: the MR stops reading `X` and a DAC still sets it. Propose a removal MR on that DAC. A dead value can make a live feature look off in prod.
- Always exit 0. The removal MRs are follow-ups, not blockers for this MR.
