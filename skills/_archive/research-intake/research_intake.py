#!/usr/bin/env python3
"""
research-intake: Automated harness research archival tool.
Fetches URLs, detects content type, files to raw/, optionally stubs analysis.

Usage:
  python3 research_intake.py archive <URL> [--note "why this landed"]
  python3 research_intake.py status
  python3 research_intake.py stub-analysis <raw-filename>
  python3 research_intake.py lint
"""

import sys
import os
import re
import json
import argparse
import subprocess
from datetime import date
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlparse

# ── Config ─────────────────────────────────────────────────────────────────

RESEARCH_ROOT = Path(
    "~/Developer/gabriel-amyot/projects/ai-software-development"
    "/dark-software-factory/research"
).expanduser()

RAW_DIR = RESEARCH_ROOT / "raw"
ANALYSIS_DIR = RESEARCH_ROOT / "analysis"
INDEX_PATH = RESEARCH_ROOT / "INDEX.md"

TODAY = date.today().isoformat()

# ── URL Detection ──────────────────────────────────────────────────────────

def detect_url_type(url: str) -> dict:
    """Returns type, raw_url, slug, author from a URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # GitHub repo
    if parsed.netloc in ("github.com", "www.github.com"):
        parts = path.split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            # Gist
            if owner == "gist.github.com" or parsed.netloc == "gist.github.com":
                gist_id = parts[0] if len(parts) == 1 else parts[1]
                return {
                    "type": "Gist",
                    "raw_url": f"https://gist.githubusercontent.com/{path}/raw/",
                    "slug": f"{repo}-gist" if len(parts) >= 2 else f"gist-{gist_id[:8]}",
                    "author": owner,
                }
            # Regular repo
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
            return {
                "type": "README",
                "raw_url": raw_url,
                "raw_url_fallback": f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
                "slug": f"{repo}-readme",
                "author": owner,
            }

    # Gist domain
    if parsed.netloc == "gist.github.com":
        parts = path.split("/")
        owner = parts[0] if parts else "unknown"
        gist_id = parts[1] if len(parts) > 1 else parts[0]
        return {
            "type": "Gist",
            "raw_url": f"https://gist.githubusercontent.com/{path}/raw/",
            "slug": f"{owner}-gist-{gist_id[:8]}",
            "author": owner,
        }

    # Generic article/blog
    slug = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")[-60:]
    return {
        "type": "Article",
        "raw_url": url,
        "slug": slug or "article",
        "author": parsed.netloc,
    }


def fetch_content(raw_url: str, fallback_url: str = None) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (research-intake/1.0)"}
    for attempt_url in filter(None, [raw_url, fallback_url]):
        try:
            req = Request(attempt_url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                if content.strip():
                    return content
        except URLError:
            continue
    raise RuntimeError(f"Could not fetch content from {raw_url}")


# ── File Writing ───────────────────────────────────────────────────────────

def build_raw_filename(slug: str) -> Path:
    """Ensure no collision."""
    base = RAW_DIR / f"{slug}.md"
    if not base.exists():
        return base
    i = 2
    while True:
        candidate = RAW_DIR / f"{slug}-{i}.md"
        if not candidate.exists():
            return candidate
        i += 1


def write_raw(url: str, url_info: dict, content: str, note: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    filepath = build_raw_filename(url_info["slug"])

    frontmatter = f"""---
source: {url}
author: {url_info['author']}
type: {url_info['type']}
archived: {TODAY}
note: {note or 'No note provided.'}
---

"""
    filepath.write_text(frontmatter + content, encoding="utf-8")
    return filepath


def update_index(filepath: Path, url: str, url_info: dict):
    """Append a row to the Raw Sources table in INDEX.md."""
    if not INDEX_PATH.exists():
        return

    index = INDEX_PATH.read_text(encoding="utf-8")
    rel = filepath.name
    new_row = f"| `raw/{rel}` | {url} | {url_info['type']} | {TODAY} |"

    # Insert before the blank line after the last raw row
    raw_table_end = index.find("\n---\n", index.find("## Raw Sources"))
    if raw_table_end == -1:
        index += f"\n{new_row}\n"
    else:
        index = index[:raw_table_end] + f"\n{new_row}" + index[raw_table_end:]

    INDEX_PATH.write_text(index, encoding="utf-8")


# ── Analysis Stub ──────────────────────────────────────────────────────────

def write_analysis_stub(raw_filename: str) -> Path:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    slug = raw_filename.replace("-readme.md", "").replace("-gist.md", "").replace(".md", "")
    out = ANALYSIS_DIR / f"{TODAY}-{slug}-analysis.md"

    stub = f"""---
date: {TODAY}
raw_source: raw/{raw_filename}
tools: {slug}
status: intake
operationalized:
---

# Analysis: {slug}

## What it is

<!-- One paragraph. No fluff. -->

## Relation to existing stack

<!-- Specific overlaps, complements, replacements. -->

## Cross-pollination opportunity

<!-- What concept is worth extracting without full adoption? -->

## Verdict

<!-- adopt | cross-pollinate | park -->
**Verdict:**

**Rationale:**
"""
    out.write_text(stub, encoding="utf-8")
    return out


# ── Status Dashboard ───────────────────────────────────────────────────────

def cmd_status():
    raw_files = sorted(RAW_DIR.glob("*.md")) if RAW_DIR.exists() else []
    analysis_files = sorted(ANALYSIS_DIR.glob("*.md")) if ANALYSIS_DIR.exists() else []

    # Map raw slugs to analysis files
    analyzed_slugs = set()
    for af in analysis_files:
        text = af.read_text(encoding="utf-8")
        m = re.search(r"^raw_source:\s*raw/(.+)$", text, re.MULTILINE)
        if m:
            analyzed_slugs.add(m.group(1))

    # Analysis verdict status
    verdict_counts = {"intake": [], "adopt": [], "cross-pollinate": [], "park": [], "operationalized": []}
    for af in analysis_files:
        text = af.read_text(encoding="utf-8")
        status_m = re.search(r"^status:\s*(.+)$", text, re.MULTILINE)
        op_m = re.search(r"^operationalized:\s*(.+)$", text, re.MULTILINE)
        status = status_m.group(1).strip() if status_m else "unknown"
        op = op_m.group(1).strip() if op_m else ""
        if op and op not in ("", "~", "null", "None"):
            verdict_counts["operationalized"].append(af.name)
        elif status in verdict_counts:
            verdict_counts[status].append(af.name)

    print(f"\n{'='*60}")
    print(f"  RESEARCH STATUS — {TODAY}")
    print(f"{'='*60}")
    print(f"\n  Raw sources:  {len(raw_files)}")
    print(f"  Analysis:     {len(analysis_files)}")
    print()

    unanalyzed = [f for f in raw_files if f.name not in analyzed_slugs]
    if unanalyzed:
        print(f"  ⚠  RAW WITHOUT ANALYSIS ({len(unanalyzed)}):")
        for f in unanalyzed:
            print(f"     - {f.name}")
    else:
        print("  ✓  All raw sources have analysis")

    print()
    for verdict, files in verdict_counts.items():
        if files:
            icon = {"intake": "🔍", "adopt": "✅", "cross-pollinate": "🔀", "park": "📦", "operationalized": "🚀"}.get(verdict, "•")
            print(f"  {icon} {verdict.upper()} ({len(files)}):")
            for f in files:
                print(f"     - {f}")
    print()


# ── Lint ───────────────────────────────────────────────────────────────────

def cmd_lint():
    issues = []

    for f in RAW_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---"):
            issues.append(f"[raw/{f.name}] Missing frontmatter")
        else:
            for field in ("source:", "author:", "archived:", "type:"):
                if field not in text[:400]:
                    issues.append(f"[raw/{f.name}] Missing frontmatter field: {field}")

    for f in ANALYSIS_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---"):
            issues.append(f"[analysis/{f.name}] Missing frontmatter")
        else:
            for field in ("date:", "status:", "tools:"):
                if field not in text[:400]:
                    issues.append(f"[analysis/{f.name}] Missing frontmatter field: {field}")
            status_m = re.search(r"^status:\s*(.+)$", text, re.MULTILINE)
            if status_m and "verdict" in status_m.group(1) and "operationalized:" not in text:
                issues.append(f"[analysis/{f.name}] Verdict set but no operationalized: field")

    if issues:
        print(f"\n  LINT — {len(issues)} issue(s):\n")
        for i in issues:
            print(f"  ⚠  {i}")
    else:
        print("\n  ✓ Research files pass lint\n")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="research-intake: harness research archival tool")
    sub = parser.add_subparsers(dest="cmd")

    arc = sub.add_parser("archive", help="Fetch and archive a URL to raw/")
    arc.add_argument("url")
    arc.add_argument("--note", default="", help="One-line context note")
    arc.add_argument("--stub-analysis", action="store_true", help="Also create analysis stub")

    sub.add_parser("status", help="Show research dashboard")
    sub.add_parser("lint", help="Lint frontmatter on all research files")

    stub = sub.add_parser("stub-analysis", help="Create analysis stub for a raw file")
    stub.add_argument("raw_filename", help="e.g. gstack-readme.md")

    args = parser.parse_args()

    if args.cmd == "archive":
        print(f"  Detecting URL type...")
        info = detect_url_type(args.url)
        print(f"  Type: {info['type']}  Author: {info['author']}")
        print(f"  Fetching from {info['raw_url']}...")
        content = fetch_content(info["raw_url"], info.get("raw_url_fallback"))
        print(f"  Fetched {len(content)} chars")
        filepath = write_raw(args.url, info, content, args.note)
        update_index(filepath, args.url, info)
        print(f"  ✓ Archived → {filepath.relative_to(RESEARCH_ROOT)}")
        if args.stub_analysis:
            stub_path = write_analysis_stub(filepath.name)
            print(f"  ✓ Analysis stub → {stub_path.relative_to(RESEARCH_ROOT)}")

    elif args.cmd == "status":
        cmd_status()

    elif args.cmd == "lint":
        cmd_lint()

    elif args.cmd == "stub-analysis":
        stub_path = write_analysis_stub(args.raw_filename)
        print(f"  ✓ Analysis stub → {stub_path.relative_to(RESEARCH_ROOT)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
