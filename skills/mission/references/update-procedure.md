# Updating a mission (what to write, when)

Read `schema.md` for field shapes. This file says which event writes which field. The goal: progress stays visible, and stale or disproven context cannot come back.

## Events and writes

| Event in the session | Write to mission.yaml | Notes |
|---|---|---|
| Gabriel decides something | `decisions` new entry, `state: ratified`, `ratified_by: {who: Gabriel, link}` | The link points at where he said it: a GH comment, a Jira comment, a Slack link, or `{kind: session, url: <session folder on GitHub>, title: "<session> turn <time>"}`. |
| You (the agent) propose a decision | `decisions` entry, `state: proposed` | It stays proposed until a human ratifies it. Never write "do not re-litigate" on it. |
| A decision changes | New entry with `supersedes: DEC-n`. Set the old entry `state: superseded` (or `reversed`). | List the code built on the old decision under its `licenses`. That list is the unwind checklist. |
| A claim is proven false | `disproven` entry with evidence and a grep `signature`. Then run `git grep -n "<signature>"` in project-management and the member repos. | Fix or fence every stale copy you find. Delete the dead text, do not annotate it. Record the sweep in `changes`. |
| A question only Gabriel can answer | `needs_you` entry (ID, question, why, options with consequence, recommendation, `after_answer`, links). | `blocking: false` puts it in the FYI row. |
| Gabriel answers it | Remove the `needs_you` entry. Add the decision or the ask answer. Add a `changes` entry. | The report shows it once in "Latest changes", then only in Journey. |
| Gabriel asks a question or makes a request | `asks` entry (`asker: Gabriel`). Update its `state` when it is answered, done or deferred. | Also for stakeholders (`asker: OT`). |
| Work is parked | `parked` entry with a bucket (`horizon`, `tomorrow`, `blocked_on_person`), owner, since, and `reentry` or `recheck`. | Blocked on a person: name the person and where you asked them. |
| A new ticket, issue, MR, folder or session joins | `members` entry with `kind`, `ref`, `url`, `title`, `role`. | Link, do not nest. A GitHub issue can have only one parent. |
| A member is done or replaced | Change its `role` to `done` or `superseded`. | Never delete members. Superseded members are hidden behind a fold in the report. |
| A file, kit or build to keep | `artifacts` entry with path and SHA. | The next session finds it here instead of searching Downloads. |
| A message to a person is drafted | `messages` entry, `state: draft`. When Gabriel says he sent it, paste his sent text into `sent_text` and set `state: sent`. | |
| A new concept or relation appears | `graph.nodes` and `graph.edges`. | Keep it small: systems, people, key concepts, decisions. |
| Gabriel confirms he knows a term | `terms` entry, `confirmed: true`. | See terminal-replies.md rule 5. |
| The main feature ships, or the destination looks reached | Nothing yet. Run `/mission check --close` (see `closeout-procedure.md`). Record its outcome in `changes` and `journey`. | Move a member to `done` only after its close-out item is done. |
| End of the session (or of a night run) | One `journey` entry: kind, session, start, end, summary, milestones, blockers, confusion, findings, decisions. | `confusion` records moments when Gabriel or the agent lost the thread. This is what makes the journey honest. |
| Anything above | One `changes` entry (`C-n`, `at`, `session`, `summary`, `refs`). | This feeds "Latest changes". |

Timestamps come from `date -u +%Y-%m-%dT%H:%M:%SZ`, never from inference.

## Keep it high level

Each text field holds one or two sentences. Put the detail in a file under `missions/<slug>/evidence/` or in the ticket folder, and link it. The lint warns above 400 characters.

## What never goes in mission.yaml

- Tracker status from Jira or GitHub. `mission_fetch.py` reads it live into `computed.json`.
- Long analysis. Link it.
- Secrets, tokens, or customer data.
