#!/usr/bin/env python3
"""
Sprint estimation-ownership audit (Klever, KTP project).

For every non-subtask ticket in a given sprint, works out who actually SET
the current story-points value (the last person to touch that field in the
changelog), and compares it to the ticket's current assignee. This is not
an estimator — it never proposes a number. It only tells you whether the
number already on the ticket was put there by the person who owns the work.

Reuses the same auth path as ~/.claude/skills/jira/jira_skill.py
(jira_config.json + macOS Keychain, service "claude-jira") without touching
that script — it has a separate --full JQL-search bug
('PropertyHolder' object has no attribute 'customfield_10028') that this
script routes around by fetching compact search results, then per-ticket
detail with expand=changelog.

Usage:
    python3 audit.py --sprint-id 1781
    python3 audit.py --sprint-id 1781 --out /tmp/audit.json

Output: a single JSON file (default /tmp/sprint-estimation-audit.json) —
see the "classification" field per ticket:
    UNESTIMATED         no story points set at all
    ESTIMATED_BY_OTHER   points present, but the owner never set them
    OK                   the assignee's own edit produced the current value
"""
import argparse
import json
import subprocess
import sys
from jira import JIRA

CONFIG_FILE = "/Users/gabrielamyot/.claude-shared-config/skills/jira/jira_config.json"
KEYCHAIN_SERVICE = "claude-jira"
ORG = "klever"
PROJECT = "KTP"

STORY_POINT_FIELD_NAMES = {"Story Points", "Story point estimate"}
STORY_POINT_FIELD_IDS = {"customfield_10028", "customfield_10016"}


def get_token(org):
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", f"jira_{org}", "-w"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR: no keychain token for jira_{org}. Run jira_config_setup.py configure {org} first.",
              file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def connect():
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    org_cfg = config["organizations"][ORG]
    token = get_token(ORG)
    return JIRA(server=org_cfg["jira_url"], basic_auth=(org_cfg["jira_username"], token)), org_cfg["jira_url"]


def current_story_points(fields):
    sp = getattr(fields, "customfield_10028", None)
    if sp is None:
        sp = getattr(fields, "customfield_10016", None)
    return sp


def story_point_history(changelog):
    changes = []
    for history in changelog.histories:
        for item in history.items:
            field = getattr(item, "field", None)
            field_id = getattr(item, "fieldId", None)
            if field in STORY_POINT_FIELD_NAMES or field_id in STORY_POINT_FIELD_IDS:
                changes.append({
                    "author": history.author.displayName if history.author else None,
                    "created": history.created,
                    "from": item.fromString,
                    "to": item.toString,
                })
    changes.sort(key=lambda c: c["created"])
    return changes


def classify(assignee, current_sp, history, reporter):
    if current_sp is None:
        return "UNESTIMATED", None
    if history:
        last_author = history[-1]["author"]
        if last_author == assignee:
            return "OK", None
        return "ESTIMATED_BY_OTHER", last_author
    # Points present, no changelog entry at all -> set inline at creation.
    # Jira does not log field values supplied in the creation payload, only
    # later edits, so the changelog is genuinely empty in this case.
    if reporter == assignee:
        return "OK", None
    return "ESTIMATED_BY_OTHER", reporter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sprint-id", required=True, type=int,
                         help="Jira sprint id (get it from: jira_skill.py --org klever sprints --project KTP --state active,future)")
    parser.add_argument("--out", default="/tmp/sprint-estimation-audit.json")
    args = parser.parse_args()

    jira, base_url = connect()

    jql = f"project = {PROJECT} AND sprint = {args.sprint_id}"
    issues = jira.search_issues(jql, maxResults=200)

    results = []
    for issue in issues:
        detail = jira.issue(issue.key, expand="changelog")
        fields = detail.fields

        issue_type = fields.issuetype.name
        if issue_type == "Sub-task":
            # Subtasks inherit their estimation context from the parent story/task;
            # flagging them individually just adds noise to the report.
            continue

        assignee = fields.assignee.displayName if fields.assignee else None
        reporter = fields.reporter.displayName if fields.reporter else None
        current_sp = current_story_points(fields)
        history = story_point_history(detail.changelog)
        classification, set_by = classify(assignee, current_sp, history, reporter)

        results.append({
            "key": issue.key,
            "url": f"{base_url}/browse/{issue.key}",
            "summary": fields.summary,
            "status": fields.status.name,
            "type": issue_type,
            "assignee": assignee,
            "current_story_points": current_sp,
            "classification": classification,
            "set_by": set_by,  # who actually set the current value, when it wasn't the assignee
        })

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    flagged = [r for r in results if r["classification"] != "OK"]
    print(f"{len(results)} tickets audited (subtasks excluded), {len(flagged)} unestimated-by-owner.")
    print(f"Full data written to {args.out}")


if __name__ == "__main__":
    main()
