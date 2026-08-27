# Next.js Static Export on Cloudflare Pages — Build Gotchas

Cross-project knowledge. Applies to any Next.js (`output: 'export'`) site deployed to Cloudflare Pages. Learned 2026-06-05 debugging compostelaguide.com search (404 index in prod despite a green local build).

## 1. Cloudflare Pages skips npm lifecycle hooks

Cloudflare Pages' build command is whatever is set in the Pages dashboard — commonly a **bare `npx next build`**, NOT `npm run build`.

`prebuild` / `postbuild` are **npm lifecycle hooks** — they run only when you invoke `npm run build`. A bare `next build` runs them **never**. So any build artifact you generate from a `prebuild` script (search index, sitemap, feed, etc.) is **silently absent in production** while working perfectly in local `npm run build`.

**Symptom:** the artifact 404s in prod (`/search-index.json` → 404, `content-type: text/html`, `cf-cache-status: DYNAMIC`). Client features that fetch it return nothing.

**Fix (robust, code-only):** generate the artifact from `next.config.ts` during the production phase, so it runs regardless of how the build is triggered:
```ts
import { PHASE_PRODUCTION_BUILD } from 'next/constants'
import { generateSearchIndex } from './scripts/searchIndex'
const nextConfig = async (phase: string): Promise<NextConfig> => {
  if (phase === PHASE_PRODUCTION_BUILD) await generateSearchIndex()
  return { output: phase === PHASE_PRODUCTION_BUILD ? 'export' : undefined, /* ... */ }
}
```
Files in `public/` are copied into `out/` after config resolves, so generating into `public/` from the (awaited) async config guarantees inclusion. Keep the `prebuild` CLI too for `npm run build` users — the generator is idempotent. The config function may be invoked once per build process, so the generator can run a few times; make it idempotent.

**Fix (alternative):** set the Pages build command to `npm run build`. Simple, but breaks again if someone resets it — prefer the code-only fix or do both.

## 2. Verification gap: local `npm run build` ≠ the prod build command

A green local `npm run build` does **not** prove the prod build works, because the deploy platform may run a different command. When verifying a build-TIME artifact, run the **exact** command the platform uses (for CF Pages, often `npx next build`), after deleting any stale local copy of the artifact.

## 3. Diagnosing "deployed but not working" on Cloudflare Pages

A read-only Cloudflare API token (account id + token, e.g. in a project `.env.local`) is enough to get ground truth:
- **Build config:** `GET /accounts/{acc}/pages/projects/{project}` → `result.build_config.build_command`, `result.source.config.production_branch`. This reveals whether `npm run build` vs `npx next build` is used.
- **Deployments:** `GET /accounts/{acc}/pages/projects/{project}/deployments?per_page=N` → `latest_stage.{name,status}` (queued→build→deploy→success) and `deployment_trigger.metadata.{branch,commit_hash,commit_message}`. Confirms the live commit and whether the deploy finished.

Always confirm the live deployment is the commit you expect before concluding a fix didn't work — and check the artifact URL's actual HTTP status, not just the page.

## 4. FR-at-root i18n + static export

When French is served at the root (no `/fr` prefix) and EN/PT are prefixed: build-time indexes/data should store **locale-less slugs**, and the client prefixes them at use time via the shared `localizedHref` helper (the same one nav links use). Root paths resolve in prod via `public/_redirects` rewrites (`/itineraires → /fr/itineraires 200`); these rewrites do NOT exist in `next dev`, so FR-at-root navigation only fully works in the deployed build — matching existing nav-link behavior, not a regression.
