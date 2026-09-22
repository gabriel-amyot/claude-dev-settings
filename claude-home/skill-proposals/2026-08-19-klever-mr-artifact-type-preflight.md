# Skill Proposal: klever-mr artifact-type-aware prod-promotion preflight
Date: 2026-08-19
Source: KTP-830 — promoting the DOOH client report (a zip-artifact FaaS repo) to prod

## Problem

`klever-mr`'s PROD-PROMOTION gate runs `promotion-image-preflight.sh`, which checks whether an
**image tag** exists in the approved Docker registry. It assumes every Klever app repo deploys a
Docker image.

FaaS / Cloud Function repos do not. They ship a **GCS zip**, and their DAC consumes it as
`storage_source { object = "<repo>/zip/<repo>_${var.artifact_tag_version}.zip" }`. The approved
registry holds **zero** images for them.

Result: the gate reports

```
🛑 RED — image tag app-dooh-client-report:0.5.1 does NOT exist in the approved registry.
   This is the version-bump-on-main trap. main does not BUILD; playing deploy-in-prod now → prod 502.
```

That verdict is a false negative. It recommends building a snapshot, which is meaningless for a zip
repo. A reader who trusts it either blocks a safe promotion or, worse, learns to ignore a red gate.

## Trigger

Any `/klever-mr` invocation where the MR targets `main`, i.e. the existing PROD-PROMOTION gate.

## Scope

Global — the `klever-mr` skill and `scripts/promotion-image-preflight.sh`.

## Draft steps

1. **Detect the artifact type** before choosing a check. Read the repo's DAC (or the app's
   `.gitlab-ci.yml`) for the deploy mechanism:
   - `storage_source` / `DATASOPHIA_INCL_ZIP_ARTIFACT_*` present → **zip artifact**
   - image / `cpe_cos_version` / `build_docker_tag_version` → **Docker image**
2. **Zip path:** assert the artifact exists for the version being promoted.
   ```bash
   gcloud storage ls "gs://${BUCKET}/${REPO}/zip/${REPO}_${VERSION}.zip"
   ```
   GREEN when present. RED when absent, with the correct remediation: merge to `dev` first and let
   its pipeline upload, because `main` never builds.
3. **Image path:** keep the current registry check unchanged.
4. **Never emit a verdict for an artifact type that was not detected.** If detection is ambiguous,
   report `CANT_VERIFY` and say which check was skipped. A confident wrong verdict is worse than an
   honest abstention — the whole point of the gate is that its output is trusted.
5. Record the two related FaaS pipeline facts in the skill body, since both bit during this ticket:
   - `bz-build-upload` runs on **dev only** (the `main` workflow rule leaves `BUILD_UPLOAD` at the
     global `"false"`), so promotion re-points rather than rebuilds — no 403 risk on promotion.
   - **Every** merge to `dev` needs a version bump, docs-only included, because the artifact name
     derives from the version and the CI service account lacks `storage.objects.delete`.

## Evidence

- `gcloud artifacts docker images list .../app-dooh-client-report` → `Listed 0 items.`
- `dac-gcp-report-doohrp` on `origin/main`, `terraform/cloudfunction.tf` → `storage_source`
- A docs-only MR merged to `dev` without a version bump broke the pipeline with
  `AccessDeniedException: 403 ... storage.objects.delete`, which is the failure the current gate
  claims to be about but checks in the wrong place.
