---
name: klever-repo-rename
description: >-
  Rename a Klever GitLab repo (display name AND URL/path) in place via the cfg
  config-as-code terraform, safely — no delete-and-recreate, history/MRs/tokens
  preserved. Handles the app repos (cfg-app) and DAC repos (cfg-dac-env), the
  short_name-vs-path gotcha, cross-repo reference repointing, plan-gating, and
  the manual apply gate. Use when the user wants to rename a repo, change a
  repo's name/URL/slug, or asks "rename the repo", "the repo has the wrong
  name", "move/rename this project". Klever org only (GitLab behind IAP). Does
  NOT delete/recreate repos.
nav:
  bay: ops
  when: >-
    Renaming an existing Klever GitLab repo that is managed by the cfg-*
    terraform (cfg-app for app/function repos, cfg-dac-env for DAC repos).
  when_not: >-
    Creating a NEW repo (that's a cfg entry add, not a rename). Renaming a
    branch (use klever-repo/branch tooling). Non-Klever repos.
  org: klever
---

# Klever Repo Rename (in-place, config-as-code, safe)

Rename a GitLab repo's **display name AND URL path** through the cfg terraform, in place. The repo keeps its project id, history, branches, MRs, and access tokens; GitLab adds a redirect from the old URL. **Never delete-and-recreate** — that changes the project id and orphans every reference (tokens, pipeline triggers, cross-repo imports).

## Core gotcha (why naive renames only half-work)
- `short_name` → sets `gitlab_project.name` (the **display name**) only.
- `path` → sets the **URL slug**. On an existing repo it is NOT re-derived from short_name; you must set it explicitly.
- **A full rename needs BOTH `short_name` and `path`.**

## Procedure

**1. Locate the repo's cfg entry.**
- App / function repos → `grp-cfg/cfg-app` (a `for_each` map entry with `short_name`, e.g. in `grp_backend_gcp_models.tf`, `grp_backend_gcp_cloudfunction.tf`, `grp_backend_ms.tf`, `grp_frontend*.tf`).
- DAC repos → `grp-cfg/cfg-dac-env` (an individual `module "datasophia-glb-project_*"` block, e.g. in `dac_env_report.tf`).
- Work in a worktree off `origin/main` (fetch first — cfg checkouts are often far behind).

**2. Set BOTH name and URL in the entry.**
- `short_name = "<new-short>"` (display name).
- `path = "<new-full-slug>"` (URL). The full slug matches the current path pattern (e.g. `app-ai-insights`, `dac-gcp-report-aiinsi`).
- **Keep the for_each KEY / module block address unchanged** → guarantees in-place. If you must change the key too, add a `moved {}` block (the DSO 917 `move.tf` pattern) so terraform treats it as a move, not destroy/recreate.
- For DAC repos, the `TF_VAR_faas_composite_minor_name` also drives GCP resource names (Cloud Function/Scheduler/BQ table) — changing it recreates those GCP resources on apply. Change it only if you want the infra renamed too.

**3. Repoint cross-repo references.**
- cfg-app references DAC repos by exact path in `import.tf` (`datasophia_glb_downstream_projects`) and in `grp_multi_project_pipeline_res.tf` (app→DAC deploy triggers, `downstream.project_key`). Update these to the new name.
- Heads-up: repointing a downstream key **destroys + recreates** that link's `gitlab_project_access_token` + its CI variable. That's credential rotation for the renamed link (safe), NOT repo loss.

**4. Plan-gate — read the plan before ANY apply.**
- Open the MR; let `init-validate-plan` run; read the plan.
- REQUIRED on the repo resource: `~ path "old" -> "new"`, `will be updated in-place`, and `Plan: ... 0 to destroy` (repo not destroyed).
- If the gitlab_project shows `-/+` / `must be replaced` → **STOP** (that would delete the repo). A token/variable destroy+create is fine (credential re-key); a repo destroy is not.

**5. Order cross-repo renames.**
- If the rename couples two repos (e.g. cfg-app imports the DAC by path), apply the **referenced** repo (DAC) FIRST. The referencing repo's (cfg-app) MR plan will 404 on the new path until the referenced apply lands. Refresh/merge the referencing MR only after.

**6. Merge + apply.**
- Merge the MR (via `/klever-mr` or `gitlab_skill.py mr --action merge`). Merging to `main` runs the pipeline: `init-validate-plan` (auto) then `apply in noe` (stage `apply`) as **MANUAL**.
- **Merge ≠ apply.** A human triggers `apply in noe` to execute the rename. Agents do not trigger applies.

**7. Verify by project ID (not old path).**
- Confirm via `GET /api/v4/projects/<id>` that `name` and `path` are the new value.
- The REST API `GET /projects/:old-url-encoded-path` returns **404** after rename (it doesn't follow the redirect route). Web/git URLs DO redirect. So verify by numeric project id, never by hitting the old path.

## GitLab API helper (for ops the gitlab CLI doesn't expose)
Reuse `gitlab_skill.py` auth for direct `/api/v4` calls (merge, notes, project-by-id, access-token list):
```python
from gitlab_skill import load_config, get_token_from_keychain, get_iap_token
cfg = load_config()["organizations"]["klever"]; url = cfg["gitlab_url"]
hdrs = {"PRIVATE-TOKEN": get_token_from_keychain("klever")}
iap = get_iap_token(url, iap_refresh_repo=cfg.get("iap_refresh_repo"))
if iap: hdrs["Authorization"] = f"Bearer {iap}"
```

## Do NOT
- Delete-and-recreate the repo (loses history + orphans tokens/triggers/imports; changes the project id).
- Change only `short_name` and think it renamed the URL (it renames the display name only).
- Change the for_each key / module address without a `moved {}` block (destroy/recreate).
- Trigger the `apply in noe` job as an agent (human gate).

Learned from the app-campaign-insight → app-ai-insights + dac-gcp-report-cmpins → dac-gcp-report-aiinsi renames (2026-07), where the short_name-only change renamed the display name but not the URL, and the repoint re-keyed the deploy token.
