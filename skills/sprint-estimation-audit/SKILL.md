---
name: sprint-estimation-audit
description: "Audit a Klever (KTP) sprint for story-point ESTIMATION OWNERSHIP — who actually set the current point value on each ticket, versus who owns (is assigned) the ticket. Flags tickets with no points, and tickets where someone other than the assignee (a teammate, Raj, Gabriel helping out) set the number — those don't count as the owner having estimated. Does NOT propose new estimates (that's the sprint-estimation skill) and never writes to Jira. Triggers on: 'who hasn't estimated their tickets', 'check estimation ownership', 'who's missing points', 'unestimated by owner', 'sprint estimation audit', 'did people point their own tickets', 'who needs to estimate sprint N'."
nav:
  bay: know
  when: "Read-only audit of who set existing story points on sprint tickets, grouped by assignee. Ends with a Slack-paste HTML opened in Chrome. Standard D-1 pre-sprint step, run right after refinement (documentation/process/sprint-planning-protocol.md)."
  when_not: "Proposing NEW point values with code investigation (use sprint-estimation). Sprint board status/crossover (use klever-sprint-mgmt). Posting anything to Jira (this skill never does)."
  org: [klever]
---

# Sprint Estimation Audit

**Purpose:** answer "did the ticket owner actually estimate their own ticket?" — not "how big is this ticket?" A story-points field can be non-empty because Raj filled it in during refinement, or because Gabriel touched it while triaging, or because it was set at creation and the assignee never looked at it again. None of that is the same as the owner having thought about complexity and committed to a number. This skill finds those tickets and hands you a report, nothing more.

**Where this sits in the pipeline:** this is the D-1 pre-sprint check that runs right after refinement, per `documentation/process/sprint-planning-protocol.md`. Refinement gets a number onto every ticket; this audit checks whether the *right person* put it there before sprint start.

If the user wants a *number proposed* for a ticket, that's `/sprint-estimation`, not this. This skill is read-only: it never calls `jira_skill.py update` and never posts a comment.

## Workflow

### 1. Resolve the sprint

```bash
cd ~/.claude/skills/jira && python3 jira_skill.py --org klever sprints --project KTP --state active,future
```

Match the user's phrasing ("Sprint 5", "next sprint", "current sprint") against the `name`/`state` fields and take that sprint's `id`. If ambiguous, ask.

### 2. Run the audit script

```bash
python3 ~/.claude/skills/sprint-estimation-audit/scripts/audit.py --sprint-id <ID> --out /tmp/sprint-estimation-audit.json
```

This does the heavy lifting in one shot: pulls every ticket in the sprint, fetches each with `expand=changelog`, walks the Story Points field history (`customfield_10028`, falls back to `customfield_10016`) to find who made the last change, and classifies each ticket. It reuses the jira skill's own auth (`jira_config.json` + Keychain service `claude-jira`) — no separate login needed, no token ever printed.

**Why a dedicated script and not `jira_skill.py search --full`:** that command's `--full` flag currently throws on this JQL path (`'PropertyHolder' object has no attribute 'customfield_10028'`). The script routes around it by fetching compact search results, then per-issue detail with changelog. Don't try to fix `jira_skill.py` as part of running this skill — that's shared infra other things depend on; if it's still broken, just note it and move on.

**Classification per ticket** (subtasks are excluded automatically — a subtask's estimate is scoped by its parent, so flagging it separately is noise):
- `UNESTIMATED` — no story points at all.
- `ESTIMATED_BY_OTHER` — points are set, but the last person to touch that field (per changelog) isn't the current assignee. If the field was never touched after creation (no changelog entry for it — this happens because Jira doesn't log values supplied in the creation payload), the script falls back to comparing reporter vs. assignee: same person, `OK`; different person, `ESTIMATED_BY_OTHER` with the reporter named as the likely source.
- `OK` — the assignee's own edit produced the current value.

The output JSON (small — one sprint's worth of tickets) has `key`, `url`, `summary`, `status`, `type`, `assignee`, `current_story_points`, `classification`, `set_by`. Read it directly; no need for a follow-up script.

### 3. Build the "needs owner estimation" list

Filter to `classification != "OK"`. Group by `assignee` (unassigned tickets get their own group). For each `ESTIMATED_BY_OTHER` ticket, note who actually set it — that's the whole point of the flag: "Raj estimated this, so it still doesn't count as Alpha having pointed it."

Present this as the primary chat answer, one heading per assignee, tickets as clickable Jira links (`[KTP-XXX](url)`) per this project's link-rendering rule. Keep it scannable — key + short title, not the full description.

### 4. Slack-paste artifact

The user will very likely want to paste this into a standup or sprint-planning channel. Build an HTML file using the exact same minimal template the `klever-3ps` skill uses (check a recent file under `general/3ps/*.html` for the current version if this drifts) — inline `<style>`, system font stack, `p.header` for bold section labels, plain `<ul><li>`, links in `#1264a3`, no emoji/tables/card styling. Slack's paste-from-clipboard only preserves plain formatting like this; anything fancier pastes as a mangled table or gets stripped.

One `<p class="header">{Assignee Name}</p>` + `<ul>` per group, one `<li><a href="...">KTP-XXX</a> — summary</li>` per ticket.

Save it to `general/sprints/{sprint-slug}/estimation-audit-{date}.html` in the project-management repo (create the sprint folder if it doesn't exist yet — check `general/sprints/README.md` for the slug convention already in use).

Open it for the user with:

```bash
open -a "Google Chrome" "<full path to the html file>"
```

Use the plain macOS `open` command, not the claude-in-chrome MCP `navigate` tool — that tool has mishandled a bare `file://` URL before (silently prepending `https://`), where `open` just works.

Tell the user the file is open and ready to select-all/copy into Slack.

### 5. Stop there

No Jira writes, no Slack posts, no comments drafted. If the user then asks to actually estimate the unestimated tickets, hand off to `/sprint-estimation` — don't try to do that work here.

## Notes

- KTP project / board 248 only, hardcoded in `scripts/audit.py`. If this ever needs to run for another org's project, that script needs a `--project`/org parameter — don't hack org detection in ad hoc.
- "Owner" = current assignee. If the user means something else by "owner" for a given sprint, confirm before running.
- A ticket in `Won't Do` status still gets audited (it's still in the sprint); mention it but don't make a fuss about it needing points.
