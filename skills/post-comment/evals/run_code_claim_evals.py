#!/usr/bin/env python3
"""
run_code_claim_evals.py — deterministic eval suite for verify-code-claims.py.

verify-code-claims.py is the KTP-688 Layer B gate: it blocks an external post that cites a
code location (`bigquery.py:46`, `sub_agents/data_routing/agent.py:97`, ranges like `foo.py:10-20`)
unless the citation carries a deploy-identity STAMP on the same line
(`[VERIFIED against dev@<sha>]` or `[UNVERIFIED — read on main, deploy=dev]`).

Each fixture is a draft an agent might try to post; `expected` is the gate's exit code
(0 = OK/warn, 2 = BLOCK) and `needle` is a substring that must appear in the gate's output
(None = don't care). Fixtures are materialized to a temp dir at runtime, so the suite is
self-contained. Every red-team finding below is encoded as a fixture that PINS the gate's
CURRENT behavior — evasions the regex misses are marked `# KNOWN GAP` and listed in the report.

Usage: python3 run_code_claim_evals.py [--script <path>] [-v]
Exit 0 if all cases pass, 1 otherwise.
"""
import argparse
import os
import subprocess
import sys
import tempfile

DEFAULT_SCRIPT = os.path.expanduser(
    "~/.claude-shared-config/skills/post-comment/verify-code-claims.py")

# Fenced code block containing a bare citation. The gate does NOT parse markdown — it scans
# every physical line — so a citation inside ``` still blocks. Pinned intentionally: a stack
# trace pasted into a fence is exactly the case where a main-vs-dev line-ref must be stamped.
FENCED_CITE = "```\nTraceback: bigquery.py:46 in _build_result\n```"

# name -> (draft text, expected exit, needle-in-output or None)
FIXTURES = {
    # === SEED (from the approved plan) ===============================================
    "01-seed-bare-cite-no-stamp": (
        "The bug is at bigquery.py:46 — the bare except swallows the to_html error.",
        2, "BLOCKED"),
    "02-seed-verified-stamp": (
        "The bug is at bigquery.py:46 [VERIFIED against dev@bae8f58] — the except swallows it.",
        0, "OK"),
    "03-seed-unverified-stamp": (
        "The bug is at bigquery.py:46 [UNVERIFIED — read on main, deploy=dev].",
        0, "UNVERIFIED"),

    # === TRUE POSITIVES: unstamped code-location citation must BLOCK (exit 2) =========
    "04-multi-dir-path": (
        "sub_agents/data_routing/agent.py:97 drops the exception before it reaches the router.",
        2, "BLOCKED"),
    "05-range-citation": (
        "The guardless block spans foo.py:10-20, so any NUMERIC column hits the cap.",
        2, "foo.py:10-20"),
    "06-java-extension": (
        "The stale assertion is at StatePerformanceAdapter.java:212 in the test.",
        2, "BLOCKED"),
    "07-second-line-unstamped": (
        # First citation is stamped, but a SECOND citation on a later line is not.
        # Stamps are per-line, so the unstamped one still blocks the whole draft.
        "first: bigquery.py:46 [VERIFIED against dev@aaa1111]\n"
        "and also flow.py:97 with no stamp at all",
        2, "flow.py:97"),

    # --- behavior PINS (verified 2026-07-07 against the live gate) ---
    "08-backtick-wrapped-cite": (
        # Backticks are not word chars and do NOT shield the citation — the \b boundary still
        # matches inside `...`. Pinned: wrapping a ref in code font is not an escape hatch.
        "See `bigquery.py:46` for the swallow.",
        2, "bigquery.py:46"),
    "09-fenced-code-block-cite": (
        # The gate scans physical lines, not markdown structure, so a citation inside a ```
        # fence still blocks. Pinned as current (and desirable) behavior.
        FENCED_CITE,
        2, "bigquery.py:46"),
    "10-stamp-on-line-above": (
        # Stamp is on the line ABOVE the citation. Stamps are per-line, so the citation line
        # is unstamped and blocks. Pinned: the stamp must sit on the citation's own line.
        "bigquery.py:46 [VERIFIED against dev@abc1234]\n"
        "the same swallow also touches flow.py:97",
        2, "flow.py:97"),

    # === TRUE NEGATIVES: pass (exit 0) ================================================
    "11-two-cites-one-stamp-same-line": (
        # Line-scope rule: one stamp anywhere on the line covers every citation on that line.
        "Both bigquery.py:46 and flow.py:97 are fixed [VERIFIED against dev@abc1234].",
        0, "OK"),
    "12-multiple-stamped-lines": (
        "first: bigquery.py:46 [VERIFIED against dev@aaa1111]\n"
        "second: flow.py:97 [VERIFIED against dev@bbb2222]",
        0, "OK"),
    "13-plain-prose-no-refs": (
        "Deployed the logging change to dev. Structured errors now show in Cloud Logging; "
        "will monitor the next few chart turns overnight.",
        0, "OK"),
    "14-lowercase-stamp": (
        # STAMP regex is case-insensitive, so a lowercased stamp still counts.
        "bug at bigquery.py:46 [verified against dev@bae8f58]",
        0, "OK"),
    "15-mixed-verified-and-unverified": (
        # One VERIFIED line, one UNVERIFIED line: no unstamped citations, so exit 0 with the
        # UNVERIFIED warning surfaced for the human approver.
        "confirmed: bigquery.py:46 [VERIFIED against dev@aaa1111]\n"
        "guessing: flow.py:97 [UNVERIFIED — read on main, deploy=dev]",
        0, "UNVERIFIED"),

    # === FALSE-POSITIVE CANDIDATES: legit text that must NOT block (verified) =========
    "16-fp-timestamp": (
        "The deploy finished at 12:46 UTC yesterday; no errors since.",
        0, "OK"),
    "17-fp-ratio": (
        "The billboard creative is locked to a 16:9 aspect ratio per the spec.",
        0, "OK"),
    "18-fp-version-pin": (
        "We pinned python3.11:latest in the build image to stop the drift.",
        0, "OK"),
    "19-fp-time-range": (
        "The outage window was 10:20-10:40 this morning; recovered on its own.",
        0, "OK"),
    "20-fp-filename-no-line": (
        # A filename with NO :line is not a code-location citation — correctly passes.
        "The change lives in bigquery.py and touches the result router.",
        0, "OK"),

    # === FALSE POSITIVE we CANNOT dodge — pinned so a fix is a conscious choice ========
    "21-fp-url-with-jsline": (
        # A CDN/sourcemap URL of the form `.../app.js:80` matches the citation regex and BLOCKS.
        # This is a genuine false positive (the URL is not a deployed-code claim). Pinned as
        # CURRENT behavior; flagged in the report as needing a human decision on a URL guard.
        "Stack trace pointed at https://cdn.example.com/app.js:80 in the prod bundle.",
        2, "app.js:80"),

    # === RED-TEAM EVASIONS: natural phrasings that DODGE the regex (exit 0) ============
    # Each PINS current behavior. `# KNOWN GAP` = a real code-location claim the gate lets
    # through unstamped. Listed prominently in the report's "Surviving evasions" section.
    "22-evasion-line-N-of-file": (  # KNOWN GAP: "line 46 of bigquery.py" has no `.py:NN`
        "The bug is on line 46 of bigquery.py — the except is bare.",
        0, "OK"),
    "23-evasion-file-space-line": (  # KNOWN GAP: "bigquery.py line 46"
        "See bigquery.py line 46 for the swallow.",
        0, "OK"),
    "24-evasion-function-at-comma-line": (  # KNOWN GAP: "src/flow.py, line 94"
        "The function at src/flow.py, line 94 swallows the TypeError.",
        0, "OK"),
    "25-evasion-colon-space": (  # KNOWN GAP: a space after the colon breaks `.py:\d`
        "The swallow is at bigquery.py: 46 in the handler.",
        0, "OK"),
    "26-evasion-github-hash-anchor": (  # KNOWN GAP: GitHub permalink style `.py#L46`
        "Permalink bigquery.py#L46 shows the bare except.",
        0, "OK"),
    "27-evasion-parenthetical-line": (  # KNOWN GAP: "bigquery.py (line 46)"
        "bigquery.py (line 46) drops the error silently.",
        0, "OK"),
    "28-evasion-uncovered-extension": (  # KNOWN GAP: config exts (yaml/yml/json/xml) not in list
        "The value is set at application.yaml:12 and never overridden.",
        0, "OK"),
}


def run_case(script, workdir, name, draft, expected, needle):
    draft_path = os.path.join(workdir, f"{name}.md")
    with open(draft_path, "w", encoding="utf-8") as fh:
        fh.write(draft)
    proc = subprocess.run([sys.executable, script, draft_path],
                          capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    ok = proc.returncode == expected and (needle is None or needle.lower() in output.lower())
    return ok, proc.returncode, output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=DEFAULT_SCRIPT)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.script):
        print(f"gate script not found: {args.script}", file=sys.stderr)
        return 1

    failures = 0
    with tempfile.TemporaryDirectory() as workdir:
        print(f"{'case':40} {'want':>4} {'got':>4}  result")
        print("-" * 64)
        for name, (draft, expected, needle) in FIXTURES.items():
            ok, code, output = run_case(args.script, workdir, name, draft, expected, needle)
            print(f"{name:40} {expected:>4} {code:>4}  {'PASS' if ok else 'FAIL'}")
            if not ok:
                failures += 1
                if needle and needle.lower() not in output.lower():
                    print(f"    (missing expected output: {needle!r})")
            if args.verbose or not ok:
                for line in output.strip().splitlines()[:6]:
                    print(f"    | {line}")

    total = len(FIXTURES)
    print("-" * 64)
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
