---
name: mapbox-upload
description: Upload .mbtiles tilesets to Mapbox Studio using the Python SDK and 1Password for token management. The Mapbox CLI is broken (Python compatibility issue with the Directions class), so this skill uses the mapbox.Uploader class directly. Use this skill whenever the user mentions uploading tilesets, pushing tiles to Mapbox, "upload to mapbox", "publish tilesets", deploying map tiles, or has .mbtiles files that need to go to Mapbox Studio. Also triggers when the user references tileset publishing, Mapbox tileset updates, or refreshing map layers after generating new tiles with tippecanoe.
nav:
  bay: ops
  when: uploading .mbtiles to Mapbox, tileset publishing, map tile deployment
  when_not: downloading tiles, generating tiles with tippecanoe, Mapbox GL JS styling
---

# Mapbox Tileset Upload

Upload .mbtiles files to Mapbox Studio. Handles token management via 1Password, batch uploads with progress polling, and optional tileset registry updates.

## Why this exists

The `mapbox` CLI (`mapbox upload`) is broken due to a Python compatibility issue in the `Directions` class import. The `mapbox` Python package's `Uploader` class works fine when called directly. This skill wraps that working path with 1Password integration and batch support.

## Prerequisites

```bash
pip3 install mapboxcli boto3
```

The `mapboxcli` package provides the `mapbox` Python module (including `mapbox.Uploader`). `boto3` is required by the uploader for S3 staging.

1Password CLI (`op`) must be installed and authenticated.

## Usage

```
/mapbox-upload <tiles-directory> [--prefix <mapbox-username>] [--dry-run]
```

**Arguments:**
- `<tiles-directory>` — path containing .mbtiles files (required)
- `--prefix` — Mapbox account prefix for tileset IDs (default: `app-klever-mapbox`)
- `--dry-run` — list what would be uploaded without actually uploading

## How it works

1. **Discover** all `.mbtiles` files in the given directory
2. **Derive tileset names** from filenames by stripping date stamps and feature-count suffixes (e.g., `county_boundaries_20260525_3514f_7pct.mbtiles` becomes `county_boundaries`)
3. **Fetch Mapbox token** from 1Password, cache to `/tmp/.mapbox_token_cache` to avoid repeated biometric prompts
4. **Upload each file** using `mapbox.Uploader`, poll for completion with progress reporting
5. **Print summary** table with tileset IDs and status
6. **Update tileset-registry.md** if one exists in or near the tiles directory

## Execution

Run the bundled script. Parse the user's arguments and pass them through:

```bash
python3 ~/.claude/skills/mapbox-upload/scripts/upload_tilesets.py \
  <tiles-directory> \
  --prefix <prefix> \
  [--dry-run]
```

Read the script's stdout for progress and results. If any upload fails, report the error and continue with remaining files (the script does not abort on individual failures).

## Tileset name derivation

The script strips these patterns from filenames to derive the tileset name:
- Date stamps: `_YYYYMMDD` (e.g., `_20260525`)
- Feature counts: `_NNNf` or `_NNNNf` (e.g., `_3514f`)
- Simplification hints: `_Npct` (e.g., `_7pct`)

So `zip_boundaries_20260525_35434f_5pct.mbtiles` becomes tileset ID `app-klever-mapbox.zip_boundaries`.

## 1Password token path

```
op://grp-client-portal-ui/app-mapbox/Saved on account.mapbox.com/cli-developer-management
```

This token has `uploads:write` scope. The script caches it at `/tmp/.mapbox_token_cache` (mode 0600) so `op read` only runs once per session.

## Tileset registry

If a `tileset-registry.md` file exists within 2 parent directories of the tiles directory, the script appends or updates entries after successful uploads. The registry is a markdown table tracking production tilesets. If no registry is found, the script skips this step silently.

## After uploading

Uploaded tilesets take a few minutes to process on Mapbox's side. The script polls until completion (up to ~7.5 minutes per tileset). Once processing finishes, the tilesets are immediately available in Mapbox Studio and via the Mapbox Tilesets API. Frontend code referencing these tileset IDs will pick up the new data on next load (no code changes needed if the tileset ID is unchanged).
