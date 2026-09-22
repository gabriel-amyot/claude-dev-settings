# Skill Proposal: capture-ui-screenshots-for-jira
Date: 2026-06-08
Source: KTP-759 DOOH detail-panel validation (needed Jira screenshot evidence)

## Trigger
When a frontend AC needs screenshot evidence attached to Jira (per the "Frontend ACs need screenshots" rule), and claude-in-chrome cannot produce a host-accessible file (its `save_to_disk` persists to the conversation store, not disk).

## Scope
Klever (frontend / Measurement Map), generalizable to any Klever Next.js UI.

## Why it's needed
claude-in-chrome is great for live inspection but its screenshots are NOT retrievable as files, so they can't be uploaded to Jira. Playwright against the local stack produces real PNG files at a path you control, at DPR 1 (no pixel-scale mismatch), and the local mock identity means no auth wall.

## Draft Steps
1. Verify the local stack is up (`:3000` frontend, `:8097` backend) — start via `start-stop-portal-in-local.sh` if not (frontend env: `IAP_IDENTITY_SOURCE=LOCAL_MOCK`, `DEV_FAKE_AUTH0_USER_ID=auth0|plat-001`, `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` from 1Password).
2. Write a Playwright script (CommonJS), run with `NODE_PATH=<worktree>/node_modules node script.cjs` so `@playwright/test` resolves. Viewport at DPR 1.
3. Navigate `localhost:3000/<route>`; drive the UI to the target state (select advertiser, toggle layers; use `window.mapObj`/`window.mapStore` on the local build for precise map control; open panels via store actions if a real click is hard).
4. `page.screenshot({ path: 'tickets/{PREFIX}/{EPIC}/{TICKET}/design/screenshots/<name>.png' })`.
5. Upload: `jira_skill.py upload-attachment {KEY} <path>`; reference in the comment with `!<name>.png|thumbnail!`.

## Notes
- Headless WebGL may leave the map canvas blank — fine if the evidence is an HTML panel (it renders regardless).
- Prefer ASCII-only data for clean shots (real venue names with en/em-dashes showed a UTF-8/Latin-1 mojibake — a separate bug).
