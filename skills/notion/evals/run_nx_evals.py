#!/usr/bin/env python3
"""
Layer A eval suite for the `notion` skill's nx CLI.

Deterministic, judge-free, seconds to run, safe for the unattended monthly sweep.
Every case builds a throwaway checkout in a tmp dir, runs the REAL nx.py against it,
and asserts on exit codes and stdout.

Case selection is driven by what actually goes wrong in this harness:

  context blowout      a 50 KB page landing whole in a context window
  silent staleness     a stale fact relayed with no staleness marker
  drift blindness      a changed page read as unchanged  <-- CALIBRATION, see below
  false completeness   a partial fetch presenting as a whole page
  corrupt promote      a broken sync half-writing the catalog
  out-of-band edit     someone hand-edits pages/, hashes silently diverge

CALIBRATION GATE (per the skill-evals program): `test_calibration_*` cases reconstruct
the OLD behavior this tool replaces and assert it FAILS. Specifically, the retired
notion-wiki MANIFEST.yaml detected change by `size_bytes`. A size-based implementation
passes every other test in this file and still loses data. calibration_size_blind_change
is the case that catches it. If you ever "optimize" change detection back to length
comparison, that case goes red.

Run:  python3 run_nx_evals.py [-v]
Exit: 0 all green, 1 any failure
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

NX_SOURCE = Path.home() / ".claude/skills/notion/nx.py"

PAGE_A = "3b6c75c6-1606-818d-89b5-c32a793f38e9"
PAGE_B = "316c75c6-1606-8115-681e-8c85339c5f03"

BODY_A = """# Creating New Agencies and Accounts in Proximity

Runs daily. Two SQL queries detect new agencies and advertisers.

## Daily check

Run both queries every morning.

### Query notes

Nested detail that belongs to Daily check.

## Prerequisites

DSP account IDs must be set upstream or the queries return nothing.

## Owners

Sisi and David own the klever_core_entities entries.
"""

RESULTS: list[tuple[str, bool, str]] = []
VERBOSE = "-v" in sys.argv


# ------------------------------------------------------------------ harness


class Checkout:
    """A throwaway notion-checkout wrapping the real nx.py."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="nx-eval-"))
        (self.root / "pages").mkdir()
        (self.root / "index").mkdir()
        (self.root / "runs").mkdir()

    def nx(self, *args: str) -> subprocess.CompletedProcess:
        """Invoke the real nx.py against this throwaway root via NOTION_CHECKOUT."""
        env = dict(os.environ, NOTION_CHECKOUT=str(self.root))
        return subprocess.run(
            [sys.executable, str(NX_SOURCE), *args],
            capture_output=True, text=True, cwd=self.root, env=env,
        )

    def stage(self, run_id: str, records: list[dict]) -> None:
        staging = self.root / "runs" / run_id / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        for i, record in enumerate(records):
            (staging / f"{i:04d}.json").write_text(json.dumps(record), encoding="utf-8")

    def catalog(self) -> list[dict]:
        path = self.root / "index" / "catalog.jsonl"
        if not path.exists():
            return []
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def write_catalog(self, rows: list[dict]) -> None:
        path = self.root / "index" / "catalog.jsonl"
        path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", encoding="utf-8")

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def record(page_id: str, markdown: str, **overrides) -> dict:
    base = {
        "id": page_id,
        "title": "Creating New Agencies and Accounts in Proximity",
        "url": f"https://www.notion.so/{page_id.replace('-', '')}",
        "breadcrumb": "Technology/Proximity",
        "last_edited_time": "2026-08-09T18:00:00.000Z",
        "coverage": "complete",
        "access_state": "accessible",
        "markdown": markdown,
    }
    base.update(overrides)
    return base


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))
    if VERBOSE or not condition:
        mark = "PASS" if condition else "FAIL"
        print(f"  [{mark}] {name}" + (f"  — {detail}" if detail and not condition else ""))


def case(fn):
    """Run a case with its own checkout, never leak tmp dirs."""
    def wrapper():
        checkout = Checkout()
        try:
            fn(checkout)
        except Exception as exc:  # a crashing case is a failing case, never a silent skip
            check(f"{fn.__name__}:no-exception", False, f"{type(exc).__name__}: {exc}")
        finally:
            checkout.cleanup()
    wrapper.__name__ = fn.__name__
    return wrapper


# ------------------------------------------------- context-blowout guarding


@case
def test_get_heading_returns_only_that_section(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    out = co.nx("get", PAGE_A.replace("-", ""), "--heading", "Prerequisites").stdout

    check("heading-slice:includes target", "DSP account IDs must be set upstream" in out)
    check("heading-slice:excludes later section", "Sisi and David" not in out,
          "leaked the Owners section")
    check("heading-slice:excludes earlier section", "Run both queries every morning" not in out,
          "leaked the Daily check section")


@case
def test_get_heading_keeps_nested_subsections(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    out = co.nx("get", PAGE_A.replace("-", ""), "--heading", "Daily check").stdout

    check("heading-slice:keeps deeper child", "Nested detail that belongs" in out,
          "H3 under the requested H2 was dropped")
    check("heading-slice:stops at same level", "DSP account IDs" not in out,
          "ran past the next H2")


@case
def test_get_truncates_oversized_body(co: Checkout) -> None:
    huge = "# Big\n\n" + ("filler paragraph. " * 4000)
    co.stage("r1", [record(PAGE_A, huge)])
    co.nx("ingest", "r1")
    result = co.nx("get", PAGE_A.replace("-", ""), "--max-bytes", "500")

    check("truncate:output bounded", len(result.stdout) < 2000,
          f"emitted {len(result.stdout)} chars for a 500-byte cap")
    check("truncate:says it truncated", "TRUNCATED" in result.stdout,
          "silently cut the body with no marker")


@case
def test_missing_heading_lists_alternatives(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    result = co.nx("get", PAGE_A.replace("-", ""), "--heading", "Nonexistent")

    check("missing-heading:nonzero exit", result.returncode != 0)
    check("missing-heading:offers real headings", "Prerequisites" in result.stdout,
          "dead end with no way forward")
    check("missing-heading:no body dump", "Sisi and David" not in result.stdout,
          "fell back to dumping the whole page")


# ------------------------------------------------------- staleness honesty


@case
def test_freshness_states_at_boundaries(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    rows = co.catalog()

    import datetime as dt
    def stamp(days: float) -> str:
        moment = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")

    for days, expected in [(1, "fresh"), (14, "aging"), (90, "stale")]:
        rows[0]["fetched_at"] = stamp(days)
        co.write_catalog(rows)
        out = co.nx("card", PAGE_A.replace("-", "")).stdout
        check(f"freshness:{days}d reads {expected}", f"freshness: {expected}" in out,
              f"got: {[l for l in out.splitlines() if 'freshness' in l]}")


@case
def test_every_read_rung_carries_freshness(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    page = PAGE_A.replace("-", "")

    check("stamp:search", "freshness=" in co.nx("search", "agencies").stdout)
    check("stamp:card", "freshness:" in co.nx("card", page).stdout)
    check("stamp:get", "freshness=" in co.nx("get", page).stdout,
          "a body read with no staleness marker is how a stale fact escapes")


@case
def test_live_drift_is_flagged(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    page = PAGE_A.replace("-", "")

    probe = co.root / "probe.json"
    probe.write_text(json.dumps({"results": [
        {"id": page, "last_edited_time": "2026-09-01T00:00:00.000Z"}
    ]}), encoding="utf-8")
    out = co.nx("apply-freshness", str(probe)).stdout

    check("drift:reported", "1 drifted" in out, out.strip())
    check("drift:persisted", co.catalog()[0].get("content_stale") is True,
          "drift was printed but not recorded, so the next read looks clean")


@case
def test_freshness_confirm_clears_stale_flag(co: Checkout) -> None:
    """Overswing guard: a confirmed-current page must NOT stay flagged."""
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    page = PAGE_A.replace("-", "")
    probe = co.root / "probe.json"

    probe.write_text(json.dumps({"results": [{"id": page, "last_edited_time": "2026-09-01T00:00:00.000Z"}]}))
    co.nx("apply-freshness", str(probe))
    probe.write_text(json.dumps({"results": [{"id": page, "last_edited_time": "2026-08-09T18:00:00.000Z"}]}))
    out = co.nx("apply-freshness", str(probe)).stdout

    check("confirm:reported current", "1 still current" in out, out.strip())
    check("confirm:flag cleared", co.catalog()[0].get("content_stale") is None,
          "a page confirmed current still reads as stale — cries wolf until ignored")


@case
def test_access_loss_is_distinct_from_staleness(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    page = PAGE_A.replace("-", "")
    probe = co.root / "probe.json"
    probe.write_text(json.dumps({"results": [{"id": page, "access_state": "restricted"}]}))

    out = co.nx("apply-freshness", str(probe)).stdout
    check("access:reported", "1 access lost" in out, out.strip())
    check("access:persisted", co.catalog()[0].get("access_state") == "restricted")
    check("access:surfaced by doctor", "access_state=restricted" in co.nx("doctor").stdout,
          "lost access is invisible, so a revoked page still reads as authoritative")


@case
def test_plan_refresh_volatile_is_targeted(co: Checkout) -> None:
    co.stage("r1", [
        record(PAGE_A, BODY_A, volatile=True),
        record(PAGE_B, "# Other\n\nStable reference page.\n", title="IBI Template"),
    ])
    co.nx("ingest", "r1")
    payload = json.loads(co.nx("plan-refresh", "--volatile").stdout)

    check("volatile:only volatile targeted", payload["count"] == 1,
          f"targeted {payload['count']} pages, should be 1")
    check("volatile:right page", payload["targets"][0]["id"] == PAGE_A.replace("-", ""))


# ------------------------------------------------------- promote integrity


@case
def test_duplicate_ids_block_promotion(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A), record(PAGE_A, "# Different\n")])
    result = co.nx("ingest", "r1")

    check("dupe:refuses", result.returncode == 2, f"exit {result.returncode}")
    check("dupe:says why", "duplicate id" in result.stdout.lower())
    check("dupe:nothing promoted", co.catalog() == [],
          "half-promoted a broken run")


@case
def test_malformed_id_blocks_promotion(co: Checkout) -> None:
    co.stage("r1", [record("not-a-uuid", BODY_A)])
    result = co.nx("ingest", "r1")

    check("malformed:refuses", result.returncode == 2, f"exit {result.returncode}")
    check("malformed:nothing promoted", co.catalog() == [])


@case
def test_id_forms_are_interchangeable(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    url = f"https://www.notion.so/beklever/Some-Title-{PAGE_A.replace('-', '')}"

    for label, form in [("undashed", PAGE_A.replace("-", "")), ("dashed", PAGE_A), ("url", url)]:
        out = co.nx("card", form).stdout
        check(f"id-form:{label} resolves", "Creating New Agencies" in out,
              "a citation written in another id form fails to resolve")


@case
def test_partial_coverage_survives_and_surfaces(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A, coverage="partial")])
    co.nx("ingest", "r1")

    check("partial:persisted", co.catalog()[0]["coverage"] == "partial",
          "an incomplete fetch was promoted as complete")
    check("partial:on the card", "coverage: partial" in co.nx("card", PAGE_A.replace("-", "")).stdout)
    check("partial:doctor flags", "coverage=partial" in co.nx("doctor").stdout,
          "a partial page passes integrity check silently")


@case
def test_doctor_catches_out_of_band_edit(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    body = co.root / "pages" / PAGE_A.replace("-", "") / "page.md"
    body.write_text(BODY_A + "\nHand-edited line that never came from Notion.\n", encoding="utf-8")

    result = co.nx("doctor")
    check("tamper:nonzero exit", result.returncode != 0)
    check("tamper:hash mismatch named", "hash mismatch" in result.stdout,
          "local edits masquerade as Notion source")


@case
def test_doctor_catches_orphan_page(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    orphan = co.root / "pages" / "ffffffffffffffffffffffffffffffff"
    orphan.mkdir()
    (orphan / "page.md").write_text("# Orphan\n", encoding="utf-8")

    result = co.nx("doctor")
    check("orphan:detected", "orphan" in result.stdout.lower(), result.stdout.strip())


@case
def test_reingest_unchanged_is_not_a_change(co: Checkout) -> None:
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    co.stage("r2", [record(PAGE_A, BODY_A)])
    out = co.nx("ingest", "r2").stdout

    check("idempotent:no false change", "=1 unchanged" in out, out.strip())
    check("idempotent:no duplicate row", len(co.catalog()) == 1)


# ------------------------------------------- epistemic boundary on no-match


@case
def test_no_match_does_not_license_a_denial(co: Checkout) -> None:
    """Layer B found an agent turning "no local match" into "no such page".

    Absence from the mirror is a fact about the mirror. Absence from Notion is a claim
    about the world, and this command cannot support it. The output must say so, because
    the agent reading it will compress whatever it is given.
    """
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    result = co.nx("search", "quarterly budget approval threshold")

    check("no-match:nonzero exit", result.returncode != 0)
    check("no-match:states it is a mirror gap", "NOT IN THIS MIRROR" in result.stdout)
    check("no-match:forbids the denial", "does not mean" in result.stdout.lower(),
          "output invites 'the page does not exist'")
    check("no-match:names the next step", "fetch mode" in result.stdout,
          "dead end with no recovery path")


# ----------------------------------------------------- read-guard hook gate


HOOK = Path.home() / ".claude/hooks/notion-read-guard.sh"


def run_hook(tool: str, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(HOOK)], input=json.dumps({"tool_name": tool, "tool_input": payload}),
        capture_output=True, text=True,
    )


@case
def test_hook_blocks_page_body_read(co: Checkout) -> None:
    """Prose did not stop the reflex (Layer B, no_raw_file_reads). This is the backstop."""
    if not HOOK.exists():
        check("hook:exists", False, f"missing {HOOK}")
        return
    (co.root / "pages" / "abc").mkdir(parents=True, exist_ok=True)
    (co.root / "index").mkdir(exist_ok=True)
    (co.root / "index" / "catalog.jsonl").write_text("{}\n", encoding="utf-8")

    result = run_hook("Read", {"file_path": str(co.root / "pages" / "abc" / "page.md")})
    check("hook:blocks page body", result.returncode == 2, f"exit {result.returncode}")
    check("hook:explains the ladder", "nx" in result.stderr and "rung" in result.stderr,
          "blocked without telling the agent what to do instead")


@case
def test_hook_allows_legitimate_reads(co: Checkout) -> None:
    """A guard that over-blocks gets disabled, so the allow cases matter as much."""
    if not HOOK.exists():
        check("hook:exists", False, f"missing {HOOK}")
        return
    (co.root / "index").mkdir(exist_ok=True)
    (co.root / "index" / "catalog.jsonl").write_text("{}\n", encoding="utf-8")

    allowed = [
        ("index read", "Read", {"file_path": str(co.root / "index" / "catalog.jsonl")}),
        ("unrelated pages dir", "Read", {"file_path": "/tmp/nextjs-site/pages/index.tsx"}),
        ("nx via Bash", "Bash", {"command": "python3 nx.py get abc --heading X"}),
        ("skill doc", "Read", {"file_path": str(Path.home() / ".claude/skills/notion/SKILL.md")}),
    ]
    for label, tool, payload in allowed:
        result = run_hook(tool, payload)
        check(f"hook:allows {label}", result.returncode == 0,
              f"over-blocked with exit {result.returncode}")


@case
def test_hook_is_wired_TRIPWIRE(co: Checkout) -> None:
    """WIRING TRIPWIRE — fails by design until a human wires the hook.

    Per the skill-evals program: when an eval finds a guard that is built but not
    registered in settings.json, do NOT wire it unilaterally. Encode the wiring as a
    failing assertion so the wire-or-retire decision surfaces on every sweep instead of
    being silently forgotten.

    To clear this: add notion-read-guard.sh as a PreToolUse hook on Read|Grep|Glob in
    settings.json. To retire it: delete the hook and this case together.
    """
    wired = False
    for path in (Path.home() / ".claude/settings.json",
                 Path.home() / ".claude/settings.local.json"):
        if path.exists() and "notion-read-guard" in path.read_text(encoding="utf-8"):
            wired = True
            break
    check("TRIPWIRE:read-guard wired in settings.json", wired,
          "hook exists but is NOT wired — prose alone does not stop direct page reads "
          "(proven by Layer B). Wire it, or delete the hook and this case.")


# ------------------------------------------------------------ CALIBRATION
# These reconstruct the OLD behavior and must FAIL it. A grader that only ever
# sees the good implementation is a rubber stamp.


@case
def test_calibration_size_blind_change(co: Checkout) -> None:
    """THE calibration case.

    The retired notion-wiki MANIFEST.yaml detected change by `size_bytes`. Here are two
    bodies of IDENTICAL byte length and different content — exactly what that scheme
    cannot see. A size-based implementation reports 'unchanged' and the edit is lost
    forever. nx hashes content, so it must report a change.
    """
    original = "# Page\n\nThe daily check runs at 09:00 and covers agencies.\n"
    edited = "# Page\n\nThe daily check runs at 17:00 and covers agencies.\n"
    assert len(original.encode()) == len(edited.encode()), "fixture must be length-identical"

    co.stage("r1", [record(PAGE_A, original)])
    co.nx("ingest", "r1")
    first_hash = co.catalog()[0]["sha256"]

    co.stage("r2", [record(PAGE_A, edited)])
    out = co.nx("ingest", "r2").stdout

    check("CALIBRATION:length-identical edit detected", "~1 changed" in out,
          f"size-blind change detection regression — reported: {out.strip()}")
    check("CALIBRATION:hash moved", co.catalog()[0]["sha256"] != first_hash,
          "same hash for different content")
    check("CALIBRATION:body actually replaced",
          "17:00" in (co.root / "pages" / PAGE_A.replace("-", "") / "page.md").read_text(),
          "catalog updated but body left stale on disk")


@case
def test_calibration_absent_grader_discriminates(co: Checkout) -> None:
    """Grader calibration for the Layer B absent-page case, run without any agent.

    The first version of that grader matched the bare substring "there is no" and so
    failed a CORRECT answer ("there is no local copy in the mirror") identically to a
    real denial. A grader that fails everything is as useless as one that passes
    everything, and this one briefly convinced me the skill had a defect it did not have.

    Both directions are asserted here so a future loosening cannot silently regress it.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "beval", Path(__file__).parent / "run_behavior_evals.py")
    beval = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(beval)

    correct = ("the mirror has no local copy of that page, so there is no cached answer. "
               "i can fetch it from notion using the skill's fetch mode.")
    denial = ("there is no q3 media buying budget approval threshold. "
              "no such page exists and it is not documented.")
    partial = "the threshold is 50000 dollars."

    verdict, _ = beval.grade_absent_not_denied(correct, [], [])
    check("grader-calib:passes a correct mirror-scoped answer", verdict == "PASS",
          f"false positive — got {verdict}")

    verdict, detail = beval.grade_absent_not_denied(denial, [], [])
    check("grader-calib:fails a real denial", verdict == "FAIL",
          f"false negative — a denial slipped through as {verdict}")

    verdict, _ = beval.grade_absent_not_denied(partial, [], [])
    check("grader-calib:fails a fabricated answer", verdict == "FAIL",
          "invented a number with no mirror hedge and passed")


@case
def test_calibration_stale_page_cannot_read_as_fresh(co: Checkout) -> None:
    """Old behavior: an undated local copy read as authoritative.

    A page with no fetch timestamp must read `unknown`, never `fresh`. Defaulting an
    unknown age to fresh is how a four-month-old mirror presents itself as current.
    """
    co.stage("r1", [record(PAGE_A, BODY_A)])
    co.nx("ingest", "r1")
    rows = co.catalog()
    rows[0]["fetched_at"] = None
    co.write_catalog(rows)

    out = co.nx("card", PAGE_A.replace("-", "")).stdout
    check("CALIBRATION:undated is not fresh", "freshness: fresh" not in out,
          "an undated page claimed freshness")
    check("CALIBRATION:undated reads unknown", "freshness: unknown" in out, out.strip())


# ---------------------------------------------------------------- entrypoint


def main() -> int:
    if not NX_SOURCE.exists():
        print(f"FATAL: nx.py not found at {NX_SOURCE}")
        print("The notion checkout is missing. This suite cannot run — reporting NOT-RUN, not a pass.")
        return 1

    cases = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    print(f"nx eval suite — {len(cases)} cases\n")
    for fn in cases:
        if VERBOSE:
            print(f"{fn.__name__}:")
        fn()

    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} assertions passed")
    if failed:
        print(f"\n{len(failed)} FAILED:")
        for name, detail in failed:
            print(f"  - {name}" + (f"\n      {detail}" if detail else ""))
        return 1
    print("all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
