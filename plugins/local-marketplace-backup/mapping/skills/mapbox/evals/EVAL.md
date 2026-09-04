# mapping:mapbox — Eval Suite

Two layers. The automated layer (`eval_argparse.py`) is offline and runs with no
credentials. The live layer below requires a real Mapbox token and exercises the
three behaviours `SKILL.md` flags as still-unverified against the live API.

## 1. Offline — `eval_argparse.py` (automated, no token)

```bash
python3 ~/.claude/plugins/local-marketplace/mapping/skills/mapbox/evals/eval_argparse.py
```

Invokes `manage_tilesets.py` as a subprocess and asserts only the CLI parsing
contract:

- `--help` for the top level and each subcommand (`list`, `status`, `replace`)
  exits 0 and dumps no Python traceback.
- Each subcommand's help mentions its key option (`--prefix`, `upload_id`,
  `--tileset-id`).
- Missing required args, unknown subcommands, and unknown flags exit non-zero
  with a clean argparse usage error (no traceback).

It makes **no** Mapbox API calls and needs no 1Password token. The module-level
`from upload_tilesets import ...` is safe to import (stdlib only at import time;
the `mapbox` SDK import is lazy inside `cmd_replace`).

## 2. LIVE smoke checklist (manual, needs a real token)

These three behaviours cannot be verified offline because they depend on the
live Mapbox response shape. They mirror the "To live-test with a real token"
section of `SKILL.md`. Run them once a valid token is available.

Prerequisite: 1Password CLI authenticated, `mapbox` + `boto3` installed for the
`replace` step:

```bash
pip3 install mapboxcli boto3
op signin   # token is fetched via get_mapbox_token() from 1Password
```

Set the account once:

```bash
PREFIX="app-klever-mapbox"
SCRIPT=~/.claude/plugins/local-marketplace/mapping/skills/mapbox/scripts/manage_tilesets.py
```

### Uncertainty A — `list` field shape (`id` / `name` / `modified`)

`cmd_list` renders a JSON array using `id`, `name`, `modified`, falling back to
`-` for missing fields and printing the raw payload if the response is not a
list. Confirm the live shape matches.

```bash
python3 "$SCRIPT" list --prefix "$PREFIX" --limit 5
python3 "$SCRIPT" list --prefix "$PREFIX" --limit 5 --json
```

PASS when:
- The table prints real `ID` / `NAME` / `MODIFIED` values (not all `-`).
- The `--json` payload is a JSON **array** of objects, each carrying `id`,
  `name`, `modified` (this is the documented shape the table assumes).
- If you instead see "Unexpected response shape (expected a JSON array)", the
  live contract drifted — update `cmd_list` and `SKILL.md`.

### Uncertainty B — `status` progress is a `0..1` float

`cmd_status` prints `progress * 100` as a percentage and maps
`complete`/`error` to a state. Confirm `progress` is the documented `0..1`
float (not already a 0..100 percentage).

```bash
# Use an upload_id from a recent/in-flight upload.
UPLOAD_ID="<paste a real upload id>"
python3 "$SCRIPT" status "$UPLOAD_ID" --prefix "$PREFIX"
python3 "$SCRIPT" status "$UPLOAD_ID" --prefix "$PREFIX" --json
```

PASS when:
- The `--json` `progress` value is between `0` and `1` inclusive.
- The printed `progress: NN%` reads sensibly (e.g. raw `0.5` → `50%`). If raw
  `progress` is already `50` and the printout shows `5000%`, the multiply-by-100
  is wrong — fix `cmd_status` and `SKILL.md`.
- An errored upload prints `state: FAILED`, surfaces the `error`, and exits
  non-zero.

### Uncertainty C — `replace` overwrites a tileset in place

`cmd_replace` re-uploads an `.mbtiles` into an existing tileset id, relying on
Uploads-API semantics that replace contents in place rather than creating a
duplicate.

```bash
# Pick a NON-PRODUCTION tileset id to avoid disrupting the live map.
TARGET="$PREFIX.scratch_eval_tileset"
python3 "$SCRIPT" list --prefix "$PREFIX" --json   # note the target's `modified` before
python3 "$SCRIPT" replace /path/to/file.mbtiles --tileset-id "$TARGET"
python3 "$SCRIPT" list --prefix "$PREFIX" --json   # compare after
```

PASS when:
- After replace, `list` shows the **same** tileset id (no second/duplicate
  entry) with an updated `modified` timestamp.
- The command prints `Result: OK` and exits 0; a failed upload exits non-zero.

Warning: run `replace` only against a scratch/non-production tileset. It mutates
the live map layer.

## Updating after a live run

If any live uncertainty resolves differently than documented, update both
`scripts/manage_tilesets.py` (the rendering logic) and the "To live-test with a
real token" section of `SKILL.md`, then note the resolution here.
