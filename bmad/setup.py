#!/usr/bin/env python3
"""Restore the small BMAD user-level entry points without replacing other settings."""
import argparse
from pathlib import Path

START = "<!-- shared-bmad-loading:start -->"
END = "<!-- shared-bmad-loading:end -->"
RULE = """<!-- shared-bmad-loading:start -->
## BMAD loading

Load `~/.claude-shared-config/skills/bmad/SKILL.md` only for an explicit BMAD request or BMAD command.
Use its index, then read only the selected definition and required dependencies. Keep unselected personas, workflows and sidecars unread.
Explicitly invoked workflows may load their declared BMAD dependencies. Use the active project's domain context and placement rules.
Report unavailable definitions instead of inventing replacements. Generic role-related work does not activate BMAD.
<!-- shared-bmad-loading:end -->"""


def add_rule(path):
    text = path.read_text() if path.exists() else ""
    if (START in text) != (END in text) or text.count(START) > 1:
        raise ValueError("Malformed existing BMAD block: " + str(path))
    if START in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        want = before + RULE + after
    else:
        want = text.rstrip() + ("\n\n" if text.strip() else "") + RULE + "\n"
    if text != want:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(want)
        print("Updated " + str(path))


def link(target, destination):
    if destination.is_symlink() and destination.resolve() == target.resolve():
        return
    if destination.exists() and destination.resolve() == target.resolve():
        return
    if destination.exists() or destination.is_symlink():
        raise ValueError("Conflicting BMAD path, preserved: " + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(target, target_is_directory=target.is_dir())
    print("Linked " + str(destination))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    shared = Path(__file__).resolve().parent.parent
    # Check all conflicting skill paths before writing user instructions.
    target = shared / "skills/bmad"
    if not (target / "SKILL.md").is_file():
        raise ValueError("Shared BMAD router is missing")
    destinations = [home / ".agents/skills/bmad", home / ".claude/skills/bmad"]
    for dest in destinations:
        if (dest.exists() or dest.is_symlink()) and dest.resolve() != target.resolve():
            raise ValueError("Conflicting BMAD path, preserved: " + str(dest))
    for dest in destinations:
        link(target, dest)
    add_rule(shared / "CLAUDE.md")
    add_rule(home / ".codex/AGENTS.md")
    claude = home / ".claude/CLAUDE.md"
    if not claude.exists() and not claude.is_symlink():
        link(shared / "CLAUDE.md", claude)
    elif claude.resolve() != (shared / "CLAUDE.md").resolve():
        add_rule(claude)
    print("BMAD user entry points ready")


if __name__ == "__main__":
    main()
