#!/usr/bin/env python3
"""Classify never-invoked skills by whether anything else references them.

A skill with zero invocations is not necessarily dead. It may be a sub-step
another skill, agent, hook, or CLAUDE.md rule depends on. This separates:

  ORPHAN     - zero invocations, nothing references it        -> retire
  REFERENCED - zero invocations, but other config points at it -> investigate
               (either the caller is also dead, or the rule is not being followed)

Usage: python3 skill_refs_scan.py --names-from USAGE-SCAN.md
"""
import argparse
import re
import subprocess
from pathlib import Path

HOME = Path.home()
# Where a reference to a skill would live. Transcripts are deliberately excluded:
# this asks "does the CONFIG point at it", not "was it used".
SEARCH_ROOTS = [
    HOME / ".claude" / "skills",
    HOME / ".claude" / "agents",
    HOME / ".claude" / "hooks",
    HOME / ".claude" / "commands",
    HOME / ".claude" / "library",
    HOME / ".claude" / "CLAUDE.md",
    HOME / "Developer" / "grp-beklever-com" / "project-management" / "CLAUDE.md",
    HOME / "Developer" / "grp-beklever-com" / ".claude" / "CLAUDE.md",
]


def refs_for(name):
    """Count INSTRUCTION-SHAPED references to a skill, outside its own directory.

    A bare substring search is wrong here and produced a bad first report:
    'archive' matched every mention of an archive/ folder, 'triage' matched
    'human-triaged', 'diagnose' matched 'diagnoses are hypotheses'. Those are
    word collisions, not callers, and they inflate the referenced count enough
    to hide the real orphans.

    So require the name to appear in a shape that actually invokes or locates it:
      /name                      slash-command invocation
      skill: "name" / 'name'     Skill-tool call
      skills/name                a path to the skill directory
      `name` skill / skill `name`  prose that names it as a skill
    """
    roots = [str(p) for p in SEARCH_ROOTS if p.exists()]
    if not roots:
        return 0, []
    n = re.escape(name)
    # Emphasis markers must be optional. Requiring backticks missed
    # "via the **inbox-writer** skill" in skill-evals and nearly retired a live
    # dependency of the monthly cron sweep. Allow `x`, **x**, *x*, "x", or bare.
    q = r'["\'`*]*'
    pattern = (
        rf'(/{n}\b)'
        rf'|(skill["\s:=]+["\']?{n}["\']?)'
        rf'|(skills/{n}\b)'
        rf'|({q}{n}{q}\s+skill\b)'
        rf'|(skill\s+{q}{n}{q})'
        rf'|(invoke\s+{q}{n}{q})'
        rf'|(use\s+(the\s+)?{q}{n}{q})'
    )
    try:
        out = subprocess.run(
            ["rg", "-l", "--no-messages", "-i", pattern, *roots],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0, []
    own = f"/.claude/skills/{name}/"
    hits = [ln for ln in out.splitlines() if ln and own not in ln]
    return len(hits), hits


def parse_never(path):
    text = Path(path).read_text()
    section = text.split("## Never invoked")[1].split("## Invoked")[0]
    return re.findall(r"^- ([a-zA-Z0-9:_-]+)$", section, re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names-from",
                    default=str(HOME / ".claude" / "skill-proposals" / "USAGE-SCAN.md"))
    ap.add_argument("--out",
                    default=str(HOME / ".claude" / "skill-proposals" / "RETIREMENT-CANDIDATES.md"))
    args = ap.parse_args()

    names = parse_never(args.names_from)
    orphans, referenced = [], []
    for n in names:
        count, hits = refs_for(n)
        (orphans if count == 0 else referenced).append((n, count, hits))

    lines = [
        "# Retirement Candidates",
        "",
        "Derived from USAGE-SCAN.md. Every skill here had ZERO invocations in the",
        "scan window. This pass adds the second question: does any other skill,",
        "agent, hook, or CLAUDE.md still point at it?",
        "",
        f"## ORPHAN ({len(orphans)}) — zero invocations, zero references",
        "",
        "Nothing calls these and nothing points at them. Safest to archive.",
        "",
    ]
    lines += [f"- {n}" for n, _, _ in orphans] or ["- (none)"]
    lines += [
        "",
        f"## REFERENCED ({len(referenced)}) — zero invocations, but still wired in",
        "",
        "Do NOT archive on the count alone. Zero invocations plus a live reference",
        "means either the caller is also dead, or a documented rule is not being",
        "followed in practice. Both are worth knowing.",
        "",
    ]
    for n, c, hits in sorted(referenced, key=lambda x: -x[1]):
        short = [h.replace(str(HOME), "~") for h in hits[:3]]
        lines.append(f"- **{n}** ({c} refs) — {', '.join(short)}")
    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"orphans: {len(orphans)} | referenced: {len(referenced)}")
    print(f"report: {args.out}")


if __name__ == "__main__":
    main()
