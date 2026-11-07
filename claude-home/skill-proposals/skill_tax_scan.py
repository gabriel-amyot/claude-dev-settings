#!/usr/bin/env python3
"""Measure the real always-on cost of the installed skill set.

A raw skill COUNT is a poor bloat metric. Skills are progressively disclosed:
only the name and description load at session start; the body loads on
invocation. So the standing tax is description size, paid on every session,
plus the risk that a vague description fires when it should not.

That means a narrowly-scoped skill nobody triggers is nearly free, while one
broad skill with a 200-word description costs more than five precise ones.
This reports the tax so a cap can be set on something real.

Two numbers per skill:
  desc_chars  - always-on cost, charged every session
  breadth     - a rough trigger-precision proxy. Counts generic verbs and
                bare common nouns in the description. High breadth plus high
                desc_chars is the expensive combination worth fixing.

Usage: python3 skill_tax_scan.py [--out TAX-REPORT.md]
"""
import argparse
import re
from pathlib import Path

SKILLS = Path.home() / ".claude" / "skills"

# Words that make a description fire broadly. A description built mostly from
# these matches many situations and invites mis-triggering.
GENERIC = {
    "code", "file", "files", "work", "task", "check", "run", "review", "update",
    "create", "build", "fix", "test", "data", "project", "help", "manage",
    "process", "handle", "use", "make", "get", "any", "all", "thing", "stuff",
    "change", "changes", "new", "issue", "issues", "report", "write",
}


def parse_frontmatter(path):
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return None, None
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end == -1:
        return None, None
    fm = text[3:end]
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    # description may be quoted and may span lines until the next top-level key
    desc = re.search(r"^description:\s*(.+?)(?=\n[a-zA-Z_-]+:|\Z)", fm, re.M | re.S)
    return (name.group(1).strip() if name else None,
            desc.group(1).strip().strip('"\'') if desc else None)


def breadth(desc):
    words = re.findall(r"[a-zA-Z']+", desc.lower())
    if not words:
        return 0.0
    return round(100 * sum(w in GENERIC for w in words) / len(words), 1)



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
    ap.add_argument("--out", default=str(Path.home() / ".claude" / "skill-proposals" / "TAX-REPORT.md"))
    args = ap.parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from skill_usage_scan import installed_skill_paths

    rows = []
    for display_name, sk in sorted(installed_skill_paths().items()):
        name, desc = parse_frontmatter(sk)
        if not desc:
            rows.append((display_name, 0, 0.0, "NO DESCRIPTION"))
            continue
        rows.append((display_name, len(desc), breadth(desc), ""))

    total = sum(r[1] for r in rows)
    by_size = sorted(rows, key=lambda r: -r[1])
    # expensive = big AND vague
    risky = sorted([r for r in rows if r[1] > 300 and r[2] >= 8], key=lambda r: -r[1])
    missing = [r for r in rows if r[3]]

    lines = [
        "# Skill Tax Report",
        "",
        f"Skills measured: {len(rows)}.",
        f"Installed description characters (inventory estimate): **{total:,}** "
        f"(~{total // 4:,} tokens).",
        f"Mean per skill: {total // max(len(rows), 1):,} chars.",
        "",
        "This measures discovered description text, not observed prompt loading or exact tokens.",
        "Bodies and host-specific selection/truncation are outside this estimate.",
        "Treat this as a maintenance signal, not billing or usage telemetry.",
        "",
        "## The 20 most expensive descriptions",
        "",
        "| Skill | Chars | Generic-word % |",
        "|---|---|---|",
    ]
    lines += [f"| {n} | {c:,} | {b} |" for n, c, b, _ in by_size[:20]]
    lines += [
        "",
        f"The top 20 account for {sum(r[1] for r in by_size[:20]):,} chars, "
        f"{round(100 * sum(r[1] for r in by_size[:20]) / max(total, 1))}% of the total.",
        "",
        "## Broad AND expensive — the ones worth rewriting",
        "",
        "Long description built largely from generic verbs. These are the",
        "mis-trigger risks: they cost the most to carry and match the most",
        "situations they were not written for.",
        "",
        "| Skill | Chars | Generic-word % |",
        "|---|---|---|",
    ]
    lines += [f"| {n} | {c:,} | {b} |" for n, c, b, _ in risky] or ["| (none) | | |"]
    if missing:
        lines += ["", "## Missing a description (never routes correctly)", ""]
        lines += [f"- {n}" for n, _, _, _ in missing]
    Path(args.out).write_text("\n".join(lines) + "\n")
    publish_harness("tax-scan", args.out)
    print(f"skills: {len(rows)} | total desc chars: {total:,} (~{total//4:,} tokens)")
    print(f"broad+expensive: {len(risky)} | missing description: {len(missing)}")
    print(f"report: {args.out}")


if __name__ == "__main__":
    main()
