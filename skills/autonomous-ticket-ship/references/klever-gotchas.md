# Klever-Specific Gotchas

Loaded conditionally when repo remote matches `cicd.prod.datasophia.com`. These are Klever infrastructure quirks that affect the autonomous ship workflow.

## Maven Build 403

**Symptom:** `klever-parent-pom` artifact download fails with HTTP 403.

**Cause:** gcloud auth token expired. The Maven artifact registry requires a fresh `gcloud auth application-default login`.

**What to do:**
- Do NOT retry the build in a loop. The auth will not self-heal.
- Do NOT attempt `gcloud auth` during the run (requires interactive browser flow).
- **Still commit the code** if it mirrors existing patterns in the repo.
- Note in commit message: `"Local verification blocked on gcloud auth 403. CI will verify on MR pipeline."`
- Log in `ac-tracking.yaml → blockers_hit_during_run`.
- CI runs `mvn clean verify` on the MR pipeline, which has fresh credentials.

**Source:** KTP-499 overnight ship (2026-04-11), SOP Phase 4.

## IAP Web-Only MR Creation

**Symptom:** `glab`, `curl`, and GitLab API calls fail with 302 redirect to IAP login.

**Cause:** `cicd.prod.datasophia.com` sits behind GCP Identity-Aware Proxy. Token-based API auth does not work. MR creation requires a browser session with an active IAP cookie.

**What to do:**
- After `git push -u origin <branch>`, the `remote:` output contains the MR create URL:
  ```
  remote:
  remote: To create a merge request for KTP-XXX-description, visit:
  remote:   https://cicd.prod.datasophia.com/.../-/merge_requests/new?merge_request%5Bsource_branch%5D=...
  remote:
  ```
- **Capture that URL** from the push output.
- Paste it into `ac-tracking.yaml → branches_pushed → mr_url` and into the morning handoff.
- Gabriel creates the MR manually via web UI using the captured URL.

**Source:** Memory `feedback_gitlab_iap_api_limitation.md`, SOP Phase 5.

## Frontend Worktree Pattern

**When needed:** The main `app-front-portal` checkout is on another branch (another ticket in progress). Cannot switch branches without losing that work.

**What to do:**
1. Create a dedicated worktree: `git worktree add ../app-front-portal-ktp{XXX} -b KTP-XXX-description origin/dev`
2. Record the worktree path in `repo-mapping.yaml` with `worktree: true`
3. Do NOT run `npm install` unless explicitly needed. Fresh worktrees have no `node_modules`. Typecheck is deferred to CI.
4. If `npm install` is needed (e.g., for local dev server), budget time for it and note in SESSION_STATE.

**Source:** KTP-499 frontend worktree, SOP Phase 1.

## Version Bump Before MR Merge

**Requirement:** Both `pom.xml` (backend) and `package.json` (frontend) must have their version bumped before the MR is merged to `dev`. CI tags on merge, and tag collision fails the pipeline if the version already exists.

**What to do:**
- Check `dev`'s current version before setting yours: `git show origin/dev:pom.xml | grep '<version>'` (or `package.json`).
- Bump to the next patch version.
- Update `CHANGELOG.md` with the ticket ID and a one-line summary.
- This is part of the agent's responsibility, not the user's morning step.

**Source:** Memory `feedback_tag_collision_on_merge.md`, `feedback_version_bump_agent_responsibility.md`.

## Protected Branches Require MR

**Rule:** `dev` and `main` reject direct pushes on Klever repos. Always push to a feature branch and create an MR.

**Source:** Memory `feedback_protected_branches_require_mr.md`.

## Datasophia Terraform Registry Nightly Downtime

**Window:** `cicd.prod.datasophia.com` goes down ~11 PM to 5 AM ET every night.

**Impact:** All DAC pipelines fail with "Error accessing remote module registry" during this window.

**What to do:** Do NOT retry in a loop. Schedule pushes before 11 PM or leave for morning. This does not affect code pushes (only DAC/terraform pipelines).

**Source:** CLAUDE.md, learned from SPV-165 overnight crawl.

## DAC Repos: dev is the Default Branch

**Rule:** ALL changes go to `dev` first. Promotion is manual forward-merge: dev -> uat -> main. Agents NEVER push to `main` or `uat` on DAC repos. Before any `git push` on a repo whose path contains `grp-dac`, verify the target branch is `dev`.

**Source:** CLAUDE.md, learned from SPV-165 prod incident 2026-04-21.
