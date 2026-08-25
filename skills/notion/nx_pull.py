#!/usr/bin/env python3
"""Deterministic Notion pull. No model in the loop.

Talks to the Notion REST API directly, so pagination is exhaustive and coverage is
provable rather than guessed. Writes the same staging record shape that `nx ingest`
expects, so it is a drop-in replacement for the headless-session fetch path.

Auth: a Notion internal integration token in $NOTION_TOKEN, or in a file passed with
--token-file. The integration only sees pages explicitly shared with it.

    export NOTION_TOKEN=ntn_xxx
    python3 nx_pull.py discover --out runs/<run>/api-manifest.jsonl
    python3 nx_pull.py pull --manifest runs/<run>/api-manifest.jsonl --staging runs/<run>/staging
    python3 nx_pull.py pull --ids a,b,c --staging runs/<run>/staging

Both commands are resumable: `pull` skips ids already present in --staging.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

# Notion's published limit is ~3 requests/second averaged. Stay under it.
MIN_INTERVAL = 0.34
_rate_lock = threading.Lock()
_last_call = [0.0]

# Query strings on Notion S3 links carry temporary AWS session credentials.
# They must never land on disk. The stable block reference replaces them.
PRESIGNED = re.compile(r"https://[^\s)\"']*?(?:X-Amz-Security-Token|X-Amz-Signature)[^\s)\"']*")
SECRET_PATTERNS = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}"),
    re.compile(r"\bghp_[0-9A-Za-z]{30,}"),
    re.compile(r"\bglpat-[0-9A-Za-z_-]{20,}"),
    re.compile(r"\bntn_[0-9A-Za-z]{40,}"),
    re.compile(r"\bsecret_[0-9A-Za-z]{40,}"),
]


class Fatal(Exception):
    pass


def token(args) -> str:
    if args.token_file:
        return open(os.path.expanduser(args.token_file)).read().strip()
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    if not tok:
        raise Fatal("No token. Set $NOTION_TOKEN or pass --token-file.")
    return tok


def call(tok: str, method: str, path: str, body: dict | None = None, tries: int = 6) -> dict:
    """One API call, rate limited, with backoff on 429 and 5xx."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Notion-Version", VERSION)
    req.add_header("Content-Type", "application/json")

    for attempt in range(tries):
        with _rate_lock:
            gap = time.monotonic() - _last_call[0]
            if gap < MIN_INTERVAL:
                time.sleep(MIN_INTERVAL - gap)
            _last_call[0] = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and attempt < tries - 1:
                wait = float(e.headers.get("Retry-After") or (2 ** attempt))
                time.sleep(min(wait, 30))
                continue
            detail = e.read().decode(errors="replace")[:300]
            raise Fatal(f"{method} {path} -> HTTP {e.code}: {detail}")
        except urllib.error.URLError as e:
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            raise Fatal(f"{method} {path} -> {e}")
    raise Fatal(f"{method} {path} exhausted retries")


def paginate(tok: str, method: str, path: str, body: dict | None = None) -> Iterable[dict]:
    """Walk every page of a paginated endpoint. This is the whole point of the script."""
    cursor = None
    while True:
        payload = dict(body or {})
        if method == "GET":
            sep = "&" if "?" in path else "?"
            url = f"{path}{sep}page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            res = call(tok, "GET", url)
        else:
            payload["page_size"] = 100
            if cursor:
                payload["start_cursor"] = cursor
            res = call(tok, method, path, payload)
        yield from res.get("results", [])
        if not res.get("has_more"):
            return
        cursor = res.get("next_cursor")
        if not cursor:
            return


def rich(items: list[dict] | None) -> str:
    out = []
    for t in items or []:
        txt = t.get("plain_text", "")
        ann = t.get("annotations") or {}
        if ann.get("code"):
            txt = f"`{txt}`"
        if ann.get("bold"):
            txt = f"**{txt}**"
        if ann.get("italic"):
            txt = f"*{txt}*"
        if ann.get("strikethrough"):
            txt = f"~~{txt}~~"
        href = t.get("href")
        if href:
            txt = f"[{txt}]({href})"
        out.append(txt)
    return "".join(out)


def title_of(obj: dict) -> str:
    props = obj.get("properties") or {}
    for v in props.values():
        if v.get("type") == "title":
            return rich(v.get("title")) or "(untitled)"
    if obj.get("object") == "database":
        return rich(obj.get("title")) or "(untitled database)"
    return "(untitled)"


class Puller:
    def __init__(self, tok: str, staging: str, expand_databases: bool):
        self.tok = tok
        self.staging = staging
        self.expand_databases = expand_databases
        self.bc_cache: dict[str, str] = {}
        self.bc_lock = threading.Lock()

    # -- breadcrumbs -------------------------------------------------------
    def breadcrumb(self, obj: dict, depth: int = 0) -> str:
        """Exact parent chain. The MCP path could not do this reliably."""
        if depth > 12:
            return ""
        parent = obj.get("parent") or {}
        ptype = parent.get("type")
        if ptype == "workspace":
            return ""
        pid = parent.get(ptype) if ptype else None
        if not isinstance(pid, str):
            return ""
        with self.bc_lock:
            if pid in self.bc_cache:
                return self.bc_cache[pid]
        try:
            if ptype == "database_id":
                p = call(self.tok, "GET", f"/databases/{pid}")
            elif ptype in ("page_id", "block_id"):
                p = call(self.tok, "GET", f"/{'pages' if ptype == 'page_id' else 'blocks'}/{pid}")
                if p.get("object") == "block":
                    return self.breadcrumb(p, depth + 1)
            else:
                return ""
        except Fatal:
            return ""
        up = self.breadcrumb(p, depth + 1)
        name = title_of(p)
        chain = f"{up}/{name}" if up else name
        with self.bc_lock:
            self.bc_cache[pid] = chain
        return chain

    # -- block rendering ---------------------------------------------------
    def blocks_md(self, block_id: str, depth: int, state: dict) -> str:
        if depth > 8:
            state["partial"] = True
            state["reasons"].add("depth-limit")
            return ""
        lines: list[str] = []
        try:
            children = list(paginate(self.tok, "GET", f"/blocks/{block_id}/children"))
        except Fatal as e:
            state["partial"] = True
            state["reasons"].add(f"children-failed:{str(e)[:40]}")
            return ""
        numbered = 0
        for b in children:
            t = b.get("type")
            d = b.get(t) or {}
            text = rich(d.get("rich_text"))
            pad = "  " * depth
            if t == "paragraph":
                lines.append(f"{pad}{text}")
            elif t in ("heading_1", "heading_2", "heading_3"):
                lines.append(f"{pad}{'#' * int(t[-1])} {text}")
            elif t == "bulleted_list_item":
                lines.append(f"{pad}- {text}")
            elif t == "numbered_list_item":
                numbered += 1
                lines.append(f"{pad}{numbered}. {text}")
            elif t == "to_do":
                lines.append(f"{pad}- [{'x' if d.get('checked') else ' '}] {text}")
            elif t == "toggle":
                lines.append(f"{pad}- {text}")
            elif t == "code":
                lines.append(f"{pad}```{d.get('language') or ''}\n{text}\n{pad}```")
            elif t == "quote":
                lines.append(f"{pad}> {text}")
            elif t == "callout":
                lines.append(f"{pad}> {text}")
            elif t == "divider":
                lines.append(f"{pad}---")
            elif t == "child_page":
                lines.append(f"{pad}- [child page] {d.get('title', '')} (notion:{b['id'].replace('-', '')})")
            elif t == "child_database":
                lines.append(f"{pad}- [database] {d.get('title', '')} (notion:{b['id'].replace('-', '')})")
                if not self.expand_databases:
                    state["partial"] = True
                    state["reasons"].add("unexpanded-database")
            elif t in ("image", "file", "pdf", "video"):
                f = d.get("file") or d.get("external") or {}
                url = f.get("url", "")
                name = d.get("name") or (url.split("/")[-1].split("?")[0] if url else "attachment")
                lines.append(f"{pad}- [{t}] notion-attachment://{b['id']}/{name}")
            elif t == "bookmark" or t == "embed" or t == "link_preview":
                lines.append(f"{pad}- [{t}] {d.get('url', '')}")
            elif t == "table":
                pass  # rows come through as children below
            elif t == "table_row":
                cells = [rich(c) for c in d.get("cells") or []]
                lines.append(f"{pad}| " + " | ".join(cells) + " |")
            elif t == "synced_block":
                src = (d.get("synced_from") or {}).get("block_id")
                if src:
                    # A mirror of another block. Follow it once, at the source.
                    lines.append(self.blocks_md(src, depth, state))
            elif t == "unsupported":
                state["partial"] = True
                state["reasons"].add("unsupported-block")
            else:
                if text:
                    lines.append(f"{pad}{text}")

            if b.get("has_children") and t not in ("synced_block", "child_page", "child_database"):
                lines.append(self.blocks_md(b["id"], depth + 1, state))

        return "\n".join(x for x in lines if x is not None)

    # -- one page ----------------------------------------------------------
    def pull_page(self, page_id: str) -> dict:
        dashed = page_id if "-" in page_id else "-".join(
            [page_id[:8], page_id[8:12], page_id[12:16], page_id[16:20], page_id[20:]]
        )
        out_path = os.path.join(self.staging, f"{dashed}.json")
        if os.path.exists(out_path):
            return {"id": dashed, "status": "skipped"}

        state = {"partial": False, "reasons": set()}
        try:
            meta = call(self.tok, "GET", f"/pages/{dashed}")
        except Fatal as e:
            msg = str(e)
            if "HTTP 404" in msg or "HTTP 403" in msg:
                return {"id": dashed, "status": "no_access", "detail": msg[:120]}
            return {"id": dashed, "status": "error", "detail": msg[:160]}

        body = self.blocks_md(dashed, 0, state)
        body = PRESIGNED.sub(lambda m: "notion-attachment://redacted-presigned-url", body)
        if PRESIGNED.search(body):
            state["partial"] = True

        for pat in SECRET_PATTERNS:
            if pat.search(body):
                return {"id": dashed, "status": "secret", "detail": pat.pattern[:40]}

        rec = {
            "id": dashed,
            "title": title_of(meta),
            "url": meta.get("url", ""),
            "breadcrumb": self.breadcrumb(meta),
            "last_edited_time": meta.get("last_edited_time", ""),
            "coverage": "partial" if state["partial"] else "complete",
            "access_state": "accessible",
            "markdown": body,
        }
        tmp = out_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(rec, f, ensure_ascii=False)
        os.replace(tmp, out_path)
        return {
            "id": dashed,
            "status": "ok",
            "coverage": rec["coverage"],
            "bytes": len(body),
            "reasons": sorted(state["reasons"]),
        }


def cmd_discover(args) -> int:
    tok = token(args)
    seen: dict[str, dict] = {}
    for obj in paginate(tok, "POST", "/search", {}):
        oid = obj.get("id")
        if not oid:
            continue
        seen[oid] = {
            "id": oid,
            "object": obj.get("object"),
            "title": title_of(obj),
            "url": obj.get("url", ""),
            "last_edited_time": obj.get("last_edited_time", ""),
            "archived": bool(obj.get("archived")),
        }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        for r in seen.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    pages = sum(1 for r in seen.values() if r["object"] == "page")
    dbs = sum(1 for r in seen.values() if r["object"] == "database")
    arch = sum(1 for r in seen.values() if r["archived"])
    print(f"discovered {len(seen)} objects: {pages} pages, {dbs} databases, {arch} archived")
    print(f"wrote {args.out}")
    print("pagination exhausted -> this listing is complete for what the integration can see")
    return 0


def cmd_pull(args) -> int:
    tok = token(args)
    os.makedirs(args.staging, exist_ok=True)

    ids: list[str] = []
    if args.ids:
        ids = [x.strip() for x in args.ids.split(",") if x.strip()]
    elif args.manifest:
        for line in open(args.manifest):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("object") == "database" and not args.expand_databases:
                continue
            if r.get("archived") and not args.include_archived:
                continue
            if r.get("id"):
                ids.append(r["id"])
    else:
        raise Fatal("Give --ids or --manifest.")

    puller = Puller(tok, args.staging, args.expand_databases)
    tally: dict[str, int] = {}
    problems: list[dict] = []
    done = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for res in pool.map(puller.pull_page, ids):
            done += 1
            tally[res["status"]] = tally.get(res["status"], 0) + 1
            if res["status"] in ("no_access", "error", "secret"):
                problems.append(res)
            if res.get("coverage") == "partial":
                tally["partial"] = tally.get("partial", 0) + 1
            if done % 25 == 0 or done == len(ids):
                print(f"  {done}/{len(ids)}  {tally}", flush=True)

    print()
    print("pull complete:", tally)
    if problems:
        print(f"{len(problems)} problem page(s):")
        for p in problems[:20]:
            print(f"  {p['id']}  {p['status']}  {p.get('detail', '')}")
        if any(p["status"] == "secret" for p in problems):
            print("NOTE: pages flagged 'secret' were NOT written. Review them by hand.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic Notion pull (no model in the loop)")
    ap.add_argument("--token-file")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover", help="exhaustively list everything the integration can see")
    d.add_argument("--out", required=True)
    d.set_defaults(fn=cmd_discover)

    p = sub.add_parser("pull", help="fetch page bodies into a staging dir")
    p.add_argument("--manifest")
    p.add_argument("--ids")
    p.add_argument("--staging", required=True)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--expand-databases", action="store_true")
    p.add_argument("--include-archived", action="store_true")
    p.set_defaults(fn=cmd_pull)

    args = ap.parse_args()
    try:
        return args.fn(args)
    except Fatal as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\ninterrupted. staged files persist, rerun to resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
