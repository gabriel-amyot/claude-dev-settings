#!/usr/bin/env python3
"""Layer A contract suite: the worktree skill is ours, and stays ours.

Migration invariants, 2026-09-10. `using-git-worktrees` used to live only in the
superpowers plugin cache, with a drifted second copy under library/practices. Both were
unowned, and the older copy carried a weaker gitignore check. This suite pins the outcome
of owning it.

Deterministic, judge-free, no model calls. Safe for the unattended sweep.

Hardened 2026-09-10 after a Codex adversarial pass returned "not trustworthy". Fixes:
  - the plugin-cache scan now looks at the REAL cache (~/.claude/plugins/), which is not
    under shared-config, so the original case could never see it
  - a plugin bump is now a RED test, not a silent event (case 07)
  - the ignore-check cases inspect fenced commands and the decision MECHANISM, instead of
    substring-matching text that also appears in prose (cases 04, 05)
  - the EXEMPT allowlist is itself asserted, so widening it cannot silently disable
    cases 06/09 (case 10)

Usage: python3 run_vendored_skill_evals.py [-v]
Exits non-zero on any failure.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SHARED = Path.home() / ".claude-shared-config"
CLAUDE = Path.home() / ".claude"
OWNED = SHARED / "skills/using-git-worktrees/SKILL.md"
TOMBSTONE = SHARED / "library/practices/development/using-git-worktrees-isolated-branches.md"

# The REAL plugin cache. Not under SHARED — that was the original bug.
PLUGIN_GLOB = "plugins/cache/*/superpowers/*/skills/using-git-worktrees/SKILL.md"

# Frozen allowlist. Case 10 asserts this exact set, so widening it to disable other
# cases fails loudly. Every entry is a path fragment that legitimately still names the
# old prefixed skill: historical transcripts, archives, the migration design doc, and
# the files this suite is about.
EXEMPT = (
    "/.specstory/",
    "/_archive/",
    "/library/archive/",
    "/docs/specs/2026-09-10-git-consolidation-design.md",
    "/hooks/evals/run_vendored_skill_evals.py",
    "/library/practices/development/using-git-worktrees-isolated-branches.md",
    "/skills/using-git-worktrees/SKILL.md",
)

# Case 09 must see the tombstone: it is the one path where a fork already grew once.
EXEMPT_FOR_DUPLICATE_SCAN = tuple(
    e for e in EXEMPT if "using-git-worktrees-isolated-branches" not in e
)


def _frontmatter(path):
    """Return the YAML frontmatter block as text, or '' if absent."""
    body = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", body, re.S)
    return m.group(1) if m else ""


def _fenced_blocks(path):
    return re.findall(r"```[a-zA-Z]*\n(.*?)```", path.read_text(), re.S)


def _grep(pattern, exempt=EXEMPT):
    proc = subprocess.run(
        ["grep", "-rn", "--binary-files=without-match", pattern, str(SHARED)],
        capture_output=True, text=True,
    )
    hits = []
    for line in proc.stdout.splitlines():
        path = line.split(":", 1)[0]
        if not any(frag in path for frag in exempt):
            hits.append(line.replace(str(Path.home()), "~"))
    return hits


def _installed_plugin_copies():
    return sorted(CLAUDE.glob(PLUGIN_GLOB))


def case_01_owned_copy_exists():
    return [] if OWNED.is_file() else [f"owned skill missing at {OWNED}"]


def case_02_owned_has_nav_block():
    if not OWNED.is_file():
        return ["owned skill missing"]
    fm = _frontmatter(OWNED)
    problems = []
    if not fm:
        return ["owned skill has no YAML frontmatter"]
    if not re.search(r"^nav:", fm, re.M):
        problems.append("no nav: block (house requirement)")
    if not re.search(r"^\s+bay:", fm, re.M):
        problems.append("nav block has no bay:")
    return problems


def case_03_owned_records_upstream():
    """A merge-by-hand policy needs real upstream coordinates, not just a marker."""
    if not OWNED.is_file():
        return ["owned skill missing"]
    fm = _frontmatter(OWNED)
    if not re.search(r"^upstream:", fm, re.M):
        return ["no upstream: block (needed to merge plugin bumps by hand)"]
    problems = []
    for field in ("source", "vendored_at", "merge_policy"):
        if not re.search(rf"^\s+{field}:", fm, re.M):
            problems.append(f"upstream block missing required field {field!r}")
    return problems


SAFETY_HEADING = "## Safety Verification"


def _section(path, heading):
    """Text from `heading` up to the next same-level heading."""
    body = path.read_text()
    start = body.find(heading)
    if start == -1:
        return ""
    rest = body[start + len(heading):]
    end = re.search(r"^## ", rest, re.M)
    return rest[: end.start()] if end else rest


def _safety_commands(path):
    """Executable (non-comment) lines from fenced blocks in the Safety section only.

    Scoped to the section on purpose. Codex finding 1 showed a whole-file check passing
    when the operative line was deleted, because `git check-ignore` also appears in the
    Common Mistakes prose AND inside the Example Workflow fence.
    """
    section = _section(path, SAFETY_HEADING)
    lines = []
    for block in re.findall(r"```[a-zA-Z]*\n(.*?)```", section, re.S):
        for line in block.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    return lines


def case_04_operative_check_is_check_ignore():
    """The COMMAND in the Safety section must use git check-ignore.

    Codex finding 1. First fix attempt still passed this mutation because the Example
    Workflow fence also mentions the command; hence the section scope and the
    comment-line filter.
    """
    if not OWNED.is_file():
        return ["owned skill missing"]
    if not _section(OWNED, SAFETY_HEADING):
        return [f"{SAFETY_HEADING!r} section is gone"]
    commands = _safety_commands(OWNED)
    if not commands:
        return ["Safety Verification section has no executable command"]
    if not any("git check-ignore" in c for c in commands):
        return ["no executable command in Safety Verification uses `git check-ignore` "
                "(prose and example-workflow mentions do not count)"]
    return []


def case_05_decision_is_not_gitignore_text_matching():
    """Reject the MECHANISM, not one exact string.

    Codex finding 2: the original blacklist matched one double-quoted grep and would
    pass the same broken logic with single quotes, `rg`, or different spacing.
    """
    if not OWNED.is_file():
        return ["owned skill missing"]
    problems = []
    for line in _safety_commands(OWNED):
        reads_gitignore = re.search(r"\b(grep|rg|ag|awk|sed|cat)\b[^|]*\.gitignore", line)
        if reads_gitignore and "check-ignore" not in line:
            problems.append(
                f"decides ignore-status by reading .gitignore text: {line!r}")
    return problems


def case_06_no_prefixed_references():
    return [f"stale prefixed reference: {h}" for h in _grep("superpowers:using-git-worktrees")]


def case_07_plugin_bump_is_red():
    """A plugin upgrade must fail this suite until someone merges by hand.

    Codex finding 4: the original case grepped shared-config for 'plugins/cache', but
    the real cache lives under ~/.claude/plugins, so it inspected nothing. It also had
    no notion of the upstream version changing.
    """
    if not OWNED.is_file():
        return ["owned skill missing"]
    fm = _frontmatter(OWNED)
    m = re.search(r"^\s+vendored_at:\s*(\S+)", fm, re.M)
    if not m:
        return ["upstream.vendored_at absent; cannot detect a plugin bump"]
    pinned = m.group(1).strip().strip('"\'')

    installed = _installed_plugin_copies()
    if not installed:
        return []

    versions = sorted({p.parts[-4] for p in installed})
    if pinned not in versions:
        return [
            f"superpowers plugin now at {versions}, but upstream.vendored_at pins "
            f"{pinned!r}. Diff upstream against the owned skill, merge by hand, then "
            f"bump vendored_at."
        ]
    return []


def case_08_tombstone_is_a_stub():
    if not TOMBSTONE.is_file():
        return ["tombstone missing; INDEX.md and old transcripts point at it"]
    body = TOMBSTONE.read_text()
    problems = []
    if "superseded_by:" not in body:
        problems.append("no superseded_by pointer")
    if len(body.splitlines()) > 60:
        problems.append(f"regrown to {len(body.splitlines())} lines (stub budget 60)")
    procedure_markers = ("## Directory Selection Process", "## Creation Steps",
                         "git worktree add", "## Safety Verification")
    for marker in procedure_markers:
        if marker in body:
            problems.append(f"contains procedure content again: {marker!r}")
    return problems


def case_09_exactly_one_authoritative_copy():
    """Scans the tombstone too — that is where a fork already grew once."""
    hits = []
    for marker in ("## Directory Selection Process", "## Creation Steps"):
        hits += _grep(marker, exempt=EXEMPT_FOR_DUPLICATE_SCAN)
    return [f"second copy of the procedure: {h}" for h in hits]


def case_10_exempt_allowlist_is_pinned():
    """Guards the guard.

    Codex finding 7: widening EXEMPT to ('/',) made cases 06/07/09 inspect nothing and
    stay green. Nothing validated the exemption scope.
    """
    expected = {
        "/.specstory/",
        "/_archive/",
        "/library/archive/",
        "/docs/specs/2026-09-10-git-consolidation-design.md",
        "/hooks/evals/run_vendored_skill_evals.py",
        "/library/practices/development/using-git-worktrees-isolated-branches.md",
        "/skills/using-git-worktrees/SKILL.md",
    }
    problems = []
    if set(EXEMPT) != expected:
        added = set(EXEMPT) - expected
        removed = expected - set(EXEMPT)
        if added:
            problems.append(f"EXEMPT widened with {sorted(added)} — justify and pin it here")
        if removed:
            problems.append(f"EXEMPT narrowed, dropped {sorted(removed)}")
    for frag in EXEMPT:
        if len(frag.strip("/")) < 8:
            problems.append(f"EXEMPT entry {frag!r} is too broad to be a real exemption")
    if "using-git-worktrees-isolated-branches" in " ".join(EXEMPT_FOR_DUPLICATE_SCAN):
        problems.append("tombstone must NOT be exempt from the duplicate scan")
    return problems


CASES = [
    ("01-owned-copy-exists", case_01_owned_copy_exists,
     "the migration's whole point"),
    ("02-owned-has-nav-block", case_02_owned_has_nav_block,
     "house requirement for every SKILL.md"),
    ("03-owned-records-upstream", case_03_owned_records_upstream,
     "merge-by-hand on a bump needs real coordinates, not a marker"),
    ("04-operative-check-is-check-ignore", case_04_operative_check_is_check_ignore,
     "the COMMAND must be correct; prose mentions are not coverage"),
    ("05-decision-not-gitignore-text", case_05_decision_is_not_gitignore_text_matching,
     "reject the broken mechanism, not one exact string"),
    ("06-no-prefixed-references", case_06_no_prefixed_references,
     "a stale superpowers: reference routes back to the vendored copy"),
    ("07-plugin-bump-is-red", case_07_plugin_bump_is_red,
     "a silent plugin bump is how the drift returns"),
    ("08-tombstone-is-a-stub", case_08_tombstone_is_a_stub,
     "the fork must not regrow where it already grew once"),
    ("09-exactly-one-authoritative-copy", case_09_exactly_one_authoritative_copy,
     "two copies with no owner is how the drift happened"),
    ("10-exempt-allowlist-pinned", case_10_exempt_allowlist_is_pinned,
     "guards the guard: a widened EXEMPT silently disables other cases"),
]


def run(verbose=False):
    failed = 0
    for name, fn, why in CASES:
        problems = fn()
        ok = not problems
        if not ok:
            failed += 1
        if verbose or not ok:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
            for p in problems:
                print(f"        {p}")
            if not ok:
                print(f"        why: {why}")

    total = len(CASES)
    print(f"\nharness/no-vendored-worktree-skill: {total - failed}/{total} passed")
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    return run(ap.parse_args().verbose)


if __name__ == "__main__":
    sys.exit(main())
