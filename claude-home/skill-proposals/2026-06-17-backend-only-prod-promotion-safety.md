# Skill Proposal: backend-only-prod-promotion-safety
Date: 2026-06-17
Source: KTP-758 DOOH prod incident — backend dev→prod merge-safety analysis

## Trigger
User wants to promote a Klever backend (e.g. app-proximity-report) from dev to prod
*without* also promoting the frontend, and asks "is it safe to merge to prod / will
this break anything". Also: any backend-ahead-of-frontend promotion question.

## Scope
org (Klever)

## Draft Steps
1. Compute the delta: `git log origin/main..origin/dev --oneline` + version diff (pom.xml/package.json) + CHANGELOG between versions. Classify each ticket: additive / removal / data-dependency.
2. For every REMOVED endpoint or behavior: `git grep` the DEPLOYED prod frontend (`origin/main` of app-front-portal) for callers. Zero callers ⇒ safe; any caller ⇒ blocker (would 404 the prod FE).
3. For every NEW BQ table / dataset dependency: `bq show prj-p-...:dataset.table` to confirm it exists and is populated in the PROD dataset.
4. Added response fields ⇒ additive/safe (old FE ignores them). Flag only backend REMOVALS of fields the prod FE reads.
5. Report a per-ticket safety table + the promotion mechanics (app repo dev→main MR; prod deploy via DAC cpe_cos_version; "Done" only after DAC deploy + prod verification).
6. Offer to open the dev→main MR via /klever-mr (stop at MR; human drives merge + DAC bump).
