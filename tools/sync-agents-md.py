#!/usr/bin/env python3
"""Mirror every tracked CLAUDE.md to a sibling AGENTS.md.

AGENTS.md is the cross-tool convention (Codex, Cursor, Copilot, Gemini CLI). This keeps
those tools on the same rules as Claude Code without maintaining a second document by hand.

The mirror is generated. Edit CLAUDE.md; never edit AGENTS.md.

Usage:
  sync-agents-md.py              # write any out-of-date mirror
  sync-agents-md.py --check      # exit 1 if any mirror is stale, write nothing
  sync-agents-md.py --hook       # hook mode: silent unless something changed
"""
import hashlib
import sys
from pathlib import Path

# (source CLAUDE.md, generated AGENTS.md). Add a pair to extend the mirror.
PAIRS = [
    (Path.home() / ".claude-shared-config/CLAUDE.md",
     Path.home() / ".claude-shared-config/AGENTS.md"),
    (Path.home() / "Developer/grp-beklever-com/project-management/CLAUDE.md",
     Path.home() / "Developer/grp-beklever-com/project-management/AGENTS.md"),
    (Path.home() / "Developer/grp-beklever-com/.claude/CLAUDE.md",
     Path.home() / "Developer/grp-beklever-com/AGENTS.md"),
]

MARKER = "<!-- generated-mirror-of-claude-md -->"


def header(source: Path, digest: str) -> str:
    try:
        shown = f"~/{source.relative_to(Path.home())}"
    except ValueError:
        shown = str(source)
    return f"""{MARKER}
<!-- source: {shown} -->
<!-- source-sha256: {digest} -->

> **Generated file. Do not edit.**
>
> This is a verbatim mirror of `{shown}`, kept in sync so that Codex, Cursor,
> Copilot and Gemini CLI read the same rules as Claude Code.
>
> To change anything here, edit the CLAUDE.md above. Regenerate with
> `python3 ~/.claude-shared-config/tools/sync-agents-md.py`.
>
> **Claude Code agents: if you have already loaded the CLAUDE.md named above, do NOT
> also load this file.** It is the same content and would double your context cost.

---

"""


def render(source: Path) -> str:
    body = source.read_text()
    digest = hashlib.sha256(body.encode()).hexdigest()[:16]
    return header(source, digest) + body


def main() -> int:
    check = "--check" in sys.argv
    hook = "--hook" in sys.argv
    stale, wrote, missing = [], [], []

    for source, target in PAIRS:
        if not source.exists():
            missing.append(source)
            continue
        want = render(source)
        have = target.read_text() if target.exists() else None

        if have == want:
            continue
        if have is not None and MARKER not in have.split("\n", 1)[0]:
            print(f"REFUSING to overwrite hand-written file: {target}", file=sys.stderr)
            print("  It has no generated-mirror marker. Move it aside first.", file=sys.stderr)
            return 2
        if check:
            stale.append(target)
        else:
            target.write_text(want)
            wrote.append(target)

    for m in missing:
        print(f"warning: source missing, skipped: {m}", file=sys.stderr)

    if check:
        for s in stale:
            print(f"STALE: {s}")
        if stale:
            print(f"\n{len(stale)} mirror(s) out of date. Run sync-agents-md.py to fix.")
            return 1
        if not hook:
            print(f"All {len(PAIRS) - len(missing)} mirror(s) current.")
        return 0

    if wrote:
        for w in wrote:
            print(f"synced: {w}")
    elif not hook:
        print(f"All {len(PAIRS) - len(missing)} mirror(s) already current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
