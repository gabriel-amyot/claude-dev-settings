---
name: mission
description: Track a long-running, cross-session goal (a "mission") with one committed record and render it as a rich HTML report. Use whenever Gabriel says "mission", "start a mission", "open the mission", "update the mission", "mission report", "where are we on X", "big picture", "latest changes", "what is blocked", "what needs me", "what did the night run do", or when work spans several sessions, tickets or GitHub issues (TTD MCP, planning map, Salesforce media plan, harness work) and a new session must not reload stale or disproven context. Also governs how to reply in the terminal while a mission is active (detail dial: "left"/"more", "right"/"less", "refs").
version: "0.1.0"
nav:
  bay: plan
  when: "A goal that crosses sessions needs one source of truth (decisions, disproven claims, blockers, parked tracks, journey) and an on-demand HTML view of it."
  when_not: "Session-to-session task handoff (use session:handoff). A single-ticket build (use dark-factory). Planning decision tickets on a map (use wayfinder; a wayfinder map can be a mission member). A crawl's per-run 'mission brief' is a run brief, not a mission."
---

# Mission

A **mission** is one cross-session outcome with a destination. It ends when the destination is reached. It is bigger than one session and often bigger than one Jira epic. It can bundle Jira tickets, unlinked GitHub issues, harness work, ticket folders and sessions.

The skill fixes two failures that cost Gabriel weeks:
- **Lost thread.** He sees only the last screen of the terminal, so answers, blockers and decisions get buried. The fix is an HTML report on request, rendered from the record.
- **Stale context.** Session 3 writes a new file, session 1's file and the ticket stay stale, and session 4 reloads an idea that was already disproven. The worst case was the first TTD MCP run: five security controls built on an unratified decision, then unwound. The fix is one record per mission. It holds decisions with authority, disproven claims, scope constraints and parked tracks, and every session reads it first and writes it back.

## Where things live

```
project-management/missions/
  INDEX.md                      generated list of all missions
  _meta/skill-usage.jsonl       usage and feedback log (self-improvement)
  <slug>/
    mission.yaml                THE MAIN RECORD. Committed and pushed on every update.
    README.md                   generated: GitHub view with mermaid journey and graph
    report.html                 generated: the rich report (overwritten, never a new dated file)
    computed.json               generated: live Jira/GitHub status with fetched_at
    evidence/                   optional supporting files
```

- **GitHub root issue** in `gabriel-amyot/klever-project-management` with the label `kind:mission`. Its body holds the destination and a link to `mission.yaml`. It can be a sub-issue of a component issue (for example #594 for the TTD trading MCP). Other issues are **linked** as members, not nested: a GitHub issue can have only one parent.
- Members are links in `mission.yaml`: Jira URLs, GitHub URLs, ticket folders, session folders. GitHub's web view cannot follow a symlink, so a symlink is never the only record.
- Tracker status is never written by hand. `mission_fetch.py` reads it live. Local status claims rot (12 of 13 lagged Jira in the 2026-11-09 audit).

Schema: `references/schema.md`. Which event writes which field: `references/update-procedure.md`.

## Running the scripts

One dispatcher runs every script with its dependencies:

```bash
~/.claude/skills/mission/scripts/mission <new|lint|fetch|render|sync|log> [args]
```

Below, `mission <cmd>` means that full path. Never `cd` in Bash (a zsh override hangs). The scripts use absolute paths.

## Commands

Log every command first: `mission log use --command <cmd> --mission <slug> --session <session-slug>`.

### `/mission start <destination>`: create a mission

1. Search for an existing mission first: read `missions/INDEX.md` and grep the aliases in each `mission.yaml`. If one matches, offer to join it instead.
2. Agree with Gabriel on four things: a slug, a title, a destination of 1 or 2 lines ("done looks like…"), and a parent component issue if there is one. Propose them, and do not interrogate.
3. `mission new --slug <slug> --title "<title>" --destination "<…>" --why "<…>" [--parent <N>] --session <session>`. This creates the folder, `mission.yaml`, and the `kind:mission` root issue, then links the parent.
4. Fill in `mission.yaml`: members (the tickets, issues and folders already known), aliases, next milestone, scope constraints, and a first graph. Use the Edit tool.
5. `mission sync <slug> -m "create mission" --session <session> --status-comment`.
6. Tell Gabriel the slug, the root issue link and the record link.

### `/mission` or `/mission <slug>`: resume

Use this at the start of any session that touches the mission.
1. Read `missions/<slug>/mission.yaml`. Its `decisions` (ratified), `disproven` and `scope_constraints` win over any other file, ticket or library page. If another file contradicts them, the other file is stale. Say so, and do not use it.
2. `mission fetch <slug>` for live tracker status.
3. Give a terminal digest at the current dial level (see "Terminal replies"):
   - the destination;
   - the next milestone;
   - "needs you", with IDs and options;
   - mismatches;
   - the last journey entry.

### `/mission update`: write back

Run it whenever mission truth changes, and always before the session ends.
1. Apply the writes from `references/update-procedure.md` for what happened: decisions, disproven claims, needs-you items, asks, parked tracks, members, artifacts, messages, graph, terms, and one `journey` entry per session.
2. Add a `changes` entry for each meaningful change.
3. `mission lint <slug>`. Fix every error.
4. `mission sync <slug> -m "<what changed>" --session <session> --status-comment`. This commits and pushes, and posts a short status comment on the root issue.

An update is done only when the push succeeded. A local commit is not an update.

### `/mission report [<slug>]`: the HTML view

1. `mission fetch <slug>`.
2. `mission render <slug> --open`. This writes `report.html` and opens it in the browser.
3. In the terminal, print the `file://` link and three lines: the verdict, the needs-you count, and the number of changes since the last report.

The report has five views:
- **Mission**: verdict, tiles, needs you, deliverables, asks, messages and artifacts.
- **Journey**: trajectory with gaps, sessions, decisions, disproven claims, parked tracks and trackers.
- **Context graph**.
- **Latest changes**: a sliding window since the last report.
- **Sources**.

A report never creates a new analysis file. If the record is thin, update it first. Mid-conversation "big picture" requests use the same command: update, then report.

### `/mission close <slug>`

This needs Gabriel. Every member must be done, superseded, or moved to a named successor. Copy the parked `horizon` items into the next mission or a new issue. Set `status: done`, then sync. Close the root issue with a comment that links the record. A phase ending is not a mission ending.

### `/mission feedback "<text>"` and `/mission retro`

Log Gabriel's reactions verbatim. Retro turns repeated complaints into proposed skill changes. See `references/self-improvement.md`.

## Terminal replies while a mission is active

Read `references/terminal-replies.md` once per session. In short:
- Assume Gabriel has not read anything above your current reply, and that he knows only what he confirmed.
- Answer first.
- Never write "see above".
- Never use a bare ID or reference.
- Define new terms once.
- Persist every question before you ask it.
- Follow the detail dial: default 3, "left" means more detail, "right" means less, "refs" means links only.

## Rules that protect the record

- **Authority.** A decision is ratified only with `ratified_by` that links to where a human said it. An agent never ratifies its own proposal. "Do not re-litigate" is valid only on a ratified decision (the lint enforces it).
- **Supersede, do not annotate.** A changed decision gets a new entry with `supersedes`. A disproven claim gets an entry with a grep signature, and you sweep the stale copies. Dead text in other files is deleted or fenced, not annotated.
- **One record.** Never write a second "current status" or "start here" file for a mission. Other files link to `mission.yaml`.
- **Commit explicit paths only.** `mission_sync.py` already does this. The PM repo is single-trunk `main`: never branch, never rewrite history.

## Horizon (not in v1)

- Session meshing: sessions on one mission talking to each other directly. Research in [#670](https://github.com/gabriel-amyot/klever-project-management/issues/670).
- A hook that captures Gabriel's asks at turn time. A session-close gate that requires a mission update.
- Integration with the Klever context graph (`context-graph-sync`).
- Cross-component missions with more than one parent.

## Evals

- `evals/run_layer_a.py` (`uv run --quiet --with pyyaml python3 ~/.claude/skills/mission/evals/run_layer_a.py`): deterministic checks on the lint, render and fetch, using fixtures. Run it after any change to this skill. It is registered in `~/.claude-shared-config/evals/manifest.yaml`.
- `evals/evals.json`: behavioral cases for skill-creator.
