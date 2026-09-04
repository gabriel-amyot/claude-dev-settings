#!/usr/bin/env python3
"""Manage Mapbox Studio tilesets: list, status, replace, backup.

Companion to upload_tilesets.py. Reuses the SAME 1Password token-fetch
mechanism (get_mapbox_token, cached token file) so there is one source of
truth for credentials.

Subcommands
-----------
  list     List tilesets owned by an account (the Tilesets API).
  status   Report the state/progress/error of a single upload by upload id.
  replace  Re-upload an .mbtiles file into an EXISTING tileset id, replacing
           its contents in place (same Uploads flow as upload, but you name
           the target tileset id explicitly).
  backup   Reconstruct a re-uploadable .mbtiles from a HOSTED tileset by
           walking its tile pyramid via the Vector Tiles API. This is the
           ONLY way to back up a tileset whose source .mbtiles was lost:
           Mapbox provides no native tileset->mbtiles export (uploads are
           one-way). The backup captures the SERVED tiles (post-simplification,
           within the tileset's own minzoom..maxzoom), which is exactly what a
           restore (re-upload) would recreate. Use BEFORE deleting any tileset
           you cannot otherwise back up.

API references (documented public REST contracts):
  - List tilesets:  GET https://api.mapbox.com/tilesets/v1/{username}
        https://docs.mapbox.com/api/maps/mapbox-tiling-service/#list-tilesets
        Returns a JSON array of tileset objects. Documented fields used here:
        id, name, modified, type, visibility. Unknown/missing fields are
        rendered as "-" rather than assumed.
  - Upload status:  GET https://api.mapbox.com/uploads/v1/{username}/{upload_id}
        https://docs.mapbox.com/api/maps/uploads/#retrieve-upload-status
        Documented fields used here: id, complete, error, progress, tileset,
        created, modified, name.
  - Replace (upload):  the Uploads API replaces a tileset in place when an
        upload targets an existing tileset id. This is the same flow as a
        first-time upload; "replace" is just upload to a known id.
        https://docs.mapbox.com/api/maps/uploads/#create-an-upload
  - Backup (reconstruct):  TileJSON + Vector Tiles API.
        TileJSON metadata:  GET https://api.mapbox.com/v4/{tileset_id}.json
        Vector tile:        GET https://api.mapbox.com/v4/{tileset_id}/{z}/{x}/{y}.vector.pbf
        https://docs.mapbox.com/api/maps/vector-tiles/
        There is deliberately no Mapbox endpoint that returns the original
        uploaded .mbtiles. Reconstruction from served tiles is the documented
        workaround and the only one available.

Usage:
    python3 manage_tilesets.py list   [--prefix app-klever-mapbox] [--json] [--limit N]
    python3 manage_tilesets.py status <upload_id> [--prefix app-klever-mapbox] [--json]
    python3 manage_tilesets.py replace <file.mbtiles> --tileset-id app-klever-mapbox.county_boundaries
    python3 manage_tilesets.py backup  <tileset_id> [--output-dir DIR] [--max-zoom N]
"""

import argparse
import gzip
import json
import math
import os
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# Single-source the token logic from the proven upload script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upload_tilesets import get_mapbox_token, upload_one  # noqa: E402

API_BASE = "https://api.mapbox.com"


def _ssl_context():
    """Build an SSL context, preferring certifi's CA bundle when available.

    Some macOS Python installs lack a usable system CA bundle, which makes
    plain urllib calls fail with CERTIFICATE_VERIFY_FAILED. certifi (a
    dependency of many installed packages) provides a portable bundle.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _api_get(path, token, extra_params=None):
    """GET against the Mapbox API using stdlib urllib.

    Returns (status_code, parsed_json_or_text). On a non-2xx the body is
    returned as text so the caller can surface the real error.
    """
    params = {"access_token": token}
    if extra_params:
        params.update(extra_params)
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body
    except urllib.error.URLError as e:
        return 0, str(e)


def cmd_list(args):
    token = get_mapbox_token()
    # The Tilesets API caps page size at 500; expose --limit for the common case.
    params = {}
    if args.limit:
        params["limit"] = args.limit
    status, data = _api_get(f"/tilesets/v1/{args.prefix}", token, params)

    if status != 200:
        print(f"ERROR: list failed (HTTP {status}): {data}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    if not isinstance(data, list):
        # Defensive: documented response is a JSON array. If Mapbox returns
        # something else, show it raw rather than silently mis-parsing.
        print("Unexpected response shape (expected a JSON array):")
        print(json.dumps(data, indent=2))
        return

    if not data:
        print(f"No tilesets found for account '{args.prefix}'.")
        return

    print(f"Tilesets for '{args.prefix}' ({len(data)}):\n")
    print(f"  {'ID':<48} {'NAME':<28} {'MODIFIED'}")
    print(f"  {'-' * 48} {'-' * 28} {'-' * 24}")
    for ts in data:
        tid = ts.get("id", "-")
        name = ts.get("name", "-") or "-"
        modified = ts.get("modified", "-") or "-"
        print(f"  {tid:<48} {name[:28]:<28} {modified}")


def cmd_status(args):
    token = get_mapbox_token()
    status, data = _api_get(
        f"/uploads/v1/{args.prefix}/{args.upload_id}", token
    )

    if status != 200:
        print(
            f"ERROR: status failed (HTTP {status}): {data}", file=sys.stderr
        )
        sys.exit(1)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    complete = data.get("complete", False)
    error = data.get("error")
    progress = data.get("progress", 0)
    tileset = data.get("tileset", "-")

    if error:
        state = "FAILED"
    elif complete:
        state = "COMPLETE"
    else:
        state = "IN_PROGRESS"

    print(f"Upload {args.upload_id}")
    print(f"  state:    {state}")
    print(f"  progress: {progress * 100:.0f}%")
    print(f"  tileset:  {tileset}")
    if data.get("name"):
        print(f"  name:     {data['name']}")
    if data.get("created"):
        print(f"  created:  {data['created']}")
    if data.get("modified"):
        print(f"  modified: {data['modified']}")
    if error:
        print(f"  error:    {error}")
        sys.exit(1)


def cmd_replace(args):
    filepath = os.path.expanduser(args.file)
    if not os.path.isfile(filepath):
        print(f"ERROR: {filepath} is not a file", file=sys.stderr)
        sys.exit(1)
    if not filepath.endswith(".mbtiles"):
        print(
            f"WARNING: {filepath} does not end in .mbtiles", file=sys.stderr
        )

    tileset_id = args.tileset_id
    # Derive the account prefix from the tileset id (account.tileset_name).
    if "." not in tileset_id:
        print(
            "ERROR: --tileset-id must be in the form '<account>.<name>' "
            f"(got '{tileset_id}')",
            file=sys.stderr,
        )
        sys.exit(1)
    prefix = tileset_id.split(".", 1)[0]

    token = get_mapbox_token()

    try:
        from mapbox import Uploader
    except ImportError:
        print(
            "ERROR: mapbox package not installed. Run: pip3 install mapboxcli boto3",
            file=sys.stderr,
        )
        sys.exit(1)

    uploader = Uploader(access_token=token)

    print(f"Replacing tileset '{tileset_id}' in place...")
    # Reuse the proven single-file upload+poll path. Uploading to an existing
    # tileset id replaces its contents (Mapbox Uploads API semantics).
    result = upload_one(uploader, filepath, tileset_id, token, prefix)

    print(f"\nResult: {result.get('status')}")
    if result.get("status") != "OK":
        sys.exit(1)


def _deg2num(lon, lat, z):
    """Slippy-map tile (x, y) covering a lon/lat at zoom z (XYZ scheme)."""
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def _fetch_tile(tileset_id, z, x, y, token, ctx, retries=3):
    """Fetch one vector tile. Returns gzipped pbf bytes, or None if empty/absent."""
    url = (
        f"{API_BASE}/v4/{tileset_id}/{z}/{x}/{y}.vector.pbf"
        f"?access_token={urllib.parse.quote(token, safe='')}"
    )
    # Ask for gzip: mbtiles stores vector tiles gzip-compressed, so taking the
    # server's gzip bytes verbatim is the correct on-disk form.
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = resp.read()
                if not data:
                    return None
                # Normalize to gzip: if the server returned identity bytes
                # (no gzip magic), compress so the .mbtiles is spec-compliant.
                if data[:2] != b"\x1f\x8b":
                    data = gzip.compress(data)
                return data
        except urllib.error.HTTPError as e:
            if e.code in (404, 204):
                return None  # no tile here — expected across a pyramid
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    return None


def cmd_backup(args):
    tileset_id = args.tileset_id
    if "." not in tileset_id:
        print(
            "ERROR: tileset_id must be '<account>.<name>' "
            f"(got '{tileset_id}')",
            file=sys.stderr,
        )
        sys.exit(1)

    token = get_mapbox_token()
    ctx = _ssl_context()

    # 1) TileJSON metadata: zoom range, bounds, vector layers.
    tj_url = (
        f"{API_BASE}/v4/{tileset_id}.json"
        f"?access_token={urllib.parse.quote(token, safe='')}"
    )
    try:
        with urllib.request.urlopen(
            urllib.request.Request(tj_url), timeout=30, context=ctx
        ) as resp:
            tj = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: TileJSON fetch failed (HTTP {e.code}): {body}", file=sys.stderr)
        sys.exit(1)

    minzoom = int(tj.get("minzoom", 0))
    maxzoom = int(tj.get("maxzoom", 0))
    if args.max_zoom is not None:
        maxzoom = min(maxzoom, args.max_zoom)
    bounds = tj.get("bounds", [-180.0, -85.05, 180.0, 85.05])
    name = tj.get("name") or tileset_id.split(".", 1)[1]
    vector_layers = tj.get("vector_layers", [])

    out_dir = os.path.expanduser(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    short = tileset_id.split(".", 1)[1]
    mbtiles_path = os.path.join(out_dir, f"{short}.mbtiles")
    if os.path.exists(mbtiles_path):
        print(f"ERROR: {mbtiles_path} already exists (refusing to overwrite).", file=sys.stderr)
        sys.exit(1)

    print(f"Backing up {tileset_id}")
    print(f"  name:    {name}")
    print(f"  zoom:    {minzoom}..{maxzoom}")
    print(f"  bounds:  {bounds}")
    print(f"  layers:  {[l.get('id') for l in vector_layers]}")
    print(f"  output:  {mbtiles_path}")

    # 2) Build the .mbtiles (standard schema; tiles use the TMS row scheme).
    conn = sqlite3.connect(mbtiles_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE metadata (name TEXT, value TEXT);")
    cur.execute(
        "CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, "
        "tile_row INTEGER, tile_data BLOB);"
    )
    cur.execute(
        "CREATE UNIQUE INDEX tile_index ON tiles "
        "(zoom_level, tile_column, tile_row);"
    )

    # 3) Walk the pyramid within bounds at each zoom.
    tile_count = 0
    empty_count = 0
    safety_cap = args.max_tiles
    for z in range(minzoom, maxzoom + 1):
        x_min, y_max = _deg2num(bounds[0], bounds[1], z)  # SW -> min x, max y
        x_max, y_min = _deg2num(bounds[2], bounds[3], z)  # NE -> max x, min y
        if x_min > x_max:
            x_min, x_max = x_max, x_min
        if y_min > y_max:
            y_min, y_max = y_max, y_min
        z_tiles = 0
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if tile_count >= safety_cap:
                    print(
                        f"\nWARNING: hit --max-tiles cap ({safety_cap}); "
                        "stopping early. Increase --max-tiles to capture more.",
                        file=sys.stderr,
                    )
                    z = maxzoom + 1  # break outer
                    break
                data = _fetch_tile(tileset_id, z, x, y, token, ctx)
                if data is None:
                    empty_count += 1
                    continue
                tms_y = (2 ** z - 1) - y  # XYZ -> TMS row
                cur.execute(
                    "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?);",
                    (z, x, tms_y, sqlite3.Binary(data)),
                )
                tile_count += 1
                z_tiles += 1
            else:
                continue
            break
        print(f"  z{z}: {z_tiles} tiles", flush=True)

    # 4) Metadata (mbtiles spec + Mapbox vector requirements).
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2
    meta = {
        "name": name,
        "format": "pbf",
        "type": "overlay",
        "version": "1",
        "minzoom": str(minzoom),
        "maxzoom": str(maxzoom),
        "bounds": ",".join(str(b) for b in bounds),
        "center": f"{center_lon},{center_lat},{minzoom}",
        "description": (
            f"Backup of hosted Mapbox tileset {tileset_id}, reconstructed from "
            f"served vector tiles on {datetime.now(timezone.utc).date().isoformat()}. "
            "Mapbox has no native tileset export; this captures the served "
            "(post-simplification) tiles and is re-uploadable to restore."
        ),
        "json": json.dumps({"vector_layers": vector_layers}),
    }
    cur.executemany(
        "INSERT INTO metadata VALUES (?,?);", list(meta.items())
    )
    conn.commit()
    conn.close()

    size = os.path.getsize(mbtiles_path)
    print(f"\nWrote {tile_count} tiles ({empty_count} empty skipped) -> {mbtiles_path} ({size/1e6:.2f} MB)")
    if tile_count == 0:
        print("ERROR: no tiles captured; backup is empty.", file=sys.stderr)
        sys.exit(1)

    # 5) Append/refresh a manifest entry next to the backups.
    manifest_path = os.path.join(out_dir, "BACKUP_MANIFEST.json")
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = {"entries": []}
    manifest["entries"] = [e for e in manifest["entries"] if e.get("tileset_id") != tileset_id]
    manifest["entries"].append({
        "tileset_id": tileset_id,
        "hash": short,
        "name": name,
        "file": os.path.basename(mbtiles_path),
        "tiles": tile_count,
        "zoom": f"{minzoom}-{maxzoom}",
        "size_bytes": size,
        "backed_up": datetime.now(timezone.utc).isoformat(),
        "method": "reconstructed from served vector tiles (Mapbox has no native export)",
    })
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest updated: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage Mapbox Studio tilesets (list/status/replace)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List tilesets for an account")
    p_list.add_argument(
        "--prefix",
        default="app-klever-mapbox",
        help="Mapbox account/username (default: app-klever-mapbox)",
    )
    p_list.add_argument(
        "--limit", type=int, default=None, help="Max tilesets to return (<=500)"
    )
    p_list.add_argument("--json", action="store_true", help="Raw JSON output")
    p_list.set_defaults(func=cmd_list)

    p_status = sub.add_parser("status", help="Get status of an upload by id")
    p_status.add_argument("upload_id", help="Upload id returned at upload time")
    p_status.add_argument(
        "--prefix",
        default="app-klever-mapbox",
        help="Mapbox account/username (default: app-klever-mapbox)",
    )
    p_status.add_argument("--json", action="store_true", help="Raw JSON output")
    p_status.set_defaults(func=cmd_status)

    p_replace = sub.add_parser(
        "replace", help="Replace an existing tileset in place from an .mbtiles file"
    )
    p_replace.add_argument("file", help="Path to the .mbtiles file")
    p_replace.add_argument(
        "--tileset-id",
        required=True,
        help="Existing tileset id to replace, e.g. app-klever-mapbox.county_boundaries",
    )
    p_replace.set_defaults(func=cmd_replace)

    p_backup = sub.add_parser(
        "backup",
        help="Reconstruct a re-uploadable .mbtiles from a hosted tileset "
        "(the only way to back up a tileset whose source was lost)",
    )
    p_backup.add_argument(
        "tileset_id",
        help="Hosted tileset id to back up, e.g. app-klever-mapbox.2phw1xf2",
    )
    p_backup.add_argument(
        "--output-dir",
        default=".",
        help="Directory to write <name>.mbtiles + BACKUP_MANIFEST.json (default: cwd)",
    )
    p_backup.add_argument(
        "--max-zoom",
        type=int,
        default=None,
        help="Cap the maximum zoom captured (default: the tileset's own maxzoom)",
    )
    p_backup.add_argument(
        "--max-tiles",
        type=int,
        default=200000,
        help="Safety cap on total tiles fetched (default: 200000)",
    )
    p_backup.set_defaults(func=cmd_backup)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
