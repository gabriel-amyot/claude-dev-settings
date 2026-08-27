# Klever Shipping Workflow

On-demand context: load when tagging, shipping, deploying, creating MRs, or reviewing PRs.

## Branch Lifecycle

1. Branch from `dev` as `KTP-XXX-short-description` (no fix/feature/chore prefixes)
2. Merge `origin/dev` INTO your branch regularly. Never merge your branch into dev directly.
3. Protected branches (dev, main) reject direct pushes. Always feature branch + MR.

## Before Merging

1. **Bump patch version** in code (`package.json` for frontend, `pom.xml` for backend). CI fails on tag collision if you forget.
2. **Update CHANGELOG.md** with the version entry.
3. **MR target:** `INS-205` for all KTP-115 feature work. `dev` for everything else.

## CI/CD Behavior

- CI reads version from code, builds Docker image with that tag automatically.
- DAC pipeline applies terraform which reads the image tag.
- **Never change CI/CD variables manually.** Variables like `TF_VAR_build_docker_tag_version` (frontend, DAC ID 514) and `TF_VAR_cpe_cos_version` (backend, DAC ID 580) are set by the pipeline from code version.
- Never rollback. Always increment forward.
- If pipeline shows "manual" status, it may need a manual trigger (click Play in GitLab).

## Deploy Steps

### Pre-Deploy
1. Code merged to target branch on GitLab
2. Pipeline passes (unit tests green)
3. Version bumped, CHANGELOG updated

### Post-Deploy Verification
1. Check COS instances are RUNNING: `gcloud compute instances list --project=<project> --filter="name~<service>"`
2. Start if TERMINATED: `gcloud compute instances start <name> --zone=us-east1-b --project=<project>`
3. SSH tunnel: `cd grp-app/grp-frontend/app-front-portal && bash gcp-connect.sh`
4. Health check: `curl localhost:8097/proximity-report/actuator/health`

## `main` never builds — the version-bump-on-main trap (2026-07-29 prod outage)

Klever app repos: `dev` pipelines **build** the image (`bd-build-upload` + `bd-scan-move` → approved registry). `main` pipelines **do not build** — they run `set-version` + `configure-dac` + `deploy`, i.e. they re-deploy an image that already exists. So **main's version must always name an already-built image.**

Only two valid ways to get one:
1. **Full promotion** — send a `dev` version to `main`; dev already built its image.
2. **Snapshot** — branch off `main`, run `KLEVER_DEPLOY_SNAPSHOT=prod` (a feature branch, not main/dev); it builds a `X.Y.Z-SNAPSHOT-<ts>` image, scans, moves to approved, deploys.

**The trap:** cherry-pick onto `main` + bump `package.json`/`pom.xml` to a NEW version number → `main` configures+deploys a tag no pipeline ever built → prod 502. It is not the cherry-pick that breaks it; it is inventing a version on `main`.

**Preflight before any `main`-targeted deploy:**
```bash
bash ~/.claude/skills/klever-mr/scripts/promotion-image-preflight.sh --repo <repo> --ref <ref>
```
RED = tag absent = do NOT play deploy-in-prod. GREEN = image exists, safe to deploy. Wired into `klever-mr`'s prod-promotion gate.

## Common Issues
- **BQ 500 on dev but works locally:** COS SA lacks dataset-level access. Fix via DAC terraform (import.tf + dataset_iam.tf).
- **COS TERMINATED:** Instances shut down at ~3 AM daily. Start them manually.
- **Tunnel fails "failed to connect to backend":** COS is down or restarting. Start it first.
- **Tag collision:** Always bump version before merging. CI fails if the tag already exists.

## GitLab Instances
- Klever repos: `cicd.prod.datasophia.com` (behind GCP IAP)
- Origin8/Supervisr repos: `gitlab.prod.origin8cares.com` (separate IAP)
- IAP cookie file: `~/.config/git-gcp-iap/gamyot-beklever@cicd.prod.datasophia.com.cookie`
- If GitLab API returns 403, run `git fetch` on any Klever repo to refresh the IAP cookie.

## Shipping Safeguards (from global CLAUDE.md)
- Do NOT run GitLab pipelines from Claude in PROD or UAT (DEV is OK)
- Do NOT update GitLab CI/CD variables from Claude in PROD or UAT (DEV is OK)
- Do NOT run terraform plan/apply
- IAM/Auth changes require human gate before committing
- Create MR immediately after pushing. No exceptions.
