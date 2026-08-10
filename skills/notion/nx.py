#!/usr/bin/env python3
"""
nx — Notion checkout CLI.

Deterministic, stdlib-only. Does every mechanical operation on the local Notion
mirror so that agents never need the Notion MCP to READ knowledge, only to SYNC it.

Layout it owns:

    notion-checkout/
      pages/<page_id>/page.md        raw markdown body as fetched

    Root resolution: $NOTION_CHECKOUT, else ~/Developer/grp-beklever-com/notion-checkout.
    This file lives with the `notion` SKILL, not inside the cache it manages.
      pages/<page_id>/meta.json      per-page record (see PageMeta below)
      index/catalog.jsonl            one line per page, the rung-1 index
      index/INDEX.md                 human/agent readable section map
      index/tombstones.jsonl         pages that vanished or lost access
      LEDGER.yaml                    run-level freshness state
      runs/<run_id>/staging/         a sync in progress, promoted atomically

Progressive disclosure ladder:
    rung 1  nx search / nx ls      catalog lines      ~40 tokens per hit
    rung 2  nx card <id>           extractive card    ~200 tokens
    rung 3  nx get <id> --heading  bounded body slice  capped, never whole file

Commands:
    status                    ledger age + counts, no network
    search <query>            rank pages by title/breadcrumb/body match
    ls [--section S]          list catalog entries
    card <id|slug>            extractive card for one page
    get <id> [--heading H] [--max-bytes N]
    ingest <run_id>           normalize + hash + promote a staged sync
    plan-refresh [--volatile] [--older-than DAYS]
    apply-freshness <file>    fold live last_edited_time results into the ledger
    mark <id> --volatile|--stable
    doctor                    integrity check
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

DEFAULT_ROOT = Path.home() / "Developer/grp-beklever-com/notion-checkout"

# The mirror root. Override with NOTION_CHECKOUT to point at another checkout — which is
# what the eval suite does, and what makes this tool testable against a scripted world.
ROOT = Path(os.environ.get("NOTION_CHECKOUT") or DEFAULT_ROOT)
PAGES = ROOT / "pages"
INDEX = ROOT / "index"
RUNS = ROOT / "runs"
CATALOG = INDEX / "catalog.jsonl"
TOMBSTONES = INDEX / "tombstones.jsonl"
LEDGER = ROOT / "LEDGER.yaml"

FRESH_DAYS = 7
AGING_DAYS = 30

# ---------------------------------------------------------------- primitives


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def age_days(value: str | None) -> float | None:
    parsed = parse_iso(value)
    if parsed is None:
        return None
    delta = dt.datetime.now(dt.timezone.utc) - parsed
    return round(delta.total_seconds() / 86400, 2)


def normalize_id(raw: str) -> str:
    """Notion ids arrive dashed, undashed, or embedded in a URL. Store undashed."""
    found = re.findall(r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}", raw or "")
    if found:
        return found[0].replace("-", "").lower()
    tail = re.findall(r"([0-9a-fA-F]{32})", raw or "")
    if tail:
        return tail[0].lower()
    return (raw or "").strip().lower()


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def freshness_state(fetched_at: str | None) -> str:
    days = age_days(fetched_at)
    if days is None:
        return "unknown"
    if days <= FRESH_DAYS:
        return "fresh"
    if days <= AGING_DAYS:
        return "aging"
    return "stale"


# ---------------------------------------------------------------- catalog io


def read_catalog() -> list[dict]:
    if not CATALOG.exists():
        return []
    rows = []
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def write_catalog(rows: list[dict]) -> None:
    INDEX.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r.get("breadcrumb") or "", r.get("title") or ""))
    with CATALOG.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_ledger() -> dict:
    if not LEDGER.exists():
        return {}
    # Deliberately a tiny hand-rolled reader: flat key: value only, no PyYAML dep.
    data: dict = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(" "):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"')
        if value in ("null", ""):
            data[key.strip()] = None
        elif value.isdigit():
            data[key.strip()] = int(value)
        else:
            data[key.strip()] = value
    return data


def write_ledger(data: dict) -> None:
    lines = [
        "# Notion checkout ledger.",
        "# Written by tools/nx.py. Freshness state is DERIVED, never hand-edited.",
        "",
    ]
    for key in sorted(data):
        value = data[key]
        rendered = "null" if value is None else (str(value) if isinstance(value, int) else f'"{value}"')
        lines.append(f"{key}: {rendered}")
    LEDGER.write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_page(rows: list[dict], needle: str) -> dict | None:
    key = normalize_id(needle)
    for row in rows:
        if row.get("id") == key:
            return row
    lowered = (needle or "").strip().lower()
    for row in rows:
        if (row.get("title") or "").strip().lower() == lowered:
            return row
    matches = [r for r in rows if lowered and lowered in (r.get("title") or "").lower()]
    if len(matches) == 1:
        return matches[0]
    return None


# ---------------------------------------------------------------- extraction


def body_path(page_id: str) -> Path:
    return PAGES / page_id / "page.md"


def read_body(page_id: str) -> str:
    path = body_path(page_id)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def headings(body: str) -> list[str]:
    return [line.lstrip("#").strip() for line in body.splitlines() if line.startswith("#")]


def lead(body: str, limit: int = 2) -> list[str]:
    out = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        out.append(stripped)
        if len(out) >= limit:
            break
    return out


def build_card(row: dict, body: str) -> str:
    """Rung 2. Extractive only — no model call, so it is free and reproducible."""
    parts = [
        f"# {row.get('title') or '(untitled)'}",
        f"notion:{row.get('id')}  ·  {row.get('breadcrumb') or ''}",
        f"url: {row.get('url') or 'unknown'}",
        f"edited: {row.get('last_edited_time') or 'unknown'}  ·  fetched: {row.get('fetched_at') or 'never'}"
        f"  ·  freshness: {freshness_state(row.get('fetched_at'))}"
        + ("  ·  VOLATILE" if row.get("volatile") else ""),
        f"coverage: {row.get('coverage') or 'unknown'}  ·  access: {row.get('access_state') or 'unknown'}"
        f"  ·  {row.get('bytes') or 0} bytes",
        "",
    ]
    hs = headings(body)
    if hs:
        parts.append("sections: " + " | ".join(hs[:12]))
    for line in lead(body):
        parts.append("> " + line[:300])
    parts.append("")
    parts.append(f"full body: nx get {row.get('id')} --heading '<section>'")
    return "\n".join(parts)


# ---------------------------------------------------------------- commands


def cmd_status(args) -> int:
    rows = read_catalog()
    ledger = read_ledger()
    states = {"fresh": 0, "aging": 0, "stale": 0, "unknown": 0}
    volatile_stale = []
    for row in rows:
        state = freshness_state(row.get("fetched_at"))
        states[state] = states.get(state, 0) + 1
        if row.get("volatile") and state in ("stale", "unknown"):
            volatile_stale.append(row)

    tombstone_count = 0
    if TOMBSTONES.exists():
        tombstone_count = len([l for l in TOMBSTONES.read_text(encoding="utf-8").splitlines() if l.strip()])

    print(f"checkout root   : {ROOT}")
    print(f"pages in catalog: {len(rows)}")
    print(f"tombstones      : {tombstone_count}")
    print(f"last full sync  : {ledger.get('last_full_sync') or 'NEVER'}"
          + (f"  ({age_days(ledger.get('last_full_sync'))}d ago)" if ledger.get("last_full_sync") else ""))
    print(f"last delta sync : {ledger.get('last_delta_sync') or 'never'}")
    print(f"workspace watermark (max last_edited_time seen): {ledger.get('workspace_watermark') or 'unknown'}")
    print(f"freshness       : fresh={states['fresh']} aging={states['aging']} "
          f"stale={states['stale']} unknown={states['unknown']}")
    if volatile_stale:
        print("")
        print(f"!! {len(volatile_stale)} VOLATILE page(s) are stale. These auto-trigger a live check on lookup:")
        for row in volatile_stale[:10]:
            print(f"   - {row.get('title')}  (nx card {row.get('id')})")
    if not rows:
        print("")
        print("Catalog is empty. Run a sync: see SKILL 'notion' mode=sync, or tools/README.")
    return 0


def score(row: dict, body: str, terms: list[str]) -> int:
    title = (row.get("title") or "").lower()
    crumb = (row.get("breadcrumb") or "").lower()
    lowered = body.lower()
    total = 0
    for term in terms:
        if term in title:
            total += 40
        if term in crumb:
            total += 12
        total += min(lowered.count(term), 12) * 3
    return total


def cmd_search(args) -> int:
    rows = read_catalog()
    if not rows:
        print("catalog empty — nothing to search. Run a sync first.")
        return 1
    terms = [t.lower() for t in re.split(r"\s+", args.query.strip()) if t]
    scored = []
    for row in rows:
        body = read_body(row["id"])
        value = score(row, body, terms)
        if value > 0:
            scored.append((value, row, body))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        ledger = read_ledger()
        synced = ledger.get("last_delta_sync") or ledger.get("last_full_sync")
        days = age_days(synced)
        print(f"NO LOCAL MATCH for: {args.query}")
        print("")
        print("This means the page is NOT IN THIS MIRROR. It does NOT mean the page is absent")
        print("from Notion. Do not report it as 'no such page', 'not documented', or 'does not")
        print("exist' — that is a claim about Notion, and this command cannot support it.")
        print("")
        print(f"Mirror covers {len(rows)} page(s), last synced "
              f"{synced or 'NEVER'}" + (f" ({days}d ago)" if days is not None else ""))
        print("Correct next step: the notion skill, fetch mode, to pull the page from Notion.")
        return 1
    print(f"{len(scored)} hit(s) for '{args.query}' — showing {min(args.limit, len(scored))}\n")
    for value, row, body in scored[: args.limit]:
        state = freshness_state(row.get("fetched_at"))
        flag = " VOLATILE" if row.get("volatile") else ""
        print(f"[{value:>4}] {row.get('title')}")
        print(f"        notion:{row['id']}  {row.get('breadcrumb') or ''}")
        print(f"        freshness={state}{flag}  edited={row.get('last_edited_time') or '?'}")
    print(f"\nnext rung: nx card <id>")
    return 0


def cmd_ls(args) -> int:
    rows = read_catalog()
    if args.section:
        needle = args.section.lower()
        rows = [r for r in rows if needle in (r.get("breadcrumb") or "").lower()]
    for row in rows[: args.limit]:
        print(f"{row['id']}  {freshness_state(row.get('fetched_at')):>7}  "
              f"{(row.get('breadcrumb') or '')[:40]:<40}  {row.get('title')}")
    print(f"\n{len(rows)} page(s)")
    return 0


def cmd_card(args) -> int:
    rows = read_catalog()
    row = find_page(rows, args.id)
    if row is None:
        print(f"no page matched: {args.id}")
        return 1
    print(build_card(row, read_body(row["id"])))
    return 0


def cmd_get(args) -> int:
    rows = read_catalog()
    row = find_page(rows, args.id)
    if row is None:
        print(f"no page matched: {args.id}")
        return 1
    body = read_body(row["id"])
    if not body:
        print(f"page {row['id']} has no local body. coverage={row.get('coverage')}")
        return 1

    if args.heading:
        lines = body.splitlines()
        needle = args.heading.lower()
        start = None
        level = 0
        for i, line in enumerate(lines):
            if line.startswith("#") and needle in line.lower():
                start = i
                level = len(line) - len(line.lstrip("#"))
                break
        if start is None:
            print(f"heading not found: {args.heading}")
            print("available: " + " | ".join(headings(body)[:20]))
            return 1
        end = len(lines)
        for j in range(start + 1, len(lines)):
            candidate = lines[j]
            if candidate.startswith("#"):
                candidate_level = len(candidate) - len(candidate.lstrip("#"))
                if candidate_level <= level:
                    end = j
                    break
        body = "\n".join(lines[start:end])

    truncated = False
    encoded = body.encode("utf-8")
    if len(encoded) > args.max_bytes:
        body = encoded[: args.max_bytes].decode("utf-8", errors="ignore")
        truncated = True

    state = freshness_state(row.get("fetched_at"))
    print(f"--- notion:{row['id']} · {row.get('title')} · freshness={state} "
          f"· fetched={row.get('fetched_at')} ---")
    print(body)
    if truncated:
        print(f"\n[TRUNCATED at {args.max_bytes} bytes. Narrow with --heading, or raise --max-bytes.]")
    return 0


def cmd_ingest(args) -> int:
    """Promote a staged sync. Staging holds one JSON per page, written by the MCP subagent.

    Expected staged record:
      {"id","title","url","breadcrumb","last_edited_time","markdown",
       "coverage":"complete|partial","access_state":"accessible|restricted"}
    """
    staging = RUNS / args.run_id / "staging"
    if not staging.is_dir():
        print(f"no staging dir: {staging}")
        return 1

    staged = sorted(staging.glob("*.json"))
    if not staged:
        print(f"staging is empty: {staging}")
        return 1

    existing = {row["id"]: row for row in read_catalog()}
    seen: set[str] = set()
    problems: list[str] = []
    added = updated = unchanged = 0

    for path in staged:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{path.name}: bad json ({exc})")
            continue

        page_id = normalize_id(record.get("id", ""))
        if not page_id or len(page_id) != 32:
            problems.append(f"{path.name}: missing or malformed id")
            continue
        if page_id in seen:
            problems.append(f"{path.name}: duplicate id {page_id}")
            continue
        seen.add(page_id)

        markdown = record.get("markdown") or ""
        digest = sha256_text(markdown)
        prior = existing.get(page_id)

        page_dir = PAGES / page_id
        page_dir.mkdir(parents=True, exist_ok=True)
        body_path(page_id).write_text(markdown, encoding="utf-8")

        row = {
            "id": page_id,
            "title": (record.get("title") or "").strip() or "(untitled)",
            "url": record.get("url") or f"https://www.notion.so/{page_id}",
            "breadcrumb": record.get("breadcrumb") or "",
            "last_edited_time": record.get("last_edited_time"),
            "fetched_at": now_iso(),
            "sha256": digest,
            "bytes": len(markdown.encode("utf-8")),
            "coverage": record.get("coverage") or "complete",
            "access_state": record.get("access_state") or "accessible",
            "volatile": bool(prior.get("volatile")) if prior else bool(record.get("volatile")),
        }
        (page_dir / "meta.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        if prior is None:
            added += 1
        elif prior.get("sha256") != digest:
            updated += 1
        else:
            unchanged += 1
        existing[page_id] = row

    if problems and not args.force:
        print("REFUSING TO PROMOTE. Staging has problems:")
        for problem in problems[:20]:
            print(f"  - {problem}")
        print("\nFix the sync, or re-run with --force to promote the valid subset.")
        return 2

    rows = list(existing.values())
    write_catalog(rows)
    rebuild_index_md(rows)

    ledger = read_ledger()
    ledger["last_delta_sync"] = now_iso()
    if args.full:
        ledger["last_full_sync"] = now_iso()
    ledger["page_count"] = len(rows)
    watermark = max([r.get("last_edited_time") or "" for r in rows] + [""])
    if watermark:
        ledger["workspace_watermark"] = watermark
    write_ledger(ledger)

    print(f"promoted run {args.run_id}: +{added} new, ~{updated} changed, ={unchanged} unchanged")
    print(f"catalog now {len(rows)} page(s)")
    if problems:
        print(f"{len(problems)} record(s) skipped (--force was set)")
    return 0


def rebuild_index_md(rows: list[dict]) -> None:
    sections: dict[str, list[dict]] = {}
    for row in rows:
        top = (row.get("breadcrumb") or "(root)").split("/")[0].strip() or "(root)"
        sections.setdefault(top, []).append(row)

    lines = [
        "# Notion Checkout — Index",
        "",
        "Rung 1 of the disclosure ladder. Section map only. Do not read page bodies from here.",
        "",
        f"Generated {now_iso()} by `tools/nx.py`. {len(rows)} page(s).",
        "",
        "| Section | Pages | Stale |",
        "|---|---:|---:|",
    ]
    for name in sorted(sections):
        group = sections[name]
        stale = sum(1 for r in group if freshness_state(r.get("fetched_at")) == "stale")
        lines.append(f"| {name} | {len(group)} | {stale} |")
    lines += [
        "",
        "## How to use this",
        "",
        "```",
        "nx search \"<terms>\"     # rank pages, ~40 tokens per hit",
        "nx card <id>            # extractive card, ~200 tokens",
        "nx get <id> --heading H # bounded slice of one section",
        "```",
        "",
        "Never `cat` a file under `pages/`. Use `nx get` so the read is bounded and stamped.",
        "",
    ]
    (INDEX / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def cmd_plan_refresh(args) -> int:
    """Emit the page list a sync agent should re-check. Cheap: no network here."""
    rows = read_catalog()
    targets = []
    for row in rows:
        state = freshness_state(row.get("fetched_at"))
        days = age_days(row.get("fetched_at"))
        if args.volatile and not row.get("volatile"):
            continue
        if args.older_than is not None and (days is None or days < args.older_than):
            continue
        if not args.volatile and args.older_than is None and state == "fresh":
            continue
        targets.append({
            "id": row["id"],
            "title": row.get("title"),
            "url": row.get("url"),
            "known_last_edited_time": row.get("last_edited_time"),
            "known_sha256": row.get("sha256"),
            "fetched_at": row.get("fetched_at"),
            "volatile": bool(row.get("volatile")),
        })
    print(json.dumps({"generated_at": now_iso(), "count": len(targets), "targets": targets},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_apply_freshness(args) -> int:
    """Fold live last_edited_time probe results back in.

    Input: JSON list of {"id","last_edited_time","access_state"?}.
    Marks pages whose live edit time is newer than what we hold as content_stale.
    """
    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    probes = payload["results"] if isinstance(payload, dict) else payload
    rows = {row["id"]: row for row in read_catalog()}
    drifted, confirmed, lost = [], [], []

    for probe in probes:
        page_id = normalize_id(probe.get("id", ""))
        row = rows.get(page_id)
        if row is None:
            continue
        access = probe.get("access_state")
        if access and access != "accessible":
            row["access_state"] = access
            lost.append(row)
            continue
        live = probe.get("last_edited_time")
        row["freshness_checked_at"] = now_iso()
        known = row.get("last_edited_time")
        if live and known and live > known:
            row["content_stale"] = True
            row["live_last_edited_time"] = live
            drifted.append(row)
        else:
            row.pop("content_stale", None)
            row.pop("live_last_edited_time", None)
            confirmed.append(row)

    write_catalog(list(rows.values()))
    ledger = read_ledger()
    ledger["last_freshness_probe"] = now_iso()
    write_ledger(ledger)

    print(f"probed {len(probes)}: {len(confirmed)} still current, {len(drifted)} drifted, {len(lost)} access lost")
    for row in drifted:
        print(f"  DRIFTED  {row['title']}  (local {row.get('last_edited_time')} < live {row.get('live_last_edited_time')})")
    for row in lost:
        print(f"  ACCESS   {row['title']}  -> {row.get('access_state')}")
    return 0


def cmd_mark(args) -> int:
    rows = read_catalog()
    row = find_page(rows, args.id)
    if row is None:
        print(f"no page matched: {args.id}")
        return 1
    row["volatile"] = bool(args.volatile)
    write_catalog(rows)
    meta = PAGES / row["id"] / "meta.json"
    if meta.exists():
        meta.write_text(json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{row['title']} -> volatile={row['volatile']}")
    return 0


def cmd_doctor(args) -> int:
    rows = read_catalog()
    issues = []
    for row in rows:
        path = body_path(row["id"])
        if not path.exists():
            issues.append(f"{row['id']} in catalog but body missing")
            continue
        if row.get("sha256") and sha256_text(path.read_text(encoding="utf-8")) != row["sha256"]:
            issues.append(f"{row['id']} body hash mismatch — file edited outside nx")
        if row.get("coverage") == "partial":
            issues.append(f"{row['id']} coverage=partial — incomplete fetch, do not trust as whole")
        if row.get("access_state") not in (None, "accessible"):
            issues.append(f"{row['id']} access_state={row.get('access_state')}")

    catalog_ids = {row["id"] for row in rows}
    for page_dir in PAGES.iterdir() if PAGES.exists() else []:
        if page_dir.is_dir() and page_dir.name not in catalog_ids:
            issues.append(f"{page_dir.name} on disk but not in catalog (orphan)")

    if not issues:
        print(f"clean — {len(rows)} page(s), all hashes verified")
        return 0
    print(f"{len(issues)} issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


# ---------------------------------------------------------------- entrypoint


def main() -> int:
    parser = argparse.ArgumentParser(prog="nx", description="Notion checkout CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(func=cmd_status)

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("ls")
    p.add_argument("--section")
    p.add_argument("--limit", type=int, default=60)
    p.set_defaults(func=cmd_ls)

    p = sub.add_parser("card")
    p.add_argument("id")
    p.set_defaults(func=cmd_card)

    p = sub.add_parser("get")
    p.add_argument("id")
    p.add_argument("--heading")
    p.add_argument("--max-bytes", type=int, default=8000)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("ingest")
    p.add_argument("run_id")
    p.add_argument("--full", action="store_true", help="this run covered the whole workspace")
    p.add_argument("--force", action="store_true", help="promote valid records despite problems")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("plan-refresh")
    p.add_argument("--volatile", action="store_true")
    p.add_argument("--older-than", type=float)
    p.set_defaults(func=cmd_plan_refresh)

    p = sub.add_parser("apply-freshness")
    p.add_argument("file")
    p.set_defaults(func=cmd_apply_freshness)

    p = sub.add_parser("mark")
    p.add_argument("id")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--volatile", dest="volatile", action="store_true")
    group.add_argument("--stable", dest="volatile", action="store_false")
    p.set_defaults(func=cmd_mark)

    sub.add_parser("doctor").set_defaults(func=cmd_doctor)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
