# klever-mr repo types, Gate 4 (version bump) and Gate 5 (CHANGELOG)

## Why the version and changelog gates exist

1. **Tag collision on app repos.** CI tags Docker images from the version in code. Two branches merging with the same version = second pipeline fails. Forgetting the version bump or changelog has happened repeatedly.
2. **Empty MR descriptions on any repo.** MR descriptions without WHY and WHAT are useless for reviewers. The skill synthesizes both from commit history so every MR ships with context.

## Repo types

| Type | Detection | Version gate | Changelog gate |
|------|-----------|-------------|----------------|
| **Java backend** | `pom.xml` at repo root | Required | Required |
| **Node frontend** | `package.json` at repo root | Required | Required |
| **Python app** | `pyproject.toml` at repo root (no `pom.xml`/`package.json`) | Required | Required-if-exists |
| **Infra/DAC/terraform** | none of the above | Skipped | Skipped |

**Python app repos matter:** Klever Python agent repos (e.g. `app-media-plan`, `app-agent-hub`) build a versioned Docker image and the CI's `bc-release-version` step runs `git tag $(poetry version --short)`. If the `[project] version` in `pyproject.toml` is not bumped between merges, the tag already exists and the pipeline fails on collision. So a `pyproject.toml` repo is an **app repo**, NOT infra. Do not skip the version gate for it. (Learned from KTP-735: `app-media-plan` was misclassified as infra, the version gate was skipped, and the release step later failed.)

Infra repos (paths containing `grp-dac`, `grp-cfg`, or repos with `.tf` files) have no versioned artifacts. Their pipelines run terraform, not Docker builds. Version bump and changelog gates do not apply.

**FaaS zip-artifact app repos** (`.gitlab-ci.yml` includes `datasophia-glb-incl-zip-artifact`) are app repos with a second version location: `DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION` names the uploaded zip. Every `dev` merge needs a bump in both places. Only `dev` builds (`BUILD_UPLOAD`). `main` re-points to a zip a dev pipeline already uploaded.

## Gate 4: Version bump (app repos only)

Infra/DAC skip report: "Gate skipped: version bump (infra/terraform repo, no versioned artifact)."

`scripts/version-locations.py` parses the version file (`pom.xml` project version, `package.json`, `pyproject.toml` `[project]` via TOML) and the CI release variables (`DATASOPHIA_INCL_*_TAG_VERSION`). Other semver CI variables (`UV_VERSION`) are listed as ignored and never edited.

```bash
python3 ~/.claude/skills/klever-mr/scripts/version-locations.py --repo . --ref origin/dev
python3 ~/.claude/skills/klever-mr/scripts/version-locations.py --repo .
```

Local version MUST be strictly greater than origin/dev's version (patch increment minimum). After any bump of the version file, run the second command with `--sync` so every CI release variable matches, then run it again without `--sync`. It must exit 0. Report each location the sync changed by name.

Tag collision check:

```bash
git tag --list "v*" | grep -F "<local-version>"
git tag --list | grep -F "<local-version>"
```

- **Versions equal, auto-resolve:** increment patch (X.Y.Z to X.Y.Z+1). For package.json, also run `npm install --package-lock-only` and include the lockfile change in the commit. For `pyproject.toml`, edit the `[project] version` line and, if a `uv.lock` is present at repo root, run `uv lock` (or note it needs regen) so the lockfile's project version tracks. Report: "Bumped version X.Y.Z → X.Y.Z+1."
- **Tag already exists, auto-resolve:** find the next available patch version and bump to that. Report: "Tag X.Y.Z exists, bumped to X.Y.N."
- **Multiple version files:** if both pom.xml and package.json exist, bump both. Verify both match.
- **Dev pipeline 403 `storage.objects.delete` on a zip upload:** a stale version, not a permission gap. The zip name still uses the old `DATASOPHIA_INCL_ZIP_ARTIFACT_TAG_VERSION`. Bump it (`--sync`). Never request `objectAdmin`: the bucket refuses overwrites on purpose.

## Gate 5: CHANGELOG.md (app repos only)

Infra/DAC skip report: "Gate skipped: CHANGELOG (infra/terraform repo)."

Read `CHANGELOG.md` at repo root. It must contain an entry for the local version:

```
## [X.Y.Z] - YYYY-MM-DD
```

The date should be today or recent (within 7 days). The entry must have content (at least one bullet under a category like Added/Changed/Fixed).

- **No CHANGELOG.md, Java backend / Node frontend:** STOP: "No CHANGELOG.md found at repo root."
- **No CHANGELOG.md, Python app:** required-if-exists, not a hard blocker. Report: "No CHANGELOG.md in this Python repo. Skipping the changelog gate (the version bump above is the gate that prevents the tag collision). Consider adding one." Do NOT stop.
- **No entry for current version, auto-resolve:** add a `## [X.Y.Z] - YYYY-MM-DD` section with entries from `git log --reverse --format="- %s" origin/dev..HEAD`. Report: "Added CHANGELOG entry for X.Y.Z."
- **Empty entry, auto-resolve:** populate from commit subjects. Report what was added.

Commit every auto-resolved fix with `{TICKET-ID}: pre-MR housekeeping (version bump, changelog)` before pushing.
