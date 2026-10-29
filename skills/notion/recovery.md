# Restore a Notion mirror on another machine

Check the root before any lookup: `python3 ~/.claude/skills/notion/nx.py status`.
Root resolution is `$NOTION_CHECKOUT` (including `~` expansion), otherwise
`~/Developer/grp-beklever-com/notion-checkout`. Set the same override for fetches.
Exit 2 means the checkout or catalog is missing; exit 1 on a populated catalog's
lookup means no local match. Neither proves that a live Notion page is absent.

## Verified provenance — 2026-10-29

The original mirror was committed locally at `4ef42ab` on 2026-08-12.
The deft-pike completion record explicitly says **local only, no remote**.
It contained 232 pages (205 complete, 27 partial); full sync remained NEVER.
This MacBook has the shared tools but no mirror at the default path. No accessible
GitHub repository or alternative checkout was located in the recorded search.
The original machine/backup location remains unknown. Do not invent a clone URL,
create a replacement directory to hide the failure, or use the frozen April export.
Shared tools live in `https://github.com/gabriel-amyot/claude-dev-settings.git`;
cloning that repository does not restore mirror data.

## Recover existing work

1. On the source machine run `nx status`; inspect `git status --short`,
   `git log -1 --oneline`, and `git remote -v` without printing credential-bearing URLs.
   Preserve uncommitted changes. Commit 4ef42ab is historical evidence, not an assumed tip.
2. If a verified private remote now exists, clone that URL into the resolved destination.
   Otherwise use an authenticated direct transfer or a private backup to restore the
   existing Git repository and working files. Include unpushed history and untracked
   page data. No public repository, new permissions, or uploads are implied.
3. Restore tracked `pages/`, `index/`, and `LEDGER.yaml` consistently from one snapshot.
   Keep hashes, coverage, tombstones and freshness records. Never hand-edit bodies.
   Do not label a restored historical snapshot current.
4. Configure `.mcp.json` locally with only `mcpServers.notion`, using the existing
   approved transport. Restore authentication through that transport on this machine.
   Do not copy OAuth token caches, credentials or session files into Git.
   An absent fetch configuration must not prevent reading an existing mirror.
5. Before creating a remote, audit tracked content and history for credentials and
   presigned attachment URLs. Keep `.mcp.json`, auth caches, environment files and
   transient `runs/` artifacts machine-local and ignored. Ignore rules alone do not
   remove already tracked secrets. Never auto-delete configuration files.

## Validate before declaring recovery complete

Use bounded commands only:

```bash
python3 ~/.claude/skills/notion/nx.py status
python3 ~/.claude/skills/notion/nx.py doctor
python3 ~/.claude/skills/notion/nx.py search "Store Locations" --limit 5
python3 ~/.claude/skills/notion/nx.py card 357c75c6160680809628e73dbd9bfbaa
python3 ~/.claude/skills/notion/nx.py get 357c75c6160680809628e73dbd9bfbaa --heading "Part 1" --max-bytes 4000
```

An honest doctor report can include partial pages. Resolve hash mismatches before
trusting the cache. Probe the SOP's live edit timestamp through the isolated Notion
executor, apply the probe with `nx apply-freshness`, then fetch drifted/missing content.
Do not guess timestamps. For a one-page fetch use the existing preflighted executor:

```bash
CO="${NOTION_CHECKOUT:-$HOME/Developer/grp-beklever-com/notion-checkout}"
bash ~/.claude/skills/notion/fetch-shard.sh "$CO" recovery-sop sop 357c75c6160680809628e73dbd9bfbaa
NOTION_CHECKOUT="$CO" python3 ~/.claude/skills/notion/nx.py ingest recovery-sop
```

Stop on executor/config/auth failures. Never register Notion globally. Never mark
this one-page run full. The script verifies scope, not live authentication success.
After successful recovery, record the actual source, verified private remote if any,
restore command, last successful fetch, counts/coverage and cross-machine push/pull
procedure here. Until then, cross-machine durability is **unresolved**.
