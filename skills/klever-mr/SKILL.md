---
name: klever-mr
description: "Create Klever GitLab merge requests with mandatory pre-flight gates. Handles all Klever repo types: Java backend (pom.xml), Node frontend (package.json), Python app (pyproject.toml), and infrastructure/terraform/DAC repos (no version file). Enforces version bump + CHANGELOG for app repos (Java, Node, Python), skips those gates for infra repos. Always produces WHY + WHAT sections in the MR description. Use this skill whenever the user wants to create an MR, merge request, or PR on any Klever repo. Also use when the user says \"push to dev\", \"ready to merge\", \"create MR\", \"open merge request\", \"ship this branch\", \"merge this to dev\", or finishes a feature branch. Klever repos only (GitLab behind IAP)."
nav:
  bay: ship
  when: "Create Klever GitLab MRs. Enforces version bump, changelog, dev sync."
  when_not: "GitHub PRs (use gh CLI). Supervisr shipping (use supervisr-ship agent)."
  org: [klever]
---

# Klever Merge Request Skill

Create merge requests on Klever GitLab repos with enforced quality gates. App repos get version bump and changelog enforcement. Infra/DAC repos skip those gates. Every MR gets a WHY, a WHAT, and a sync check.

It prevents two failures: a tag collision on app repos (CI tags images from the version in code, so two merges with the same version fail the second pipeline), and empty MR descriptions. Rationale, repo-type table, Python and FaaS zip detail: `references/repo-types-and-versioning.md`.

## Hard rules

- **Never push to `main` or `uat` on a DAC repo.** Target `dev`. The skill never pushes to dev/main directly. It opens an MR.
- **App repos (Java, Node, Python) always get the version bump gate.** Java and Node also need a CHANGELOG entry. Python needs one only if `CHANGELOG.md` exists. Only Infra/DAC skips both.
- **Exit codes:** 0 GREEN/pass, 1 RED/needs a human, 3 **CANT_VERIFY**. CANT_VERIFY is never a pass and never a RED. Report "Gate N not run" with the cause, fix the cause if you can, and never report it as a missing artifact or defect.
- **`--merge-on-pass` is explicit only.** Use it only when the human pre-authorized it for this MR in this session.
- **Agents never trigger the DAC apply job.** Human-only, whatever the plan says.
- **GitLab calls use `uv run`.** Plain `python3` lacks `requests` on this Mac. Every `gitlab` skill script runs as `uv run --quiet ~/.claude-shared-config/skills/gitlab/<script>.py`. If the Klever config is missing, run `gitlab_config_setup.py configure klever --op-item <1Password item>` the same way.

## Pre-Flight Gates

Run the gates in order. Gates are **check-and-fix**, not blockers.

**Self-resolving failures** (behind dev, uncommitted changes, missing version bump, missing changelog entry): fix automatically, report what you did, continue. Never ask "should I fix this?" The answer is always yes. Commit fixes as `{TICKET-ID}: pre-MR housekeeping (version bump, changelog)` before pushing.

**Structural failures** (wrong branch type, no repo detected, stale branch already merged): report and stop. For a stale branch, create a fresh branch from dev.

### PROD-PROMOTION gate (MR targets `main`)

`main` pipelines on Klever app repos do **NOT build**. They re-deploy an artifact (Docker image or GCS zip) that a `dev` pipeline already published. A version on `main` that no `dev` pipeline built (cherry-pick + version bump) deploys a nonexistent artifact: **prod 502** (2026-07-29 outage). Before you create or advise a `main`-targeted MR, run:

```bash
bash ~/.claude/skills/klever-mr/scripts/promotion-image-preflight.sh --repo <repo> --ref <promotion-branch-or-HEAD>
```

The script detects image vs zip from the promoted revision's CI file. **0 GREEN**. **1 RED** (artifact absent): STOP. Two valid paths only: (1) promote a **dev** version whose artifact dev already built (full dev→main), or (2) for images, build a **snapshot** from a feature branch (`KLEVER_DEPLOY_SNAPSHOT=prod`). Never invent a new version number on `main`. **3 CANT_VERIFY** (ambiguous type, auth expiry, wrong name) is not a RED: fix the cause and re-run.

### Gate 1: Repo detection and type

`git rev-parse --show-toplevel` must be a repo under `~/Developer/grp-beklever-com/`. Classify: `pom.xml` → **Java backend**, `package.json` → **Node frontend**, `pyproject.toml` (no `pom.xml`/`package.json`) → **Python app**, none → **Infra/DAC**. Java, Node and Python are app repos. Never classify a `pyproject.toml` repo as infra (KTP-735).

### Gate 2: Branch check

`git branch --show-current` must be a feature branch, not `dev`, `main` or `master`. Otherwise FAIL: "You're on a protected branch. Create a feature branch first." Extract the ticket ID (`KTP-XXX-*`, `KTT-XXX-*` or `INS-XXX-*`). No ticket ID: use the branch name and warn that external posts need a Jira key.

### Gate 3: Sync with origin/dev

`git fetch origin`, then `git log HEAD..origin/dev --oneline`. Commits behind: run `git merge origin/dev` and report "Merged N commits from origin/dev." Conflicts: STOP, the user resolves. `git status --porcelain` dirty: commit as `{TICKET-ID}: uncommitted work before MR` and report. If the dirty files look unrelated to the ticket, STOP and ask.

### Gate 4: Version bump (app repos only)

Infra/DAC: skip and report it. App repos:

```bash
python3 ~/.claude/skills/klever-mr/scripts/version-locations.py --repo . --ref origin/dev
python3 ~/.claude/skills/klever-mr/scripts/version-locations.py --repo .
```

Pass: local version strictly greater than origin/dev and no existing tag for it. Fail auto-resolves: bump patch (or next free patch), then `--sync` the CI release variables and re-run without `--sync` until exit 0. Lockfiles, tag check, multi-file and zip 403 cases: `references/repo-types-and-versioning.md`.

### Gate 5: CHANGELOG.md (app repos only)

Infra/DAC: skip and report it. Pass: a `## [X.Y.Z] - YYYY-MM-DD` entry for the local version, dated within 7 days, with at least one bullet. Missing or empty entry: add it from commit subjects. No file: STOP for Java/Node, report and continue for Python. Detail: `references/repo-types-and-versioning.md`.

### Gate 6: Docs lint (only when the MR changes markdown)

No `.md` in `git diff --name-only origin/dev..HEAD`: skip and report. Otherwise run `tools/docs-repo-lint.py` on a clean `git archive` export. Blocking: Mermaid newer than GitLab's 9.1.1, broken relative links, repo-escaping links, in files this MR touches. Missing README is advisory. Commands and triage table: `references/docs-lint-gate.md`.

### Gates 7 and 8: conditional (read `references/conditional-gates.md` when triggered)

| Gate | Trigger | Script | Exit 1 means |
|---|---|---|---|
| 7 CLAUDE.md schema | MR touches `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or `docs/` | `scripts/claude-md-gate.py --repo . --base origin/dev` | New schema violations: ask the human. Never edit CLAUDE.md unasked. |
| 8 Portal DAC env | repo is `dac-gcp-front-klv1ai`, `dac-gcp-front-portal` or `app-front-portal` | `scripts/dac-env-gate.py parity` (DAC) or `app-removal` (portal) | An env var added to one DAC only: ask if required. |

Exit 3 is CANT_VERIFY: report "Gate N not run" and why, then continue.

## Modes

| Invocation | Mode | Behavior |
|---|---|---|
| `/klever-mr` | **Automatic** (default) | Creates MR via GitLab API, posts description. No merge action. Pass `--auto-merge` to enable merge-when-pipeline-succeeds. |
| `/klever-mr manual` | **Manual** (legacy) | Generates URL + description file for copy-paste into the GitLab web UI |
| `/klever-mr --merge-on-pass` | **External merge gate** (explicit only) | Codex review loop, merge to `dev` on PASS. Only when the human pre-authorized it. Read `references/external-merge-gate.md` first. |
| `/klever-mr consolidate` | **Pre-MR consolidation** | Several finished branches become one branch with one version bump, then the normal flow. Read `references/consolidation-mode.md`. |

All modes run identical pre-flight gates and generate the same MR description. They differ only in Steps 3 and 5 and in the merge step.

## MR Creation

Templates, commands and summary formats for Steps 2 to 5: `references/mr-description-and-summary.md`.

1. **Push.** `git push -u origin HEAD`. If the push fails, report and stop.
2. **Extract five mandatory components:** ticket ID, WHY (the problem, 1-2 sentences, from `git log --reverse --format="%B" origin/dev..HEAD`), WHAT (the outcome, not a file list), commits block, test plan (ask if unsure).
3. **Title** `{TICKET-ID}: {short imperative what}`. Target is `dev` unless the user says otherwise. Automatic mode resolves the project ID with `gitlab_skill.py search`. Manual mode builds the `merge_requests/new` URL.
4. **Description** sections in this order: **Why**, **What**, **Tickets**, **Commits**, **Test plan**. Use `.gitlab/merge_request_templates/Default.md` as the skeleton if it exists.
5. **Create.** Write `.mr-description.md` at repo root (not committed, add to `.gitignore` if missing). Run `python3 ~/.claude-shared-config/tools/ste_lint.py .mr-description.md`, show the score, revise obvious hits (advisory, no block). Automatic mode: `uv run --quiet ~/.claude-shared-config/skills/gitlab/gitlab_skill.py --org klever mr --action create ... --target dev`. MR already exists: update its description, never create a duplicate. API creation fails: fall back to manual mode and report the reason. `--auto-merge` only: arm auto-merge, a failure there does not block. Without `--auto-merge`, take no merge action. Print the summary block. A manual-mode URL is bare on its own line.

## Deploy to Dev (`--auto-merge`, automatic mode, app repos only)

Dev only, never demo.dev, uat or prod. Infra/DAC repos and manual mode skip it. Commands, poll limits and the report template: `references/deploy-to-dev.md`.

| App repo | DAC repo | Version variable | DAC scope |
|---|---|---|---|
| `app-front-portal` | `dac-gcp-front-klv1ai` (804; legacy `dac-gcp-front-portal` 514 is prod-only, bump its prod tag separately) | `build_docker_tag_version` | `dev` |
| `app-proximity-report` | `dac-gcp-back-proxrp` | `cpe_cos_version` | `dev` |
| `app-user-management` | `dac-gcp-back-usermg` | `cpe_cos_version` | `dev` |
| `app-proximity-explorer` | `dac-gcp-back-proexp` | `cpe_cos_version` | `dev` |

Repo not in the table: skip deploy, report "No DAC mapping for this repo. Deploy manually."

`dac-gcp-front-portal` also exists and looks like the obvious match for `app-front-portal`, but it is not the live downstream. It last ran 2026-09-29; `dac-gcp-front-klv1ai` runs on every `app-front-portal` dev pipeline and is what serves `portal.dev.klever1.ai`. Targeting the wrong one returns 404 and reads like a broken deploy.

- **Step 6: Wait for merge** (max 10 min). Then run the post-merge cleanup below.
- **Step 7: Dev app pipeline** (max 15 min). `success` or `manual` (bridge `bd-configure-dac` waiting) = build complete. `failed` = STOP.
- **Step 8: Bridge.** List with `gitlab_skill.py bridges`. Find `deploy-in-dev` or `bd-configure-dac`: `manual` → `play-job`, `success`/`running` → read `downstream_pipeline`, `failed` → STOP. No DAC pipeline 5 min after the app pipeline: report and STOP.
- **Step 9: DAC gates.** Agents MAY play the **plan** job, then summarize the trace (create/modify/destroy counts). Agents MUST NEVER trigger the **apply** job. A failed plan: report, never retry.
- **Step 10: Report** the plan. Any destroy gets a TERRAFORM DESTROY DETECTED block that lists each resource. Hand off to the human. After 20:00 EDT, note the nightly dev shutdown.

## Post-merge cleanup (any repo, any mode)

Run it when the MR is merged: after Step 6, on a later `/klever-mr status`, or when the user says "it's merged". Run `git fetch origin` first.

```bash
python3 ~/.claude/skills/klever-mr/scripts/post-merge-cleanup.py --repo <repo> --branch <branch> --ticket <TICKET-ID>
```

Exit 0 (merge proven, nothing to preserve): re-run with `--apply`. Exit 1 (not proven) or 2 (files to preserve): remove nothing and report the script output. The script never uses `--force` and never deletes the remote branch or `/tmp` clones. It only lists them.

## What This Skill Does NOT Do

- Does not deploy to demo.dev, uat, or prod (dev only)
- Does not trigger the DAC apply job (human-only gate)
- Does not manually update DAC version variables (handled by `bd-configure-dac` bridge)
- Does not manually trigger DAC pipelines (auto-triggered by app pipeline bridge)
- Does not push to dev/main directly
- Does not retry failed DAC pipelines (report and stop)
