---
name: mapbox
description: "Mapbox Studio API integration — publish and manage tilesets. Uploads .mbtiles via the mapbox Python Uploader (the CLI is broken), with 1Password token management and batch progress polling. Modes: upload, list, replace, status. Trigger: 'upload to mapbox', 'publish tilesets', 'push tiles to mapbox', 'deploy map tiles', 'refresh map layers', 'mapbox studio'."
nav:
  bay: ops
  when: "Publishing or managing tilesets in Mapbox Studio: upload .mbtiles, list/replace tilesets, poll upload status."
  when_not: "Generating/validating .mbtiles (use mapping:tileset). Mapbox GL JS styling (see the mapbox-* pattern skills)."
---

# mapping:mapbox — Mapbox Studio API Integration

Publishes `.mbtiles` (the output of `mapping:tileset`) to Mapbox Studio and manages
tilesets there. The last step of the tileset pipeline, but a distinct concern: a
vendor **API integration** with its own modes.

> **Migrated from `mapbox-upload`.** All four modes are implemented against the
> Mapbox Uploads/Tilesets REST APIs. `upload` is the proven path; `list` / `status`
> / `replace` live in the companion `manage_tilesets.py` and reuse the same
> 1Password token-fetch.

## Why the bundled script exists
The `mapbox` CLI (`mapbox upload`) is broken (Python import issue in `Directions`).
The `mapbox` Python package's `Uploader` class works when called directly; the
bundled script wraps that working path with 1Password integration and batch support.

## Prerequisites
```bash
pip3 install mapboxcli boto3
```
- `upload` / `replace` need the `mapbox` Python package (`Uploader`) + `boto3` (S3 staging).
- `list` / `status` use only the Python stdlib (`urllib`), no extra deps.
- 1Password CLI (`op`) installed and authenticated (token fetch). Both scripts share
  the same `get_mapbox_token()` (1Password `op read` → cached token file).

### 1Password token path
```
op://grp-client-portal-ui/app-mapbox/Saved on account.mapbox.com/cli-developer-management
```
This token has `uploads:write` scope. `get_mapbox_token()` caches it at
`/tmp/.mapbox_token_cache` (mode 0600) so `op read` runs only once per session.

## Modes

| Mode | Status | Script | Does |
|---|---|---|---|
| `upload` | ✅ real | `upload_tilesets.py` | Discover `.mbtiles` in a dir, derive tileset names, fetch token from 1Password, upload via `mapbox.Uploader`, poll to completion, print summary. |
| `list` | ✅ real | `manage_tilesets.py list` | List the account's tilesets (`GET /tilesets/v1/{username}`), print id / name / modified. |
| `status` | ✅ real | `manage_tilesets.py status` | Report state/progress/error of one upload by id (`GET /uploads/v1/{username}/{upload_id}`). |
| `replace` | ✅ real | `manage_tilesets.py replace` | Re-upload an `.mbtiles` into an existing tileset id, replacing it in place (same Uploads flow, explicit target id). |
| `backup` | ✅ real | `manage_tilesets.py backup` | Reconstruct a re-uploadable `.mbtiles` from a HOSTED tileset by walking its tile pyramid (TileJSON + Vector Tiles API). The **only** way to back up a tileset whose source `.mbtiles` was lost — Mapbox has no native tileset→mbtiles export (uploads are one-way). Captures the *served* (post-simplification) tiles; re-uploadable to restore. Stdlib-only + writes a `BACKUP_MANIFEST.json`. |

## Execution

### upload — publish all `.mbtiles` in a directory
```bash
python3 ~/.claude/plugins/local-marketplace/mapping/skills/mapbox/scripts/upload_tilesets.py \
  <tiles-directory> \
  --prefix <mapbox-username> \
  [--dry-run]
```
`--prefix` is the Mapbox account prefix for tileset IDs (default: `app-klever-mapbox`).
Reads stdout for progress; does not abort on individual file failure (reports and
continues). Updates a tileset registry if one exists near the tiles dir (see below).

### list — show existing tilesets
```bash
python3 ~/.claude/plugins/local-marketplace/mapping/skills/mapbox/scripts/manage_tilesets.py \
  list --prefix <mapbox-username> [--limit 100] [--json]
```

### status — poll one upload by id
```bash
python3 ~/.claude/plugins/local-marketplace/mapping/skills/mapbox/scripts/manage_tilesets.py \
  status <upload_id> --prefix <mapbox-username> [--json]
```
Exits non-zero if the upload reported an error.

### replace — refresh one tileset in place
```bash
python3 ~/.claude/plugins/local-marketplace/mapping/skills/mapbox/scripts/manage_tilesets.py \
  replace <file.mbtiles> --tileset-id <mapbox-username>.<tileset_name>
```
The account prefix is derived from `--tileset-id`. Uploading to an existing id
replaces its contents (Mapbox Uploads semantics).

### backup — reconstruct an `.mbtiles` from a hosted tileset (download-before-delete)
```bash
python3 ~/.claude/plugins/local-marketplace/mapping/skills/mapbox/scripts/manage_tilesets.py \
  backup <mapbox-username>.<tileset_id> \
  --output-dir <dir> [--max-zoom N] [--max-tiles N]
```
**Why this exists:** Mapbox uploads are one-way. There is no endpoint that returns the
original `.mbtiles` you uploaded. The only recovery path for a tileset whose source file
was lost is to walk its tile pyramid via the Vector Tiles API and repack the served tiles
into a fresh `.mbtiles`. Use this **before deleting** any tileset you cannot otherwise back up.

- Reads TileJSON (`GET /v4/{id}.json`) for zoom range, bounds, and vector layers.
- Fetches each tile (`GET /v4/{id}/{z}/{x}/{y}.vector.pbf`) within bounds, minzoom..maxzoom.
- Writes a standard `.mbtiles` (TMS row scheme, gzipped pbf, full metadata) + appends to
  `BACKUP_MANIFEST.json` (tileset id, hash, name, tile count, zoom, date, method).
- **Caveat:** captures the *served* (post-simplification) tiles within the tileset's own
  zoom range, not the original source geometry. This is exactly what a re-upload restores.
- Verify a backup by serving it with Martin (`martin <file>.mbtiles`) and fetching a tile,
  or decode a stored tile with `mapbox_vector_tile`.
- Refuses to overwrite an existing output file. `--max-tiles` (default 200000) is a safety cap.

## API endpoints used
- List:    `GET https://api.mapbox.com/tilesets/v1/{username}` (Tilesets API)
- Status:  `GET https://api.mapbox.com/uploads/v1/{username}/{upload_id}` (Uploads API)
- Backup:  `GET https://api.mapbox.com/v4/{tileset_id}.json` (TileJSON) + `GET https://api.mapbox.com/v4/{tileset_id}/{z}/{x}/{y}.vector.pbf` (Vector Tiles API)
- Upload/replace: `mapbox.Uploader.upload(src, tileset_id)` → Uploads API create + S3 stage.

## To live-test with a real token
- `list` parses a documented JSON array using fields `id` / `name` / `modified`; if
  the live shape differs, the script prints the raw payload instead of guessing.
- `status` maps `complete` / `error` / `progress` to a state; confirm progress is the
  documented `0..1` float (the printout multiplies by 100).
- `replace` relies on the Uploads API replacing in place when targeting an existing
  tileset id; verify the existing tileset's contents are overwritten (not duplicated).

## Tileset name derivation
`upload` derives the tileset name from each `.mbtiles` filename by stripping:
- Date stamps: `_YYYYMMDD` (e.g. `_20260525`)
- Feature counts: `_NNNf` / `_NNNNf` (e.g. `_3514f`)
- Simplification hints: `_Npct` (e.g. `_7pct`)

So `zip_boundaries_20260525_35434f_5pct.mbtiles` → tileset id
`app-klever-mapbox.zip_boundaries`.

## Tileset registry
If a `tileset-registry.md` exists **within 2 parent directories** of the tiles
directory, the script appends/updates its entries after successful uploads (a
markdown table tracking production tilesets). If none is found, it skips silently.

## After uploading
Uploaded tilesets take a few minutes to process Mapbox-side; the script polls until
completion (**up to ~7.5 minutes per tileset**). Once done, tilesets are immediately
available in Mapbox Studio and via the Tilesets API. Frontend code referencing the
tileset IDs picks up new data on next load — **no code changes needed if the tileset
ID is unchanged.**

## Pipeline position
`mapping:tileset` (prepare → validate-tiles) → **`mapping:mapbox` (upload)** → live map layer.
