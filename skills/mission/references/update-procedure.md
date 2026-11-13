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
| Gabriel asks a question or makes a request | `asks` entry (`asker: Gabriel`). Update its `state` when it is answered, done or deferred. | Also for stakeholders (`asker: TR`). |
| Work is parked | `parked` entry with a bucket (`horizon`, `tomorrow`, `blocked_on_person`), owner, since, and `reentry` or `recheck`. | Blocked on a person: name the person and where you asked them. |
| A new ticket, issue, MR, folder or session joins | `members` entry with `kind`, `ref`, `url`, `title`, `role`. | Link, do not nest. A GitHub issue can have only one parent. |
| A member is done or replaced | Change its `role` to `done` or `superseded`. | Never delete members. Superseded members are hidden behind a fold in the report. |
| A file, kit or build to keep | `artifacts` entry with path and SHA. | The next session finds it here instead of searching Downloads. |
| A message to a person is drafted | `messages` entry, `state: draft`. When Gabriel says he sent it, paste his sent text into `sent_text` and set `state: sent`. | |
| A new concept or relation appears | `graph.nodes` and `graph.edges`. | Keep it small: systems, people, key concepts, decisions. |
| Gabriel confirms he knows a term | `terms` entry, `confirmed: true`. | See terminal-replies.md rule 5. |
| The main feature ships, or the destination looks reached | Nothing yet. Run `/mission check --close` (see `closeout-procedure.md`). Record its outcome in `changes` and `journey`. | Move a member to `done` only after its close-out item is done. |
| End of the session (or of a night run) | One `journey` entry: kind, session, start, end, summary, milestones, blockers, confusion, findings, decisions. | `confusion` records moments when Gabriel or the agent lost the thread. This is what makes the journey honest. |
| Anything above that opens or closes a line of work | The matching thread write (see "Threads" below). | One store feeds the Mission and Closure tabs. |
| Anything above | One `changes` entry (`C-n`, `at`, `session`, `summary`, `refs`). | This feeds "Latest changes". |

Timestamps come from `date -u +%Y-%m-%dT%H:%M:%SZ`, never from inference.

## Threads: capture each one when it opens

A **thread** is one line of work or thought: an intent, a rabbit hole, an open door, a handoff, a nugget, an ask or a finding. Write it the moment it opens. At close, `/mission check --close` re-checks the list that already exists. It does not rebuild it. A thread found only at close is a capture miss.

Write threads only with the helper. It takes an flock on `mission.yaml` (several sessions write the same record) and replaces only the `threads:` block:

```bash
mission thread add <slug> --kind <kind> --title "<max 70 chars>" --session <session> --event <event> [fields]
mission thread set <slug> T-n [fields] [--state <state>] [--note "..."] --session <session>
mission thread resolve <slug> T-n --how evidence|superseded|ticket|answered|dropped --link "URL|title" [--by NAME] --note "..."
mission thread list <slug> [--state open,needs_you] [--session <session>]
```

Fields: `--ref "URL|title"` (repeatable), `--lives-in`, `--finding`, `--reason`, `--control`, `--live`, `--home "URL|title" --owner NAME [--accepted-by NAME --accepted-link URL]`, `--question`, `--option "label|consequence"` (repeatable), `--recommend "label"`, `--verb`, `--command "label|cmd"`, `--after`, `--needs-you N-n`, `--ask A-n`. `--json '{...}'` merges any other field. Never hand-edit the `threads:` block.

| Event | Who writes it | Thread write |
|---|---|---|
| `/mission start`, or Gabriel states a cross-session goal | `mission new` | `big_intent` thread T-1 (`--event mission_start`). Every other thread defaults to it as parent. |
| `session:init` extracts the session intent, and the session joins a mission | the agent, at init | `thread add --kind intent --event session_init --session <s>` |
| A tangent or debug fork starts ("wait, let me check…") | the agent, at that turn | `thread add --kind rabbit_hole --parent <current intent> --event rabbit_hole_opened` |
| The rabbit hole converges | the agent | `thread resolve T-n --how evidence --link <what settled it>` |
| "We should also…", "later", a question raised and not pursued | the agent (a skill duty; see Horizon for the hook proposal) | `thread add --kind open_door --event open_door_noticed`, state open |
| `session:handoff` writes a prompt | the agent, right after the handoff | `thread add --kind handoff --event handoff_written --home "<prompt file URL>|handoff prompt" --child "<intent 1>" --child "<intent 2>"`: one child intent per intent in the prompt |
| `session:pickup` starts a handoff | the picking-up session | `thread set T-n --note "picked up by <session>" --session <session>` (a history entry) |
| `session:report-back` closes a handoff | the reporting session | `thread resolve` each child intent with its evidence, then the handoff thread (`--how evidence --link <report>`) |
| `/operationalize`, or a nugget goes to the bibliothèque inbox | the capture skill | `thread add --kind nugget --event nugget_captured`. Resolve it with the shelf link when it is shelved. |
| Gabriel asks a question (an `asks` entry) | `/mission update` | `thread add --kind ask --ask A-n --event ask_recorded`. Resolve it (`--how answered`) when the ask is answered. |
| A `needs_you` entry is added | `/mission update` | the thread goes to `--state needs_you` with `--question`, `--option`, `--recommend`, `--after`, `--needs-you N-n`. Every needs-you thread carries a recommendation (the lint warns when it is missing). |
| Work is parked (a `parked` entry) | `/mission update` | `thread set T-n --state parked --home "<link>" --owner <name>`. Accepted only with `--accepted-by <name> --accepted-link <where they said yes>`. |
| A ticket is created to hold the work | any skill | `thread set T-n --state parked --home "<ticket URL>|<key>" --owner <name> --accepted-by <name> --accepted-link <ticket URL>` |
| `session:check` (every checkpoint) | the agent, after its intent tree | Reconcile with `thread list <slug> --session <s>`: an OPEN node keeps or updates its thread, an ABANDONED node is `resolve --how dropped --by <name> --note <reason>`, a DONE node is `resolve --how evidence --link <evidence>`, a TICKET node is parked with an accepted home. A node with no thread gets one now (`--event session_check`). |
| `mission fetch` | the script | Compares each thread's snapshot with the live tracker state and sets `drift`. A drifted thread is re-read, then `thread set T-n --clear-drift --note "<what you re-judged>"`. `resolve` refuses a drifted thread without `--rejudged`. |
| `mission check --close` | the close-out | `mission closeout render <slug>` merges `closeout.yaml` into the threads: it buckets each thread (`closeout.bucket`), adds the items live capture missed (`origin.event: closeout_sweep`, each one a capture miss) and writes `do_now` on the Needs-you rows. |
| `closeout approve` / `record` | the scripts | the action states and read-backs stay in `closeout.yaml`. Resolve the thread with the read-back as evidence when its last action is done. |
| `/mission close` | Gabriel | The gate requires every thread resolved, dropped, or parked with an accepted home, and no drift. Resolve T-1 (the big intent) with the link that proves the destination. |

A record made before threads existed: run `mission threads import <slug> --session <s>` once. It seeds threads from `needs_you`, `asks`, `parked`, journey findings and blockers, current Jira, GitHub and MR members, and the close-out items. It merges records that point at the same work (`--match N-1=CO-1` forces a pair, `--no-match N-4` blocks one) and marks each thread `origin.event: imported`. Imported is not live-captured: the Closure tab counts it apart.

## Keep it high level

Each text field holds one or two sentences. Put the detail in a file under `missions/<slug>/evidence/` or in the ticket folder, and link it. The lint warns above 400 characters.

## What never goes in mission.yaml

- Tracker status from Jira or GitHub. `mission_fetch.py` reads it live into `computed.json`.
- Long analysis. Link it.
- Secrets, tokens, or customer data.
