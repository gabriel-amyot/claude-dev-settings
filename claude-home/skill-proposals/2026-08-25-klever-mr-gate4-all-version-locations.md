# Skill Proposal: klever-mr Gate 4 — check EVERY version location, not just the version file
Date: 2026-08-25
Source: KTP-920 Chevron DOOH deliverable rebuild (session `lucid-pike`)

This is an **update to the existing `klever-mr` skill**, not a new skill.

## The failure it prevents

`klever-mr` Gate 4 reads the version from the repo's version file (`pom.xml`, `package.json`,
`pyproject.toml`) and compares it to `origin/dev`. On KTP-920 that gate passed cleanly:
`pyproject.toml` had been bumped 0.7.0 → 0.9.0, no tag collision, in sync with dev.

The dev pipeline then failed on upload:

```
gsutil -q cp app-dooh-client-report_0.7.0.zip gs://.../app-dooh-client-report_0.7.0.zip
AccessDeniedException: 403 sa-faas-app@... does not have storage.objects.delete access
```

**The artifact name does not come from the version file.** For a FaaS zip-artifact repo it comes from
`DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION`, hardcoded in `.gitlab-ci.yml`. That variable was still
0.7.0, so the build tried to overwrite the artifact the previous merge had published — and the CI
service account holds `objectCreator` and not `objectAdmin`, so an overwrite is a 403 rather than a
replace. Same immutability posture as the output buckets, which is correct and not the bug.

The gate reported PASS on a repo that could not build. It cost a failed pipeline, a follow-up branch,
an extra MR and an extra merge.

## The fix

Gate 4 currently reads one location. It should discover **all** of them and require they agree.

Detection, in addition to the existing version-file check:

```bash
# any hardcoded version-ish CI variable
grep -nE '_(TAG_)?VERSION[[:space:]]*:' .gitlab-ci.yml
```

For each hit whose value looks like a semver literal (not a `$VARIABLE` reference), treat it as a
version location that must equal the version file. When they disagree:

- **Auto-resolve** — set every location to the target version, exactly as Gate 4 already
  auto-bumps the version file. Report: "Bumped N version locations X.Y.Z → X.Y.Z+1:
  `pyproject.toml`, `.gitlab-ci.yml:DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION`."
- Fail only if a location cannot be parsed.

Also worth adding to the skill's repo-type table: a repo whose `.gitlab-ci.yml` includes
`datasophia-glb-incl-zip-artifact` is a **FaaS zip-artifact app repo**. Its artifact is named from a
CI variable, its `main` branch does **not** build (only `dev` sets `BUILD_UPLOAD`), and `main`
re-deploys an artifact a dev pipeline already published. That last point already has a gate
(PROD-PROMOTION), but the connection to the CI variable is not stated.

## Scope

Global — the skill lives at `~/.claude/skills/klever-mr/`.

## Draft Steps

1. Extend Gate 4's detection to enumerate every version location, version file plus semver literals
   in `.gitlab-ci.yml`.
2. Require agreement; auto-resolve all locations together on a bump.
3. Report the locations changed by name, so the human sees there was more than one.
4. Add the FaaS zip-artifact row to the repo-type table with the three consequences above.
5. Add the 403 signature to the skill's troubleshooting reference, since the error message names
   `storage.objects.delete` and reads like a permissions problem rather than a version problem.

## Notes

The permission posture is deliberate and must not be "fixed" by granting `objectAdmin`. The 403 is
the artifact bucket refusing to let a build overwrite a published artifact, which is the same
guarantee the deliverable buckets rely on. The bug is the stale version, not the missing permission.

There is an existing memory entry (`reference_klever_faas_version_bump_every_merge`) covering "FaaS
repos need a version bump on EVERY dev merge". It does not say the version lives in two places, which
is the part that actually broke. Update it alongside this.
