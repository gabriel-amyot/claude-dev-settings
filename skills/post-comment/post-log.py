#!/usr/bin/env python3
"""Audit log writer for /post-comment. Appends YAML entries."""

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path


def write_entry(log_path: str, entry: dict):
    """Append a YAML entry to the log file."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"- timestamp: \"{entry['timestamp']}\"")
    lines.append(f"  platform: \"{entry['platform']}\"")
    lines.append(f"  target: \"{entry['target']}\"")
    lines.append(f"  template: \"{entry['template']}\"")
    lines.append(f"  draft_path: \"{entry['draft_path']}\"")
    lines.append(f"  posted_url: \"{entry.get('posted_url', '')}\"")
    lines.append(f"  content_hash: \"{entry['content_hash']}\"")
    lines.append(f"  action: \"{entry.get('action', 'new')}\"")
    if entry.get("replaces_hash"):
        lines.append(f"  replaces_hash: \"{entry['replaces_hash']}\"")
    lines.append("")

    with open(path, "a") as f:
        f.write("\n".join(lines) + "\n")


def find_log_path(ticket: str = "") -> str:
    """Determine log path from ticket context or fall back to global."""
    if ticket:
        base = Path.cwd()
        ticket_log = base / f"tickets/{ticket}/reports/ship/post-log.yaml"
        if ticket_log.parent.exists() or (base / f"tickets/{ticket}").exists():
            return str(ticket_log)
    return str(Path.home() / ".claude-shared-config/skills/post-comment/global-post-log.yaml")


def main():
    parser = argparse.ArgumentParser(description="Log a posted comment to audit trail")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--target", required=True, help="URL or identifier of the target")
    parser.add_argument("--template", required=True, help="Template name used")
    parser.add_argument("--draft", required=True, help="Path to draft file")
    parser.add_argument("--posted-url", default="", help="URL of the posted comment")
    parser.add_argument("--content", required=True, help="Final rendered content (for hashing)")
    parser.add_argument("--ticket", default="", help="Ticket ID for log placement")
    parser.add_argument("--action", default="new", choices=["new", "edit", "delete"],
                        help="Action type: new, edit, or delete")
    parser.add_argument("--replaces-hash", default="",
                        help="Content hash of the comment being replaced (for edits)")
    args = parser.parse_args()

    content_hash = hashlib.sha256(args.content.encode()).hexdigest()[:12]
    log_path = find_log_path(args.ticket)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": args.platform,
        "target": args.target,
        "template": args.template,
        "draft_path": args.draft,
        "posted_url": args.posted_url,
        "content_hash": content_hash,
        "action": args.action,
        "replaces_hash": args.replaces_hash if args.replaces_hash else None,
    }

    write_entry(log_path, entry)
    print(f"Logged to {log_path} (action: {args.action})")


if __name__ == "__main__":
    main()
