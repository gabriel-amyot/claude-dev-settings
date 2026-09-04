# adtech:goldfish — Eval Suite

`adtech:goldfish` is a **procedural** skill: its working content is curl recipes and
field-mapping tables, not an importable code path. So the automated eval is a
**doc-completeness** check, not a functional one. The real functional test is a live
integration run (below), which needs the Goldfish API key.

## 1. Doc-completeness — `eval_completeness.py` (automated, no credentials)

```bash
python3 ~/.claude/plugins/local-marketplace/adtech/skills/goldfish/evals/eval_completeness.py
```

This skill was built from a live API spike (KTP-522 + KTP-748, re-verified 2026-06-03).
The eval guards that the gotchas that make the recipes *safe* survive future edits. It
reads `SKILL.md` and asserts:

- **Both mode headers present:** `fetch`, `plan`.
- **Every critical gotcha token survives:**
  - `{"inventory"` — the response-wrapping shape (drift trap: April contract was a flat
    array; the API now wraps every payload in a singular key).
  - `latitude` / `longitude` full-word params (`lat`/`lng` silently fail).
  - string-typed numerics (`cpm`, lat/lng) must be parsed.
  - `programmaticPlatformKey` — the BQ join to TTD `SITE` (its own bridge, not Placer).
  - pagination split — `/v2/inventory` does NOT paginate; `campaigns`/`data-plans` DO
    (`meta` / `nextUrl`).
  - `uid` header — both `x-api-key` AND `uid` are required.
  - `410` — v1 is retired; v2 only.
  - REST-direct decision — do NOT use the OAuth MCP.

Exits non-zero and lists any missing token. No network, no key.

This eval does **not** prove any curl recipe works live — it only proves the doc still
carries the knowledge needed to execute safely.

## 2. Manual functional checklist (needs the Goldfish key)

Requires read access to 1Password vault `grp-client-portal-ui`, item "Goldfish DOOH". The
key is not in `.env`.

1. **Auth + prerequisites:**
   ```bash
   GFKEY=$(op item get lptegkil5tsm5uqa6pzw7pdaue --fields credential --reveal)
   GFUID=$(op item get lptegkil5tsm5uqa6pzw7pdaue --fields username --reveal)
   curl -s -o /dev/null -w "HTTP:%{http_code}\n" \
     -H "x-api-key: $GFKEY" -H "uid: $GFUID" \
     "https://api.goldfishads.com/v2/media-types"
   ```
   Expect `HTTP:200` (401 → bad key/uid; 410 → used a v1 path).

2. **fetch — viewport:** `bash scripts/fetch_inventory.sh 43.6532 -79.3832 1`. Expect
   ~1k+ screens (Toronto), response unwraps the `inventory` key, lat/lng are strings.

3. **fetch — detail + lookups:** pull `/v2/inventory/{id}` (56-field object under
   `inventory`), confirm `programmaticPlatformKey` present; `bash scripts/fetch_lookups.sh`
   caches six tables (publishers ~455, slot-dimensions ~3,161).

4. **plan — availability:** aggregate a radius=5 fetch by `mediaTypeId`/`locationTypeId`.

5. **plan — buy-side:** `GET /v2/campaigns` returns `{"campaign":[...],"meta":{...}}`;
   confirm `meta.nextUrl` pagination (campaigns span >1 page); `/v2/advertisers` empty.

PASS when each step returns the documented shape and status codes. Capture outputs to a
ticket folder; do not paste large payloads into chat.
