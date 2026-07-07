#!/usr/bin/env python3
"""save_proof.py — persist the most recent ui-probe screenshot to a durable file.

Why this exists: in Claude Code, the claude-in-chrome `computer` screenshot with
`save_to_disk: true` delivers the image INLINE in the conversation (base64 embedded
in the session transcript) and returns an ID, not a filesystem path. The inline image
reaches a direct/interactive caller for free, but it does NOT propagate from a subagent
back to its orchestrator — only the subagent's final text does. So when a caller needs
a durable artifact (sprint-close evidence, a Jira attachment, an orchestrator that will
`Read` the file), we extract the latest inline image out of the session transcript and
write it where it belongs.

Usage:
    python3 save_proof.py --dest tickets/KTP/KTP-504/KTP-505/design/screenshots/KTP-505-AC2-2026-06-16.png
    # optional: --transcript <path.jsonl> to skip auto-discovery
    #           --cwd <dir>               to encode a different project root (default: $PWD)

It prints the absolute destination path on success (put that on the report's Proof line),
or a non-zero exit + message if no inline image was found (then report what you observed
in words rather than fabricating a file).

Note: the captured image is whatever format the MCP returned (often jpeg). The file is
written verbatim; name the --dest extension to match if you care (.jpeg vs .png), or leave
.png — consumers key off the path, not the magic bytes.
"""
import argparse, base64, glob, json, os, sys


def encode_project_dir(cwd: str) -> str:
    # Claude Code stores transcripts under ~/.claude/projects/<cwd-with-slashes-as-dashes>/
    return os.path.expanduser("~/.claude/projects/") + cwd.replace("/", "-")


def latest_inline_image(jsonl_path: str):
    """Return (b64_data, media_type) for the LAST inline image in the transcript, or None."""
    found = None
    try:
        with open(jsonl_path) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                stack = [obj]
                while stack:
                    o = stack.pop()
                    if isinstance(o, dict):
                        if o.get("type") == "image" and isinstance(o.get("source"), dict):
                            d = o["source"].get("data")
                            if d:
                                found = (d, o["source"].get("media_type"))  # last wins
                        stack.extend(o.values())
                    elif isinstance(o, list):
                        stack.extend(o)
    except OSError:
        return None
    return found


def discover_image(project_dir: str):
    """Find the latest inline image across the project's transcripts.

    Other sessions and background subagents write .jsonl files concurrently, so the
    single newest file in the tree may belong to someone else and hold no image.
    Walk candidates newest-first and return the first that actually contains an image —
    that's the transcript the capturing agent just wrote to.
    Returns ((b64, media_type), jsonl_path) or (None, None).
    """
    candidates = glob.glob(os.path.join(project_dir, "**", "*.jsonl"), recursive=True)
    for jsonl in sorted(candidates, key=os.path.getmtime, reverse=True):
        img = latest_inline_image(jsonl)
        if img:
            return img, jsonl
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True, help="where to write the screenshot file")
    ap.add_argument("--transcript", help="explicit transcript .jsonl (skips auto-discovery)")
    ap.add_argument("--cwd", default=os.getcwd(), help="project root to encode (default: $PWD)")
    args = ap.parse_args()

    if args.transcript:
        if not os.path.exists(args.transcript):
            print(f"save_proof: transcript not found: {args.transcript}", file=sys.stderr)
            return 2
        img = latest_inline_image(args.transcript)
        if not img:
            print(f"save_proof: no inline image in {args.transcript} — was a screenshot captured?", file=sys.stderr)
            return 3
    else:
        project_dir = encode_project_dir(args.cwd)
        img, jsonl = discover_image(project_dir)
        if not img:
            print(f"save_proof: no inline image found under {project_dir} — was a screenshot captured this session?", file=sys.stderr)
            return 3

    os.makedirs(os.path.dirname(os.path.abspath(args.dest)), exist_ok=True)
    with open(args.dest, "wb") as out:
        out.write(base64.b64decode(img[0]))
    print(os.path.abspath(args.dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
