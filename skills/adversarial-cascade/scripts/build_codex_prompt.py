#!/usr/bin/env python3
"""Write the Codex adversarial-review prompt for one round to disk.

    build_codex_prompt.py --out <prompt.txt> --repo <abs repo> --base <ref> --round <N>
                          [--files f1,f2,...] [--invariants <file>] [--spec <file>]
                          [--previous <prior round triage file>] [--fix-range <prev>..<fix>]
                          [--word-cap 900]

Round 1 attacks the branch diff. Every later round MUST pass --previous and --fix-range: it re-checks the
fixes, attacks what those fixes could break, and keeps the unchanged context (a diff-only re-check
produces false positives and misses regressions introduced by fixes; see the Codex SOP).
Prompt content is plain text. The prompt is never built with a shell heredoc (heredocs hang the Bash tool).
"""
import argparse
import os
import sys

RUBRIC = """SEVERITY RUBRIC (use exactly these four words):
- CRITICAL: data loss, security or auth bypass, corrupts state, or breaks an existing passing behaviour.
- MAJOR: wrong result a user or a downstream consumer sees, or a guard/test that cannot fail.
- MINOR: edge case with low reach, weak but not wrong assertion, maintainability risk.
- NIT: wording, naming, style. Never blocks."""

OUTPUT_CONTRACT = """OUTPUT CONTRACT (follow exactly; a parser reads it):
For each finding write one block:
### F<n> [<SEVERITY>] <one-line title>
File: <path>:<line>
Scenario: <concrete input or sequence that fails, and what the user sees>
Fix: <the smallest concrete change>
Label: CONFIRMED (you read the code path) or UNVERIFIED (inferred; say what would confirm it)

If a dimension is clean, say so in one line. Do not invent findings to fill space.
Emit the entire review as your final message.
End with exactly one line: VERDICT: PASS or VERDICT: BLOCK
(BLOCK only when at least one CRITICAL or MAJOR finding is listed above.)"""


def read_optional(path):
    if not path:
        return ""
    with open(path) as handle:
        return handle.read().strip()


def build(args):
    files = [f.strip() for f in (args.files or "").split(",") if f.strip()]
    parts = [
        "ROLE: You are a hostile reviewer. Your job is to DISPROVE that this change is safe to ship. Do not confirm.",
        "RULES: Read-only. Do not modify files. Do not run commands that write. Do not load skills or switch modes.",
        f"REPO: {args.repo}",
        f"BASE: {args.base}. Inspect the change with: git -C {args.repo} diff {args.base}...HEAD",
    ]
    if files:
        parts.append("FILES IN SCOPE (read these; read callers only when a finding needs them):\n" + "\n".join(f"- {f}" for f in files))
    spec = read_optional(args.spec)
    if spec:
        parts.append("SPEC / ACCEPTANCE CRITERIA:\n" + spec)
    invariants = read_optional(args.invariants)
    if invariants:
        parts.append("NON-NEGOTIABLE INVARIANTS OF THIS REPO:\n" + invariants)
    parts.append("""ATTACK LIST:
1. Logic: wrong conditionals, off-by-one, null or empty paths, error branches that swallow failures.
2. Contract: does the code do what the spec says, for every listed item, as worded?
3. Callers: existing callers and downstream consumers this change can break.
4. Security: injection, auth or permission gaps, secrets in code or logs.
5. Tests: a test that would still pass if the fix were reverted; assertions against the code's own output.
6. Scope: code beyond what the spec asks for.""")
    if args.round > 1:
        previous = read_optional(args.previous)
        if not previous or not args.fix_range:
            raise SystemExit("round >= 2 needs --previous <triage file> and --fix-range <prev>..<fix>")
        parts.append(f"""THIS IS ROUND {args.round}. The previous round's findings and what was done about them:
{previous}

The fixes are in: git -C {args.repo} diff {args.fix_range}
Do three things:
a. Check each fix actually resolves its finding.
b. Attack what each FIX could break: new regressions, a guard that now hides a defect, a check that became weaker.
c. Keep the unchanged context in view. A finding that an unchanged helper already guards is not a finding.
Do not re-report a finding the previous round rejected with evidence unless you have NEW evidence.""")
    parts.append(RUBRIC)
    parts.append(f"Keep the review under {args.word_cap} words.")
    parts.append(OUTPUT_CONTRACT)
    return "\n\n".join(parts) + "\n"


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--base", default="origin/dev")
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--files")
    p.add_argument("--invariants")
    p.add_argument("--spec")
    p.add_argument("--previous")
    p.add_argument("--fix-range")
    p.add_argument("--word-cap", type=int, default=900)
    args = p.parse_args(argv)
    text = build(args)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as handle:
        handle.write(text)
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
