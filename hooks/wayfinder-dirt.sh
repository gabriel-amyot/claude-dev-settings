#!/usr/bin/env bash
# Wayfinder Dirt Marker: PostToolUse hook for Bash
#
# The wayfinder viewer renders from a snapshot of GitHub Issues. The snapshot
# has a staleness window (default 6h), so a ticket resolved five minutes ago
# would not show up when the map is opened right after the work.
#
# This hook does NOT fetch and does NOT regenerate. Fetching costs a gh API
# call and about four seconds; doing that after every issue write would be
# noise on every tool call. It only TOUCHES a marker file. refresh.py sees the
# marker is newer than the snapshot and fetches on the next run, inside the
# window or not.
#
# Cost: one regex and one touch. No network, no subprocess beyond python3.
#
# Fires when a command segment actually invokes `gh` against the wayfinder
# repo, or invokes wayfinder_runs.py (which posts and closes issues).
#
# Known false positive: a segment that BEGINS with `gh ` or `wayfinder_runs.py`
# inside a quoted argument. The cost of a false positive is one extra fetch on
# the next refresh, so this fails open by design.
#
# Always exits 0. This is a bookkeeping hook, never a gate.

INPUT=$(cat)

CLAUDE_WF_DIRT_INPUT="$INPUT" python3 -c '
import os, json, re, pathlib, time

MARKER = pathlib.Path(
    "/Users/gabrielamyot/Developer/grp-beklever-com/project-management"
    "/tools/wayfinder-viewer/data/.dirty"
)
REPO = "gabriel-amyot/klever-project-management"

raw = os.environ.get("CLAUDE_WF_DIRT_INPUT", "")
try:
    data = json.loads(raw)
except Exception:
    raise SystemExit(0)          # fail open: bookkeeping never blocks work

command = (data.get("tool_input") or {}).get("command") or ""
if not command:
    raise SystemExit(0)

# Split at shell boundaries and only inspect segments that START with the
# binary, so a repo name quoted inside an unrelated command does not count.
segments = re.split(r"&&|\|\||;|\||\n|\$\(|`", command)

def invokes(binary, segment):
    return segment.lstrip(" \t(").startswith(binary)

WRITES = re.compile(
    r"\b(issue\s+(create|edit|close|reopen|comment|delete)"
    r"|api\b.*--method\s+(POST|PATCH|PUT|DELETE))"
)

touched = False
for segment in segments:
    if invokes("gh", segment) and REPO in segment and WRITES.search(segment):
        touched = True
        break
    if "wayfinder_runs.py" in segment and re.search(
        r"\b(chart|resolve|reflect)\b", segment
    ):
        touched = True
        break

if touched and MARKER.parent.is_dir():
    MARKER.touch()
' 2>/dev/null

exit 0
