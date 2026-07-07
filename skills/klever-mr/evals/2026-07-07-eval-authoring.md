# klever-mr — Layer B eval authoring note

**Date:** 2026-07-07
**Layer:** B (behavioral, transcript-gradeable)
**Suite:** `evals/evals.json` — 5 evals
**Schema:** skill-creator `evals.json` (`skill_name` + `evals[]` with `id`, `prompt`, `expected_output`, `files`, `expectations`)

## What each eval covers

1. **Java repo, no version bump** — pom.xml present, local version == origin/dev, stale CHANGELOG. Asserts the version + CHANGELOG gates are enforced (not skipped) for an app repo and the MR does not ship a colliding version.
2. **Infra/DAC repo** — no version file, path contains `grp-dac`. Asserts the version + CHANGELOG gates are skipped *with an explicit skip report*, WHY/WHAT are still produced, target = dev.
3. **Tag collision** — version bumped but tag already exists. Asserts the tag-collision check fires and bumps to the next free patch.
4. **MR description content** — Node frontend, ready. Asserts Why/What/Tickets/Commits/Test-plan sections, WHY = problem not solution, ticket link from branch name, package-lock sync.
5. **Protected-branch guard** — on `dev`. Asserts Gate 2 structural failure: report and STOP, no push, no MR.

## Fixtures (`evals/files/`)

- `pom.xml` — minimal Java backend pom, `<version>1.4.2</version>` (matches eval 1's scenario).
- `CHANGELOG.md` — top entry `[1.4.2]`, i.e. NOT ahead of the version, so eval 1's "add the missing entry" behavior has something to correct.

## Contradiction surfaced (IMPORTANT)

The lead's brief said the Java/no-bump case should have the agent **"BLOCK the MR, demand version bump + CHANGELOG before proceeding."** The SKILL.md's actual documented behavior for a missing version bump / missing CHANGELOG entry is **check-and-fix / auto-resolve** (Gate 4: "auto-resolve: increment patch"; Gate 5: "auto-resolve: add a CHANGELOG entry"), not a hard block. A true hard-block expectation would fail a correct run.

**Resolution:** Eval 1's expectations assert the load-bearing invariant that is true under *both* readings — the gate is enforced and no MR ships with a colliding/un-bumped version — while accepting the auto-bump-to-1.4.3 + CHANGELOG-populate path the SKILL.md actually documents. The only genuinely hard-blocking (report-and-stop) case in klever-mr is a *structural* failure (wrong branch / no repo), which is covered separately by eval 5.
