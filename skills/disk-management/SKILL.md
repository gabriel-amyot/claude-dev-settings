---
name: disk-management
description: Diagnose a full or nearly-full macOS disk and free space safely. Use when the user says the disk is full, low on space, "clean up disk space", "free up space", "out of space", or df shows very low available capacity.
---

# Disk Management

## Quick start

1. Run `scripts/scan.sh` — read-only, ranks Application Support, Caches, Downloads, dev-tool caches, Homebrew reclaimable bytes, and Trash by size. Its before-shot measures `/` and `/System/Volumes/Data` and prints a `CAPACITY_VERDICT` line for the fuller volume. On APFS, `/` is the sealed system volume and can show a low percentage while the Data volume is full. Trust the verdict line, never the `/` row alone.
2. Classify every big item into Tier A / B / C below.
3. Act on Tier A immediately. Batch Tier B and Tier C into one `AskUserQuestion` call (multi-question, not serial asks).
4. Run `scripts/scan.sh --df-only` for the after-shot and report the before/after delta of the `CAPACITY_VERDICT` volume.

## Tiers

**Tier A — safe, act without asking.** Fully regenerable caches:
- `npm cache clean --force`
- `pip cache purge`
- `~/Library/Caches/*` contents (see hard rule below — this is Caches, not Application Support)
- `brew cleanup --prune=all` (if brew installed). Plain `brew cleanup` leaves stale vendor copies in `/opt/homebrew`. The Homebrew cache size is a poor proxy for this. Use the dry-run line from `scan.sh`.
- `docker system prune` for dangling images only, never volumes, never `-a` without asking

**Tier B — large but reinstallable app data. Ask first, state the size and what regenerates.** Examples: game installs (Steam titles), downloaded game-world/asset bundles, CAD/creative-tool auto-updater caches (e.g. Autodesk `webdeploy`). Deleting these means a re-download on next use, not data loss — say that explicitly in the ask. Also look for regenerable data outside `Caches/` inside `Application Support/`: local VM bundles (for example Claude Desktop `vm_bundles`) and app `*-cache` folders. Keep a sibling `downloads/` folder in Tier C because it is user content.

**Tier C — user content. Never delete without explicit per-item confirmation.** Downloads folder contents, personal document archives, anything the user created or received. Before proposing deletion of anything in this tier:
- Peek at the folder's actual contents (`ls`, not just `du`).
- If the contents don't match the user's stated reason for why it's safe (e.g. they say "that's redundant data" but the folder is month-named personal records), **stop and flag the mismatch** instead of deleting. Don't delete on their word alone if what you see contradicts it.

## Hard rule: size the item, not its parent

Before any item goes into an `AskUserQuestion`, run `scripts/size_items.sh <path>...` (or `--children <dir>`) and put each item's own size in its option label. Never let a parent-folder total stand in for the items you offer. Example: a 22 GiB `steamapps/common` can split 21 GiB / 1 GiB between two titles.

## Hard rule: browsers

**Never delete or treat as disposable anything under `~/Library/Application Support/<Browser>/`** (Chrome, Firefox, Edge, Safari). Cookies and login state live there. Only `~/Library/Caches/<Browser>/` is safe cache — clearing it never touches cookies or sessions, but confirm this distinction to the user if they express concern, since the two paths look similar at a glance.

## Duplicate detection

`scan.sh` flags Downloads items whose names differ only by a trailing " 2", "(1)", etc. — a common sign of repeated downloads of the same file. Confirm with `du -sh` on each candidate before proposing to keep one and drop the rest; this is still Tier C (user content), so still needs confirmation.

## Reporting

Always show a before/after table of the `CAPACITY_VERDICT` volume (normally `/System/Volumes/Data`) and a short table of what was freed, grouped by tier, so the user can see exactly what happened without re-deriving it from tool output.
