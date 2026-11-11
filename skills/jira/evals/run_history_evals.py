#!/usr/bin/env python3
"""Layer A fixtures for jira_history.py and the jira_skill.py read-path fixes.

Deterministic. No network, no `jira` package, no model calls.

Covers:
  - description history: newest-first order, several edits, --back N, gaps in
    the chain, empty history (proposal 2026-07-29 jira-description-recover)
  - ancestor-aware epic walk for Sub-tasks (proposal 2026-08-26)
  - retype UI fallback across the Sub-task boundary (proposal 2026-08-26)
  - static: no `issue.fields.customfield_NNNNN` attribute read (the
    'PropertyHolder' object has no attribute 'customfield_10028' crash)
  - static: restore-description stays a dry run until --confirm, and backs up first

Usage: python3 run_history_evals.py [-v]
Exits non-zero on any failure.
"""
import argparse
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import jira_history as jh  # noqa: E402


def hist(created, author, frm, to, field="description"):
    return {"created": created, "author": {"displayName": author},
            "items": [{"field": field, "fromString": frm, "toString": to}]}


THREE_EDITS = [  # deliberately out of order, plus a non-description item
    hist("2026-07-20T20:31", "Gabriel", "v1", "v2"),
    hist("2026-05-28T16:46", "Amal", "v0", "v1"),
    {"created": "2026-07-01T00:00", "author": {}, "items": [{"field": "status", "fromString": "To Do", "toString": "Done"}]},
    hist("2026-07-20T20:39", "Gabriel", "v2", "v3"),
]


def c_newest_first():
    edits = jh.field_edits(THREE_EDITS)
    return [e["to"] for e in edits] == ["v3", "v2", "v1"], [e["to"] for e in edits]


def c_back_one_is_before_last_edit():
    return jh.version_before(jh.field_edits(THREE_EDITS), 1) == "v2", "back=1"


def c_back_three_is_original():
    return jh.version_before(jh.field_edits(THREE_EDITS), 3) == "v0", "back=3"


def c_back_too_far_refused():
    try:
        jh.version_before(jh.field_edits(THREE_EDITS), 4)
    except ValueError:
        return True, "raised"
    return False, "no error"


def c_gap_flagged():
    gapped = [hist("2026-02-01", "A", "X-not-v1", "v2"), hist("2026-01-01", "A", "v0", "v1")]
    report = jh.history_report("K-1", gapped, back=2)
    ok = not report["chain_complete"] and report.get("warning")
    return bool(ok), report.get("chain_gaps_after_edit")


def c_gap_older_than_target_no_warning():
    gapped = [hist("2026-03-01", "A", "v2", "v3"), hist("2026-02-01", "A", "X", "v2"),
              hist("2026-01-01", "A", "v0", "v1")]
    report = jh.history_report("K-1", gapped, back=1)
    return report["recovered_text"] == "v2" and not report.get("warning"), report.get("warning")


def c_empty_history_explained():
    report = jh.history_report("K-1", [], current="orig")
    return report["edit_count"] == 0 and "note" in report, report.get("note")


def c_current_match_reported():
    report = jh.history_report("K-1", THREE_EDITS, current="v3")
    return report["newest_matches_current"] is True, report.get("newest_matches_current")


def c_epic_walk_subtask():
    tree = {"K-3": {"key": "K-3", "type": "Sub-task", "parent": "K-2", "epic_link": None},
            "K-2": {"key": "K-2", "type": "Story", "parent": "K-1", "epic_link": None},
            "K-1": {"key": "K-1", "type": "Epic", "parent": None, "epic_link": None}}
    walk = jh.resolve_epic(tree.get, "K-3")
    return walk["epic"] == "K-1" and len(walk["path"]) == 3, walk


def c_epic_walk_company_epic_link():
    tree = {"K-2": {"key": "K-2", "type": "Story", "parent": None, "epic_link": "K-9"},
            "K-9": {"key": "K-9", "type": "Epic"}}
    return jh.resolve_epic(tree.get, "K-2")["epic"] == "K-9", "epic link"


def c_epic_walk_no_epic_and_cycle():
    none = jh.resolve_epic({"K-2": {"key": "K-2", "type": "Story"}}.get, "K-2")
    cyc = jh.resolve_epic({"A": {"key": "A", "type": "Story", "parent": "B"},
                           "B": {"key": "B", "type": "Story", "parent": "A"}}.get, "A")
    return none["epic"] is None and cyc["reason"] == "cycle in parent chain", (none, cyc)


def c_retype_boundary_and_steps():
    ok = (jh.is_subtask_boundary("Sub-task", "Story") and jh.is_subtask_boundary("Story", "Sub-task")
          and not jh.is_subtask_boundary("Epic", "Story"))
    steps = jh.retype_ui_steps("K-3", "Sub-task", "Story", "https://x.atlassian.net")
    return ok and "Convert to issue" in " ".join(steps) and steps[0].endswith("/browse/K-3"), steps


SOURCE = (SKILL_DIR / "jira_skill.py").read_text(encoding="utf-8")


def c_no_raw_customfield_attribute_reads():
    hits = re.findall(r"issue\.fields\.customfield_\d+", SOURCE)
    return not hits, hits[:5]


def c_restore_is_dry_run_until_confirm():
    m = re.search(r"def restore_description\(.*?\n(?=def )", SOURCE, re.S)
    if not m:
        return False, "restore_description missing"
    body = m.group(0)
    dry = body.find("if not confirm:")
    backup = body.find("f.write(current)")
    update = body.find("issue.update(")
    ok = 0 <= dry < backup < update and "_check_ownership" in body
    return ok, f"dry={dry} backup={backup} update={update}"


def c_restore_writes_verbatim():
    m = re.search(r"def restore_description\(.*?\n(?=def )", SOURCE, re.S)
    body = m.group(0) if m else ""
    return "markdown_to_jira_wiki" not in body, "wiki text must not pass through markdown conversion"


def c_history_command_dispatched():
    return '"history", "restore-description"' in SOURCE, "dispatch"


CASES = [
    ("01-history-newest-first-ignores-other-fields", c_newest_first),
    ("02-back-1-is-text-before-last-edit", c_back_one_is_before_last_edit),
    ("03-back-3-walks-to-original", c_back_three_is_original),
    ("04-back-beyond-history-refused", c_back_too_far_refused),
    ("05-chain-gap-flagged-with-warning", c_gap_flagged),
    ("06-gap-older-than-target-no-warning", c_gap_older_than_target_no_warning),
    ("07-empty-history-explained", c_empty_history_explained),
    ("08-newest-edit-matches-current", c_current_match_reported),
    ("09-epic-walk-subtask-story-epic", c_epic_walk_subtask),
    ("10-epic-walk-company-epic-link", c_epic_walk_company_epic_link),
    ("11-epic-walk-no-epic-and-cycle", c_epic_walk_no_epic_and_cycle),
    ("12-retype-subtask-boundary-ui-steps", c_retype_boundary_and_steps),
    ("13-static-no-raw-customfield-reads", c_no_raw_customfield_attribute_reads),
    ("14-static-restore-dry-run-backup-then-write", c_restore_is_dry_run_until_confirm),
    ("15-static-restore-writes-verbatim", c_restore_writes_verbatim),
    ("16-static-history-commands-dispatched", c_history_command_dispatched),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", action="store_true")
    args = parser.parse_args()
    failed = 0
    for name, fn in CASES:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"exception: {e}"
        failed += 0 if ok else 1
        print(f"{name:<50} {'PASS' if ok else 'FAIL'}" + (f"  {detail}" if args.v or not ok else ""))
    print("-" * 56)
    print(f"{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
