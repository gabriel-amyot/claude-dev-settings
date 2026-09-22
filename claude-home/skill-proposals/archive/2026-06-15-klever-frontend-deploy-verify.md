# Skill Proposal: klever-frontend-deploy-verify
Date: 2026-06-15
Source: Measurement Map ship session (KTP-809/KTP-788)

## Trigger
"deploy frontend to dev", "ship to dev and verify", after merging a frontend MR to dev when the change must actually be live.

## Scope
org (Klever)

## Draft Steps
1. Confirm MR merged to dev; app pipeline built image app-front-portal:{version} (release-version success).
2. Play the manual `deploy-in-dev` bridge; wait for downstream DAC pipeline success.
3. Read the COS instance `gce-container-declaration` image tag (cpe-usea1b-d-front-portal-cos-hera / prj-d-global-front-6kpke3wn54). If still old, wait for metadata to update.
4. If desired tag set but container not serving it: `gcloud compute instances reset` the instance (dev only) to pull the new image.
5. Verify live: grep the served JS bundle for the new code string (ui-probe), hard-refresh. Report tag + verified-live.
