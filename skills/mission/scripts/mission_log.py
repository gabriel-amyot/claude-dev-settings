"""Usage and feedback log for the mission skill (self-improvement loop).

Log: <PM>/missions/_meta/skill-usage.jsonl (committed with the PM repo, so history survives).

Usage:
  mission_log.py use --command report --mission vendor-trader-feedback [--session s] [--note "..."]
  mission_log.py feedback --text "the needs-you cards were too long" --rating -1 [--mission m] [--command report]
  mission_log.py summary [--since 2026-11-01]

rating: +1 (worked), 0 (neutral), -1 (failed or annoyed Gabriel).
Record Gabriel's words verbatim in --text. Never paraphrase feedback.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys

from mission_lib import MISSIONS_DIR, now_utc

LOG = MISSIONS_DIR / "_meta" / "skill-usage.jsonl"


def append(entry: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read(since: str | None) -> list[dict]:
    if not LOG.exists():
        return []
    rows = [json.loads(x) for x in LOG.read_text().splitlines() if x.strip()]
    return [r for r in rows if not since or r["at"] >= since]


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("use")
    u.add_argument("--command", required=True)
    u.add_argument("--mission", default=None)
    u.add_argument("--session", default=None)
    u.add_argument("--note", default=None)
    fb = sub.add_parser("feedback")
    fb.add_argument("--text", required=True)
    fb.add_argument("--rating", type=int, choices=[-1, 0, 1], required=True)
    fb.add_argument("--mission", default=None)
    fb.add_argument("--command", default=None)
    fb.add_argument("--session", default=None)
    s = sub.add_parser("summary")
    s.add_argument("--since", default=None)
    a = ap.parse_args()

    if a.cmd == "use":
        append({"at": now_utc(), "event": "use", "command": a.command, "mission": a.mission, "session": a.session, "note": a.note})
        print(f"logged use: {a.command}")
    elif a.cmd == "feedback":
        append({"at": now_utc(), "event": "feedback", "rating": a.rating, "text": a.text, "mission": a.mission,
                "command": a.command, "session": a.session})
        print("logged feedback")
    else:
        rows = read(a.since)
        uses = collections.Counter(r["command"] for r in rows if r["event"] == "use")
        fbs = [r for r in rows if r["event"] == "feedback"]
        score = sum(r["rating"] for r in fbs)
        print(f"entries: {len(rows)}  uses: {sum(uses.values())}  feedback: {len(fbs)}  net rating: {score:+d}")
        for cmd, n in uses.most_common():
            print(f"  use {cmd}: {n}")
        print("negative feedback (newest first):")
        for r in sorted((r for r in fbs if r["rating"] < 0), key=lambda r: r["at"], reverse=True)[:20]:
            print(f"  {r['at'][:10]} [{r.get('command') or '-'}] {r['text']}")
        print("positive feedback (newest first):")
        for r in sorted((r for r in fbs if r["rating"] > 0), key=lambda r: r["at"], reverse=True)[:10]:
            print(f"  {r['at'][:10]} [{r.get('command') or '-'}] {r['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
