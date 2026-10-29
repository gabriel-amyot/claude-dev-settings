#!/usr/bin/env bash
# Fetch one shard of Notion pages into a run's staging dir via an isolated headless session.
# Bodies never enter the calling context: each shard writes to disk and reports counts only.
#
# Usage: fetch-shard.sh <checkout_root> <run_id> <label> <page_id> [page_id ...]
#
# Runs on Sonnet: the work is mechanical (fetch, write, count), so a cheaper model is correct.
# Keep shards small. Page bodies accumulate in a session's context, so cost per page rises
# with pages per shard.
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: fetch-shard.sh <checkout_root> <run_id> <label> <page_id> [page_id ...]" >&2
  exit 2
fi
MODEL="${NX_FETCH_MODEL:-sonnet}"
CO="$1"; RUN="$2"; LABEL="$3"; shift 3
IDS="$*"
# Fail before mkdir: a typo must never create a phantom checkout.
if [ ! -d "$CO" ]; then
  echo "checkout missing: $CO; restore it or use the actual mirror root" >&2
  exit 2
fi
CO="$(cd "$CO" && pwd -P)"
if [ ! -f "$CO/.mcp.json" ]; then
  echo "isolated fetch config missing: $CO/.mcp.json; see notion recovery.md" >&2
  exit 2
fi
python3 - "$CO/.mcp.json" <<'PYCONFIG'
import json, sys
try:
    config = json.load(open(sys.argv[1]))
    if set(config.get("mcpServers", {})) != {"notion"}:
        raise ValueError("expected only the notion server")
except (OSError, ValueError, TypeError, AttributeError):
    print("Invalid isolated MCP config: require only mcpServers.notion; values withheld", file=sys.stderr)
    sys.exit(2)
PYCONFIG
if ! command -v claude >/dev/null 2>&1; then
  echo "fetch executor unavailable: claude; local nx reads remain usable" >&2
  exit 2
fi
if [[ ! "$RUN" =~ ^[A-Za-z0-9_-]+$ || ! "$LABEL" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "run_id and label must contain only letters, digits, underscores or hyphens" >&2
  exit 2
fi
STAGING="$CO/runs/$RUN/staging"
SHARDS="$CO/runs/$RUN/shards"
mkdir -p "$STAGING" "$SHARDS"

cd "$CO"
claude -p "Use ONLY the notion MCP plus Write and Bash.

Fetch these Notion pages, including child blocks:
$IDS

For EACH page write exactly one file to $STAGING/<page_id>.json with these keys and nothing else:
  id, title, url, breadcrumb, last_edited_time, coverage, access_state, markdown

HOW TO WRITE: use Bash with a python3 heredoc (json.dump). Do NOT use the Write tool.
A repo hook blocks the Write tool in this directory, and a blocked write loses the page.

Rules:
- breadcrumb is the parent path from the fetch result, e.g. 'Dev Team/Projects/Klever Media API'. Empty string if you truly cannot derive it. Never invent one.
- coverage is 'complete' only if you fetched the whole body and every child block. Use 'partial' for an unfinished cursor, a sampled database, or an unresolved synced/alias block.
- access_state is 'accessible', or 'restricted' if the fetch was refused. Those two values are
  the enum nx.py documents; anything else reads as unknown and doctor cannot classify it.
- markdown is the full raw body. Do not summarize, trim or reformat.
- Replace any pre-signed URL query string carrying X-Amz-Security-Token or X-Amz-Signature with notion-attachment://<block-id>/<filename> and mark that page partial.
- If a page body contains a real credential, token, password or private key, DO NOT write its file. List that id in the reply.
- Never print a page body to stdout.

REPLY with ONLY:
FILES=<count>
COMPLETE=<count>
PARTIAL=<count>
BREADCRUMBS=<count non-empty>
NOACCESS=<count>
SECRETS=<ids withheld, or none>" \
  --model "$MODEL" \
  --mcp-config .mcp.json --strict-mcp-config \
  --allowedTools "mcp__notion,Write,Bash" --permission-mode acceptEdits \
  --output-format json > "$SHARDS/$LABEL.json" 2>"$SHARDS/$LABEL.err"
