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


def installed_skills():
    """Return the set of skill names that have a SKILL.md on disk."""
    names = set()
    root = Path.home() / ".claude" / "skills"
    for p in root.iterdir():
        if p.is_dir() and (p / "SKILL.md").exists():
            names.add(p.name)
    return names


def scan(days):
    cutoff = time.time() - days * 86400
    files = [p for p in PROJECTS.rglob("*.jsonl") if p.stat().st_mtime >= cutoff]
    if not files:
        return Counter(), Counter(), 0

    tool_pat = re.compile(rb'"skill"\s*:\s*"([a-zA-Z0-9:_-]+)"')
    slash_pat = re.compile(rb'<command-name>/?([a-zA-Z0-9:_-]+)</command-name>')
    tool_hits, slash_hits = Counter(), Counter()

    for f in files:
        try:
            data = f.read_bytes()
        except OSError:
            continue
        for m in tool_pat.finditer(data):
            tool_hits[m.group(1).decode()] += 1
        for m in slash_pat.finditer(data):
            slash_hits[m.group(1).decode()] += 1
    return tool_hits, slash_hits, len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--out", default=str(Path.home() / ".claude" / "skill-proposals" / "USAGE-SCAN.md"))
    args = ap.parse_args()

    installed = installed_skills()
    tool_hits, slash_hits, nfiles = scan(args.days)

    combined = Counter()
    for name in installed:
        combined[name] = tool_hits.get(name, 0) + slash_hits.get(name, 0)

    cron = cron_invoked_skills()
    # A skill younger than the scan window cannot have accumulated usage in it.
    # Judging a 14-day-old skill on 90 days of silence is a measurement error.
    root = Path.home() / ".claude" / "skills"
    young_cutoff = time.time() - 30 * 86400
    too_new = {n for n in installed
               if (root / n / "SKILL.md").exists()
               and (root / n / "SKILL.md").stat().st_mtime >= young_cutoff}
    excluded = cron | too_new
    never = sorted(n for n, c in combined.items() if c == 0 and n not in excluded)
    rare = sorted((c, n) for n, c in combined.items() if 0 < c <= 2)
    used = sorted(((c, n) for n, c in combined.items() if c > 2), reverse=True)

    lines = [
        "# Skill Usage Scan",
        "",
        f"Window: last {args.days} days. Transcripts scanned: {nfiles}.",
        f"Installed skills with a SKILL.md: {len(installed)}.",
        "",
        "Counts combine Skill-tool calls and slash-command invocations. A zero means",
        "the skill was never reached in the window by either path. Treat zero as a",
        "retirement CANDIDATE, not a verdict: a skill can be new, seasonal, or invoked",
        "only by another skill's internals.",
        "",
        f"Excluded as cron-invoked ({len(cron)}): {', '.join(sorted(cron)) or 'none'}.",
        "A launchd/cron job runs outside any session and writes no transcript, so",
        "counting those as unused is a false negative.",
        "",
        f"Excluded as too new ({len(too_new)}): {', '.join(sorted(too_new)) or 'none'}.",
        "Modified within 30 days, so the 90-day window cannot judge them.",
        "",
        f"## Never invoked ({len(never)}) — retirement candidates",
        "",
    ]
    lines += [f"- {n}" for n in never] or ["- (none)"]
    lines += ["", f"## Invoked 1-2 times ({len(rare)}) — low use", ""]
    lines += [f"- {n} ({c})" for c, n in rare] or ["- (none)"]
    lines += ["", f"## Actively used ({len(used)})", ""]
    lines += [f"- {n} ({c})" for c, n in used] or ["- (none)"]

    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"scanned {nfiles} transcripts")
    print(f"never invoked: {len(never)} | low use: {len(rare)} | active: {len(used)}")
    print(f"report: {args.out}")


if __name__ == "__main__":
    main()
