# Klever Infrastructure Access Management

Load when: figuring out how to give a user GCP or GitLab access, auditing permissions, or investigating why a user can't deploy.

---

## GCP Access Model

Access flows through **Cloud Identity groups**, not individual IAM bindings:

```
User
  → grp-org-developer@{domain}    (Cloud Identity group, managed in Google Admin Console)
        → group-mngt               (per-DAC group, created by DAC terraform)
              → GCP project IAM    (roles/browser, roles/iap.tunnelResourceAccessor, etc.)
```

Every DAC and IAC wires `grp-org-developer` into its `group-mngt` group via `group_cloud_identity_membership.tf`. This means **a user in `grp-org-developer` automatically gets access to all Klever GCP projects**.

### To grant access to a new user

Ask Marc-André to add them to `grp-org-developer@{domain}` via **Google Admin Console**. No PR, no pipeline, no IAC change needed. Effect is immediate after group sync.

> **Why not IAC?** Individual user membership in `grp-org-developer` is NOT managed by any terraform repo. The group itself predates the IAC. Membership is managed manually.

---

## What Each IAC/Config Repo Manages

| Repo | Path | Manages |
|------|------|---------|
| `iac-gws-org-groups` | `grp-iac/grp-iac-org/iac-gws-org-groups/` | Cloud Identity group creation (not membership). Groups: `grp-org-gcpuser`, `grp-org-datascientist`, etc. `grp-org-developer` is NOT created here (pre-existing). |
| `cfg-iac-env` | `grp-cfg/cfg-iac-env/` | GitLab group/project structure, branch protection, CI variables. No user membership. |
| `cfg-app` | `grp-cfg/cfg-app/` | GitLab project settings, access tokens, multi-project pipelines. No user membership. |
| DAC repos (`dac-gcp-*`) | `grp-dac/grp-dac-env-*/` | Per-project `group-mngt` groups and GCP IAM. Add `grp-org-developer` as MEMBER to `group-mngt`. |

### Key terraform files per DAC

- `group_cloud_identity_membership.tf` — wires org groups into local `group-mngt`
- `project_iam.tf` — grants GCP roles to `group-mngt` on the GCP project
- `import.tf` — references external groups/projects by lookup

---

## GitLab Access Model

GitLab (cicd.prod.datasophia.com) uses **IAP** (Identity-Aware Proxy). The gitlab skill supports IAP auth via Bearer token extracted from `~/.config/git-gcp-iap/gamyot-beklever@cicd.prod.datasophia.com.cookie`. Full API access (MR creation, pipeline listing, project search) works. When the cookie expires, the skill auto-refreshes via `git fetch` on the configured `iap_refresh_repo`.

### Two layers: structure (code) vs. human membership (NOT code)

GitLab management splits cleanly. Verified 2026-06-30 by grepping every `.tf` in all four `grp-cfg/*` repos — **zero** `gitlab_project_membership` / `gitlab_group_membership` / `gitlab_user` / `protected_environment` resources exist.

**Layer 1 — Structure IS config-as-code** (`grp-cfg/*`, applied via `datasophia-glb-group` / `datasophia-glb-project` modules in `grp-comp`):
- Groups & projects (creation, settings): `cfg-iac-env/terraform/glb_group_res.tf`, `glb_project_res.tf`
- Branch protection by **role**: `cfg-iac-env/terraform/glb_branch_protection_res.tf` — `main` = maintainer push/merge, `dev`/`pre` = developer
- Per-project feature access levels (`environments_access_level`, `builds_access_level`, …): `glb_project_res.tf`
- **CI access tokens** (machine identities, multi-project pipelines): `cfg-app`

**Layer 2 — Human membership & roles are NOT config-as-code.** No CFG repo assigns humans to repos. You **cannot** open a CFG PR to grant a person access. Membership is manual, via GitLab **group-inheritance**: a person is added once to a group with a role (Reporter/Developer/Maintainer/Owner) and inherits it to every subgroup/project underneath.

> **Anti-pattern to avoid (the mistake this documents):** do NOT hunt for a CFG repo or propose a CFG PR to grant a human access to a repo. It does not exist by design. Human membership = manual UI + the Carl script below.

### How access is actually granted — the SOP

1. **Org-wide default access is a Datasophia-side script.** **Carl** (a Datasophia employee) runs an internal script we do **not** have access to. It grants a person **default Maintainer across ALL Klever repos** in one shot.
2. **Marc-André requests it from Carl.** MA cannot run the script himself; he asks Carl. (MA can also grant access *manually* in the GitLab UI as an interim/one-off because he holds Owner.)
3. **Once Gab has default Maintainer across all repos** (via the Carl script), **Gab self-serves per-repo grants** for teammates — Gab picks which repos each person (e.g. Sisi) gets, without going back to MA.

**Decision rule for "how do I give X access to repo Y?":**
- Is it *you* (Gab) needing broad access? → MA asks Carl to run the script (org-wide default Maintainer). One-time.
- Is it a teammate, and you already have Maintainer/Owner on the parent group? → **you grant it yourself** in the GitLab UI (Developer to run apply on `dev`, Maintainer for `main`). No MA, no Carl.
- You lack Owner/Maintainer on that group and it's urgent? → ask MA to grant manually as a one-off.

**Status as of 2026-06-30:** Sisi's access to `dac-gcp-back-biag` is already handled. Gab's org-wide default-Maintainer grant (via Carl's script, requested by MA) is the pending long-term fix that lets Gab self-serve future grants.
