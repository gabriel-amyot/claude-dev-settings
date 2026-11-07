#!/usr/bin/env python3
"""Count skill invocations across Claude Code transcripts.

Finds installed skills that were never invoked in the scan window, so an audit
can propose retirement candidates instead of guessing.

Counts two signals:
  1. Skill-tool calls        -> "skill":"<name>"
  2. Slash-command invokes   -> <command-name>/<name> or /<name> in user text

Usage:  python3 skill_usage_scan.py [--days 90] [--out report.md]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
SKILL_DIRS = [
    Path.home() / ".claude" / "skills",
    Path.home() / ".claude" / "plugins" / "local-marketplace",
]


def cron_invoked_skills():
    """Skills invoked by launchd/cron rather than from a session.

    These are INVISIBLE to a transcript scan by construction — the job runs
    outside any Claude Code session, so it writes no transcript. Counting them
    as 'never invoked' is a false negative. skill-evals is the known case: a
    monthly sweep fires it from com.harness.skill-evals-monthly.
    """
    names = set()
    sources = [Path.home() / "Library" / "LaunchAgents"]
    for root in sources:
        if not root.exists():
            continue
        for plist in root.glob("*.plist"):
            try:
                text = plist.read_text(errors="ignore")
            except OSError:
                continue
            for m in re.finditer(r"/([a-zA-Z0-9:_-]+)\b", text):
                pass
            for skill in installed_skills():
                if re.search(rf"[/\"'\s]{re.escape(skill)}\b", text):
                    names.add(skill)
    try:
        crontab = subprocess.run(["crontab", "-l"], capture_output=True,
                                 text=True, timeout=10).stdout
        for skill in installed_skills():
            if re.search(rf"[/\"'\s]{re.escape(skill)}\b", crontab):
                names.add(skill)
    except Exception:
        pass
    return names


def installed_skill_paths():
    """Inventory personal and registered plugin skills, deduplicated by source."""
    roots = [(Path.home() / ".claude" / "skills", None)]
    registry = Path.home() / ".claude/plugins/installed_plugins.json"
    try:
        for plugin, entries in json.loads(registry.read_text()).get("plugins", {}).items():
            for entry in entries if isinstance(entries, list) else [entries]:
                if entry.get("installPath"):
                    roots.append((Path(entry["installPath"]) / "skills", plugin.split("@")[0]))
    except (OSError, ValueError, TypeError):
        pass
    paths, seen = {}, set()
    for root, plugin in roots:
        if not root.is_dir():
            continue
        for folder in sorted(root.iterdir()):
            path = folder / "SKILL.md"
            if folder.name.startswith("_") or folder.name in {"synced", "templates"} or not path.is_file():
                continue
            canonical = path.resolve()
            if canonical in seen:
                continue
            seen.add(canonical)
            name = folder.name if plugin is None else plugin + ":" + folder.name
            paths[name] = canonical
    return paths


def installed_skills():
    return set(installed_skill_paths())


def _aliases():
    aliases = {}
    for display, path in installed_skill_paths().items():
        aliases[display] = display
        try:
            match = re.search(r"^name:\s*([^\n]+)", path.read_text(), re.M)
            if match:
                declared = match.group(1).strip().strip("\"'")
                if ":" in display:
                    aliases[display.split(":", 1)[0] + ":" + declared] = display
                else:
                    aliases[declared] = display
        except OSError:
            continue
    return aliases


def _event_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc).timestamp() if parsed.tzinfo is None else parsed.timestamp()
    except ValueError:
        return None


def _belongs_to_org(event, org):
    cwd = event.get("cwd") or event.get("projectPath") or ""
    marker = {"klever": "grp-beklever-com", "supervisrai": "supervisr-ai", "personal": "gabriel-amyot"}[org]
    return marker in str(cwd)


def scan(days, org="klever"):
    """Read actual message structures and per-event dates, never raw payload regexes."""
    cutoff = time.time() - days * 86400
    aliases = _aliases()
    tool_hits, slash_hits, scanned = Counter(), Counter(), 0
    marker = {"klever": "grp-beklever-com", "supervisrai": "supervisr-ai", "personal": "gabriel-amyot"}[org]
    for path in PROJECTS.rglob("*.jsonl"):
        # Directory scoping prevents unrelated org content from being opened.
        if marker not in str(path.parent):
            continue
        scanned += 1
        try:
            with path.open(errors="replace") as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    when = _event_timestamp(event.get("timestamp"))
                    if when is None or when < cutoff or when > time.time():
                        continue
                    if event.get("cwd") and not _belongs_to_org(event, org):
                        continue
                    message = event.get("message") or {}
                    if not isinstance(message, dict):
                        continue
                    content = message.get("content")
                    if event.get("type") == "assistant" and isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict) or block.get("type") != "tool_use" or block.get("name") != "Skill":
                                continue
                            supplied = block.get("input") or {}
                            invoked = supplied.get("skill") if isinstance(supplied, dict) else None
                            if invoked in aliases:
                                tool_hits[aliases[invoked]] += 1
                    elif event.get("type") == "user" and isinstance(content, str):
                        # Only a command at the start of a real user message counts.
                        match = re.match(r"\s*<command-name>/?([a-zA-Z0-9:_-]+)</command-name>", content)
                        if match is None:
                            match = re.match(r"\s*/([a-zA-Z0-9:_-]+)(?:\s|$)", content)
                        if match and match.group(1) in aliases:
                            slash_hits[aliases[match.group(1)]] += 1
        except OSError:
            continue
    return tool_hits, slash_hits, scanned


def publish_harness(kind, source_path, records=None):
    """Bridge metadata without changing the producer's result."""
    try:
        import importlib.util
        import os
        import sys
        from pathlib import Path
        shared = Path(os.environ.get("HARNESS_ROOT", str(Path.home() / ".claude-shared-config")))
        spec = importlib.util.spec_from_file_location("harness_producer", shared / "harness/producer.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.publish(kind, source_path, records)
    except Exception as error:
        import sys
        print(f"WARN harness bridge unavailable: {error}", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--org", choices=["klever", "supervisrai", "personal"], default="klever")
    ap.add_argument("--out", default=str(Path.home() / ".claude" / "skill-proposals" / "USAGE-SCAN.md"))
    args = ap.parse_args()

    installed = installed_skills()
    tool_hits, slash_hits, nfiles = scan(args.days, args.org)

    combined = Counter()
    for name in installed:
        combined[name] = tool_hits.get(name, 0) + slash_hits.get(name, 0)

    cron = cron_invoked_skills()
    # Modification time is not creation time. Keep age unknown rather than hide
    # maintained skills from the report as "too new".
    too_new = set()
    excluded = cron | too_new
    never = sorted(n for n, c in combined.items() if c == 0 and n not in excluded)
    rare = sorted((c, n) for n, c in combined.items() if 0 < c <= 2)
    used = sorted(((c, n) for n, c in combined.items() if c > 2), reverse=True)

    lines = [
        "# Skill Usage Scan",
        "",
        f"Window: last {args.days} days. Org: {args.org}. Transcripts scanned: {nfiles}.",
        f"Installed skills with a SKILL.md: {len(installed)}.",
        "",
        "Counts are observed invocation signals from structured Claude messages.",
        "A slash request and a Skill call can describe one action; these are not unique completed runs.",
        "Zero means no observed signal in available Claude transcripts, not proof of non-use.",
        "Codex activity, unsaved sessions and internal/manual workflows are outside this report.",
        "",
        f"Excluded as cron-invoked ({len(cron)}): {', '.join(sorted(cron)) or 'none'}.",
        "A launchd/cron job runs outside any session and writes no transcript, so",
        "counting those as unused is a false negative.",
        "",
        f"Excluded as too new ({len(too_new)}): {', '.join(sorted(too_new)) or 'none'}.",
        "Age exclusions are unknown: file modification time is not a reliable creation date.",
        "",
        f"## Never invoked ({len(never)}) — no observed signal, review candidates",
        "",
    ]
    lines += [f"- {n}" for n in never] or ["- (none)"]
    lines += ["", f"## Invoked 1-2 times ({len(rare)}) — low use", ""]
    lines += [f"- {n} ({c})" for c, n in rare] or ["- (none)"]
    lines += ["", f"## Actively used ({len(used)})", ""]
    lines += [f"- {n} ({c})" for c, n in used] or ["- (none)"]

    Path(args.out).write_text("\n".join(lines) + "\n")
    publish_harness("usage-scan", args.out, [{"org": args.org, "days": args.days}])
    print(f"scanned {nfiles} transcripts")
    print(f"never invoked: {len(never)} | low use: {len(rare)} | active: {len(used)}")
    print(f"report: {args.out}")


if __name__ == "__main__":
    main()
