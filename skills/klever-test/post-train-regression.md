# Post-Train Prod Regression (klever-test mode 7)

Validate **app-front-portal on prod after a dev→prod release train lands**. Two layers:

1. **Always-on core smoke** — a fixed set that runs EVERY time, independent of the diff. This is the "did a major thing break even though the train didn't touch it" guard. Do not skip it because the diff looks small.
2. **Diff-targeted feature checks** — inferred from the train's actual code delta, so you validate exactly the features that shipped without re-running the world.

This is the interim, human-in-the-loop form of what becomes validation-as-code in the front-portal CICD (see the plan: `documentation/architecture/portal-regression-cicd-plan.md`). It reuses **ui-probe** for live execution and the existing **Playwright suite** (`npm run test:e2e`) as the long-term core.

## When to use

- Right after a portal release train deploys to prod (the moment `deploy-in-prod` → DAC `apply in prod` lands a new front-portal image).
- Trigger phrases: "post-train regression", "validate the portal after the train", "did the release break anything", "regression after prod deploy".
- NOT for local dev debugging (use ui-probe directly) or a single ticket's AC (mode 2).

## Preconditions (verify FIRST — a stale build invalidates everything)

1. Confirm the **served prod build** matches the just-shipped version:
   `gcloud compute instance-templates describe <live front-portal template> --format="value(properties.metadata.items)" | grep -o 'app-front-portal:[0-9.]*'`
   (get the live template from the MIG: `gcloud compute instance-groups managed describe igm-p-front-portal-usea1-front-portal --project=prj-p-global-front-fv4vnsj20b --region=us-east1 --format="value(versions[0].instanceTemplate)"`).
2. Backend versions that shipped in the train are live + healthy (proximity-report / user-management as applicable).
3. You are logged into prod as a **@beklever.com** account (holds the `Internal` UM component) — needed for mode-switcher / permission checks.
4. If a feature is data-backed and the data rebuilds on a schedule (dataform), confirm the rebuild ran since the data change merged.

If a precondition fails, STOP and report — do not test a stale build.

## Step 1 — compute the train delta and infer the plan

The delta is the git range between the **previously deployed prod build** and the **newly deployed prod build**. By deployed tags is cleanest:

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal && git fetch origin
python3 ~/.claude/skills/klever-test/scripts/train-diff-to-testplan.py \
  --repo . --range <old_prod_tag>..<new_prod_tag> --json > /tmp/portal-testplan.json
# human view:
python3 ~/.claude/skills/klever-test/scripts/train-diff-to-testplan.py --repo . --range <old>..<new>
```

If the train was a merge (not a clean tag bump), use `origin/main..origin/dev` at assembly time, or `<prev_main_sha>..<new_main_sha>`. The script:
- emits **core_smoke** (always) + **targeted_areas** (only what changed),
- lists **unmapped_code_files** — eyeball these; if a genuinely new feature area appears, extend `FEATURE_MAP` in the script (that's how the inference gets smarter over time).

**Read the plan critically.** The inference is a starting point, not gospel. If you know the train shipped a behaviour the file-map didn't catch (e.g. a pure copy change, or a backend-only feature whose UI lives elsewhere), add it manually.

## Step 2 — execute on prod via ui-probe

Load `ui-probe` and run, in order:
1. **Core smoke** (every check in `core_smoke`). One proof screenshot for the map smoke; record served versions.
2. **Each targeted area**: drive its `checks` live, one proof screenshot per area, capture `/api/*` status + console for errors.
3. Negative checks matter: mode-switcher must be ABSENT for a client login; demo spotlight must be OFF outside Demo. A feature that should be hidden and isn't is a failure.

**Data-layer gate (KTP-739 lesson — do not skip).** For any area with a `data_layer` block, verify the data source BEFORE you judge the UI. A panel that renders nothing can be (a) a UI regression or (b) an empty/missing data table — these are different findings. Query BQ read-only (like the TC6 pattern) to confirm the table exists and has rows for the entity under test. If the data isn't there, the verdict is "data not wired," not "UI pass" and not "UI fail" — file it as its own follow-up (see the AI Insights handoff for the template).

## Step 3 — report

Per-TC table: `core smoke` rows + one row per targeted area, each PASS / FAIL / BLOCKED / DATA-GAP with a proof path. Any FAIL → open a bug linking the shipping MR (draft on disk → `/post-comment` for approval; never post inline). Save evidence under the session's `evidence/` folder or the ticket folder.

Record, always: served front-portal build, backend versions, dataform rebuild timestamp (if relevant), and which targeted areas ran vs were skipped (and why) — silent scope-narrowing reads as "all clear" when it isn't.

## What this mode deliberately does NOT do (yet)

- It does not run in CI — it's driven by a human/agent post-deploy. Wiring the Playwright suite + these checks into the front-portal pipeline is the long-term target (the plan doc).
- It does not exhaustively test every feature every time — the always-on core is the fixed safety net; the rest is diff-scoped. That's the deliberate trade for speed until validation-as-code exists.
- It does not judge UX (use mode 4, Sally) or review code (use /crit).

## Files

- `scripts/train-diff-to-testplan.py` — diff → feature areas → plan (the inference core; `FEATURE_MAP` + `AREAS` are the knobs to extend).
- Long-term anchor: the Playwright specs in `app-front-portal/e2e/*.spec.ts` (each targeted area lists the spec that covers it).
