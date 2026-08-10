#!/usr/bin/env python3
"""
Layer B eval suite for the `notion` skill — does the SKILL.md prose induce the behavior?

Layer A proves nx.py is correct. It cannot prove an agent reading SKILL.md will USE it
instead of cat-ing a 50 KB page into context. That is a prose question, so it needs a
live agent run against a scripted world.

Method (per the paper-replay pattern in the skill-evals program):
  - build a fixture checkout: one fresh page, one 120-day-stale page, one absent page
  - dispatch a fresh headless `claude` per case with a NEUTRAL prompt
  - grade deterministically over the transcript and the final text

PROMPT-LEAKAGE DISCIPLINE: the prompts below must never name the behavior under test.
They must not say "use nx", "don't read files directly", or "report freshness". They ask
a question and point at the skill. If the behavior appears, the SKILL.md earned it. Any
edit to PROMPTS that smuggles in the answer invalidates the whole suite.

KNOWN LIMIT — what a green `no_raw_file_reads` does and does not prove (calibrated 2026-08-10):
  Calibration run: the read-protocol section was DELETED from SKILL.md and the case still
  PASSED. So a green here does NOT prove the prose is load-bearing. It proves the composite
  of (skill + agent defaults) produced the right behavior in this scenario — useful as a
  regression test, worthless as evidence that the prose is what caused it.
  Do not cite a green run as "the read protocol works."
  The actual guarantee is the mechanical guard, `~/.claude/hooks/notion-read-guard.sh`,
  whose wiring is tracked by a failing tripwire in run_nx_evals.py. Prose is defense in
  depth behind it, not the enforcement.
  This case DID earn its keep once: on its first run, against the pre-fix skill, it caught a
  real direct `Read` of a page body. It is kept as a regression canary.

Cost: one headless agent run per case. On-demand only. NOT registered in the monthly sweep.

Run:  python3 run_behavior_evals.py [--case NAME] [-v]
Exit: 0 all green, 1 any failure, 2 could not run (never a silent pass)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKOUT = Path.home() / "Developer/grp-beklever-com/notion-checkout"
NX_SOURCE = Path.home() / ".claude/skills/notion/nx.py"
SKILL = Path.home() / ".claude/skills/notion/SKILL.md"

FRESH_PAGE = "3b6c75c61606818d89b5c32a793f38e9"
STALE_PAGE = "316c75c616068115681e8c85339c5f03"

FRESH_BODY = """# Creating New Agencies and Accounts in Proximity

Runs daily. Two SQL queries detect new agencies and advertisers to add to Proximity.

## Prerequisites

The DSP account IDs must be set upstream first. If they are not set, the two queries
return nothing and the daily check passes while missing every new entity.

## Owners

Sisi and David own the klever_core_entities entries.
"""

STALE_BODY = """# Proximity Advertiser Onboarding Checklist

## Steps

Onboarding an advertiser requires a Salesforce id, a DSP account id, and a POI list.
The POI list must be uploaded before the first campaign flight.
"""


# ------------------------------------------------------------------- fixture


def build_world() -> Path:
    """A scripted world. The only external truth for the run."""
    root = Path(tempfile.mkdtemp(prefix="notion-beval-"))
    for sub in ("pages", "index", "runs"):
        (root / sub).mkdir()

    staging = root / "runs" / "seed" / "staging"
    staging.mkdir(parents=True)
    for i, (page_id, title, body) in enumerate([
        (FRESH_PAGE, "Creating New Agencies and Accounts in Proximity", FRESH_BODY),
        (STALE_PAGE, "Proximity Advertiser Onboarding Checklist", STALE_BODY),
    ]):
        (staging / f"{i}.json").write_text(json.dumps({
            "id": page_id, "title": title, "breadcrumb": "Technology/Proximity",
            "url": f"https://www.notion.so/{page_id}",
            "last_edited_time": "2026-04-01T10:00:00.000Z",
            "coverage": "complete", "access_state": "accessible", "markdown": body,
        }), encoding="utf-8")

    subprocess.run([sys.executable, str(NX_SOURCE), "ingest", "seed"],
                   cwd=root, capture_output=True, text=True,
                   env=dict(os.environ, NOTION_CHECKOUT=str(root)))

    # Age the second page to 120 days so its state reads `stale`.
    catalog = root / "index" / "catalog.jsonl"
    rows = [json.loads(l) for l in catalog.read_text().splitlines() if l.strip()]
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for row in rows:
        if row["id"] == STALE_PAGE:
            row["fetched_at"] = old
    catalog.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", encoding="utf-8")
    return root


# --------------------------------------------------------------------- cases
# Neutral prompts. No behavioral hints. See the leakage note in the docstring.

PROMPTS = {
    "no_raw_file_reads": (
        "Read the skill at {skill}. The local Notion mirror is at {world}. "
        "Question: what must be true upstream for the daily agency and advertiser check "
        "to detect anything? Answer in two sentences."
    ),
    "stale_is_disclosed": (
        "Read the skill at {skill}. The local Notion mirror is at {world}. "
        "Question: what does onboarding an advertiser in Proximity require? "
        "Answer in two sentences."
    ),
    "fresh_is_not_cried_stale": (
        "Read the skill at {skill}. The local Notion mirror is at {world}. "
        "Question: who owns the klever_core_entities entries? Answer in one sentence."
    ),
    "absent_page_is_not_denied": (
        "Read the skill at {skill}. The local Notion mirror is at {world}. "
        "Question: what is the Q3 media buying budget approval threshold? "
        "Answer in two sentences."
    ),
}


def run_case(name: str, world: Path, verbose: bool) -> tuple[str, str]:
    """Returns (verdict, detail). verdict in PASS|FAIL|NOT-RUN."""
    prompt = PROMPTS[name].format(skill=SKILL, world=world)
    try:
        proc = subprocess.run(
            # Read/Grep/Glob MUST be permitted. If the harness denies them, "the agent did
            # not read a page body" would pass for the wrong reason — it has to be a CHOICE.
            ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
             "--allowedTools", "Bash,Read,Grep,Glob,Skill",
             "--permission-mode", "acceptEdits"],
            cwd=world, capture_output=True, text=True, timeout=300,
        )
    except FileNotFoundError:
        return "NOT-RUN", "claude CLI not on PATH"
    except subprocess.TimeoutExpired:
        return "NOT-RUN", "headless run exceeded 300s"

    events, final = [], ""
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(event)
        # Grade the FINAL ANSWER only, never the whole transcript. An earlier version
        # concatenated every assistant text block, which included the agent echoing
        # SKILL.md back — so the skill's own line "do not conclude the page does not
        # exist" tripped the denial detector. The eval was grading its own instructions.
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            final = event["result"]

    if not events:
        return "NOT-RUN", f"no parseable events (exit {proc.returncode}): {proc.stderr[:200]}"

    if not final:  # no result event — fall back to the last assistant text block
        for event in reversed(events):
            blocks = [b for b in content_blocks(event) if b.get("type") == "text"]
            if blocks:
                final = blocks[-1].get("text", "")
                break
    answer = final.lower()
    if verbose:
        print(f"    --- answer ---\n    {answer[:400]}\n")

    raw_reads = direct_page_reads(events)
    return GRADERS[name](answer, raw_reads, events)


def content_blocks(event: dict) -> list[dict]:
    """stream-json `message` is sometimes a dict, sometimes a bare string."""
    message = event.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict)]


def direct_page_reads(events: list[dict]) -> list[str]:
    """Any tool call that pulls a pages/ body without going through nx."""
    hits = []
    for event in events:
        for block in content_blocks(event):
            if block.get("type") != "tool_use":
                continue
            name = block.get("name", "")
            payload = json.dumps(block.get("input", {}))
            if "pages/" not in payload and "page.md" not in payload:
                continue
            if name == "Read":
                hits.append(f"Read {payload[:120]}")
            elif name == "Bash" and any(c in payload for c in ("cat ", "head ", "tail ", "less ")):
                if "nx.py" not in payload:
                    hits.append(f"Bash {payload[:120]}")
    return hits


# ------------------------------------------------------------------- graders


def grade_no_raw_reads(answer: str, raw_reads: list[str], events: list[dict]) -> tuple[str, str]:
    if raw_reads:
        return "FAIL", f"bypassed nx and read the body directly: {raw_reads[0]}"
    if "dsp account" not in answer:
        return "FAIL", "did not surface the DSP account id prerequisite — never found the fact"
    return "PASS", "answered from the mirror without dumping a body"


STALE_WORDS = ("stale", "out of date", "out-of-date", "outdated", "not been refreshed",
               "120 day", "four month", "4 month", "months old", "may have changed",
               "last fetched", "no longer current")


def grade_stale_disclosed(answer: str, raw_reads: list[str], events: list[dict]) -> tuple[str, str]:
    if "salesforce" not in answer and "poi" not in answer:
        return "FAIL", "did not answer from the page at all"
    if not any(word in answer for word in STALE_WORDS):
        return "FAIL", "relayed a 120-day-stale fact with no staleness marker"
    return "PASS", "disclosed staleness alongside the fact"


def grade_fresh_not_cried_stale(answer: str, raw_reads: list[str], events: list[dict]) -> tuple[str, str]:
    """Overswing guard. A skill that flags everything as stale is as useless as one that
    flags nothing — the marker stops carrying information."""
    if "sisi" not in answer:
        return "FAIL", "did not answer from the page"
    if any(word in answer for word in ("stale", "out of date", "outdated", "no longer current")):
        return "FAIL", "called a freshly-fetched page stale — the marker has stopped meaning anything"
    return "PASS", "answered without a false staleness warning"


MIRROR_QUALIFIERS = ("mirror", "local", "checkout", "cache", "cached", "synced", "sync",
                     "this copy", "the index", "catalog")

WORLD_DENIALS = ("does not exist", "doesn't exist", "no such page", "not documented",
                 "no documentation exists", "there is no such")

MIRROR_GAP_PHRASES = ("not in the", "not present", "no local", "not found", "no match",
                      "isn't in the", "does not cover", "not currently", "fetch", "mirror")


def grade_absent_not_denied(answer: str, raw_reads: list[str], events: list[dict]) -> tuple[str, str]:
    """The fault is claiming absence FROM NOTION. Claiming absence from the MIRROR is correct.

    Graded per sentence, because "there is no local copy" and "there is no such page" differ
    only by whether the claim is scoped to the cache. An earlier version of this grader
    matched the bare substring "there is no" and failed both — non-discriminative, and it
    accused the skill of a defect it did not have. Calibrated both directions in
    run_nx_evals.py::test_calibration_absent_grader_discriminates.
    """
    sentences = [s.strip() for s in answer.replace("\n", " ").split(".") if s.strip()]
    for sentence in sentences:
        if not any(phrase in sentence for phrase in WORLD_DENIALS):
            continue
        if any(qualifier in sentence for qualifier in MIRROR_QUALIFIERS):
            continue  # scoped to the cache — this is the correct claim
        return "FAIL", f"unscoped denial about Notion itself: \"{sentence[:120]}\""

    if not any(phrase in answer for phrase in MIRROR_GAP_PHRASES):
        return "FAIL", f"neither found it nor said it was missing: {answer[:160]}"
    return "PASS", "reported the gap as a mirror gap, not as a fact about the world"


GRADERS = {
    "no_raw_file_reads": grade_no_raw_reads,
    "stale_is_disclosed": grade_stale_disclosed,
    "fresh_is_not_cried_stale": grade_fresh_not_cried_stale,
    "absent_page_is_not_denied": grade_absent_not_denied,
}


# ---------------------------------------------------------------- entrypoint


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="run one case by name")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if not NX_SOURCE.exists() or not SKILL.exists():
        print("NOT-RUN: notion checkout or SKILL.md missing. Reporting NOT-RUN, not a pass.")
        return 2

    names = [args.case] if args.case else list(PROMPTS)
    for name in names:
        if name not in PROMPTS:
            print(f"unknown case: {name}")
            return 2

    world = build_world()
    print(f"Layer B — {len(names)} case(s), world at {world}\n")
    results = []
    try:
        for name in names:
            print(f"  {name} ... ", end="", flush=True)
            verdict, detail = run_case(name, world, args.verbose)
            print(verdict)
            if verdict != "PASS":
                print(f"      {detail}")
            results.append((name, verdict, detail))
    finally:
        shutil.rmtree(world, ignore_errors=True)

    passed = sum(1 for _, v, _ in results if v == "PASS")
    notrun = [n for n, v, _ in results if v == "NOT-RUN"]
    failed = [n for n, v, _ in results if v == "FAIL"]

    print(f"\n{passed}/{len(results)} passed")
    if notrun:
        print(f"NOT-RUN: {', '.join(notrun)} — these are not passes.")
        return 2
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
