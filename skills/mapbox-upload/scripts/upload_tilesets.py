#!/usr/bin/env python3
"""Upload .mbtiles tilesets to Mapbox Studio.

Uses the mapbox Python SDK's Uploader class directly because the CLI shim
is broken (Python compatibility issue with the Directions class import).

Token is fetched from 1Password and cached to avoid repeated biometric prompts.

Usage:
    python3 upload_tilesets.py <tiles-dir> [--prefix app-klever-mapbox] [--dry-run]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

OP_URI = (
    "op://grp-client-portal-ui/app-mapbox/"
    "Saved on account.mapbox.com/cli-developer-management"
)
TOKEN_CACHE = "/tmp/.mapbox_token_cache"


def get_mapbox_token():
    """Fetch Mapbox secret token from 1Password, with local file cache."""
    if os.path.exists(TOKEN_CACHE):
        with open(TOKEN_CACHE) as f:
            token = f.read().strip()
            if token:
                return token

    print("Fetching Mapbox token from 1Password...")
    result = subprocess.run(["op", "read", OP_URI], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: op read failed: {result.stderr.strip()}", file=sys.stderr)
        print("Make sure 1Password CLI is installed and authenticated.", file=sys.stderr)
        sys.exit(1)

    token = result.stdout.strip()
    with open(TOKEN_CACHE, "w") as f:
        f.write(token)
    os.chmod(TOKEN_CACHE, 0o600)
    print("Token cached.")
    return token


def derive_tileset_name(filename):
    """Strip date stamps, feature counts, and simplification hints from filename.

    Examples:
        county_boundaries_20260525_3514f_7pct.mbtiles -> county_boundaries
        state_centers_20260525_69f.mbtiles -> state_centers
        zip_boundaries.mbtiles -> zip_boundaries
    """
    name = Path(filename).stem
    # Strip date stamps like _20260525
    name = re.sub(r"_\d{8}", "", name)
    # Strip feature counts like _3514f or _69f
    name = re.sub(r"_\d+f", "", name)
    # Strip simplification hints like _7pct or _10pct
    name = re.sub(r"_\d+pct", "", name)
    # Clean up any trailing underscores
    name = name.strip("_")
    return name


def find_tileset_registry(tiles_dir):
    """Look for tileset-registry.md in the tiles dir or up to 2 parents."""
    search = Path(tiles_dir).resolve()
    for _ in range(3):  # current + 2 parents
        candidate = search / "tileset-registry.md"
        if candidate.exists():
            return candidate
        search = search.parent
    return None


def update_registry(registry_path, tileset_id, tileset_name, filename, status):
    """Append or update an entry in the tileset registry."""
    if status != "OK":
        return

    content = registry_path.read_text()
    today = time.strftime("%Y-%m-%d")
    entry_line = f"| `{tileset_id}` | `{tileset_name}` | `{filename}` | {today} |"

    # Check if tileset_id already has an entry and update it
    pattern = re.compile(rf"^\|.*`{re.escape(tileset_id)}`.*\|$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(entry_line, content)
        registry_path.write_text(content)
        print(f"  Registry: updated existing entry for {tileset_id}")
    else:
        # Append before the last blank line or at end
        if not content.endswith("\n"):
            content += "\n"
        content += entry_line + "\n"
        registry_path.write_text(content)
        print(f"  Registry: added new entry for {tileset_id}")


def upload_one(uploader, filepath, tileset_id, token, prefix):
    """Upload a single .mbtiles file and poll for completion."""
    size_mb = os.path.getsize(filepath) / 1024 / 1024

    print(f"\n{'=' * 60}")
    print(f"Uploading: {os.path.basename(filepath)}")
    print(f"Tileset:   {tileset_id}")
    print(f"Size:      {size_mb:.1f} MB")

    try:
        with open(filepath, "rb") as src:
            upload_resp = uploader.upload(src, tileset_id)

        if upload_resp.status_code not in (200, 201, 202):
            error = upload_resp.text
            print(f"  ERROR: HTTP {upload_resp.status_code} {error}")
            return {"status": "FAILED", "error": error}

        upload_data = upload_resp.json()
        upload_id = upload_data.get("id", "unknown")
        print(f"  Upload created: {upload_id}")

        # Poll for completion (up to ~7.5 min)
        for attempt in range(90):
            time.sleep(5)
            status_resp = uploader.session.get(
                f"https://api.mapbox.com/uploads/v1/{prefix}/{upload_id}",
                params={"access_token": token},
            )
            if status_resp.status_code != 200:
                if attempt % 6 == 0:
                    print(f"  Poll {attempt}: HTTP {status_resp.status_code}")
                continue

            status = status_resp.json()
            progress = status.get("progress", 0)
            complete = status.get("complete", False)
            error = status.get("error")

            if error:
                print(f"  FAILED: {error}")
                return {"status": "FAILED", "error": error, "upload_id": upload_id}

            if complete:
                final_id = status.get("tileset", tileset_id)
                print(f"  DONE. Tileset: {final_id}")
                return {"status": "OK", "tileset_id": final_id, "upload_id": upload_id}

            if attempt % 3 == 0:
                print(f"  Progress: {progress * 100:.0f}%...")

        print("  TIMEOUT after ~7.5 minutes")
        return {"status": "TIMEOUT", "upload_id": upload_id}

    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return {"status": "FAILED", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Upload .mbtiles to Mapbox Studio")
    parser.add_argument("tiles_dir", help="Directory containing .mbtiles files")
    parser.add_argument(
        "--prefix",
        default="app-klever-mapbox",
        help="Mapbox account prefix for tileset IDs (default: app-klever-mapbox)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be uploaded without uploading",
    )
    args = parser.parse_args()

    tiles_dir = os.path.expanduser(args.tiles_dir)
    if not os.path.isdir(tiles_dir):
        print(f"ERROR: {tiles_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Discover .mbtiles files
    mbtiles = sorted(
        f for f in os.listdir(tiles_dir) if f.endswith(".mbtiles")
    )
    if not mbtiles:
        print(f"No .mbtiles files found in {tiles_dir}")
        sys.exit(0)

    # Build upload plan
    plan = []
    for filename in mbtiles:
        tileset_name = derive_tileset_name(filename)
        tileset_id = f"{args.prefix}.{tileset_name}"
        plan.append((tileset_name, tileset_id, filename))

    print(f"Found {len(plan)} tileset(s) to upload:\n")
    print(f"  {'Tileset ID':<45} {'Source File'}")
    print(f"  {'-' * 45} {'-' * 40}")
    for _, tid, fname in plan:
        print(f"  {tid:<45} {fname}")

    if args.dry_run:
        print("\n[DRY RUN] No uploads performed.")
        sys.exit(0)

    # Fetch token and initialize uploader
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

    # Upload each tileset
    results = {}
    for tileset_name, tileset_id, filename in plan:
        filepath = os.path.join(tiles_dir, filename)
        result = upload_one(uploader, filepath, tileset_id, token, args.prefix)
        results[tileset_name] = result

    # Summary
    print(f"\n{'=' * 60}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 60}")
    ok_count = 0
    for name, result in results.items():
        status = result.get("status", "UNKNOWN")
        tid = result.get("tileset_id", "n/a")
        symbol = "OK" if status == "OK" else "FAIL"
        print(f"  [{symbol:>4}] {name}: {tid}")
        if status == "OK":
            ok_count += 1

    print(f"\n{ok_count}/{len(results)} succeeded.")

    # Update tileset registry if found
    registry = find_tileset_registry(tiles_dir)
    if registry:
        print(f"\nUpdating tileset registry: {registry}")
        for tileset_name, tileset_id, filename in plan:
            result = results.get(tileset_name, {})
            update_registry(registry, tileset_id, tileset_name, filename, result.get("status"))

    # Write results JSON
    output_file = os.path.join(tiles_dir, "upload-results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_file}")

    # Exit with error if any failed
    if ok_count < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
