---
name: wayfinder-report-back
description: Report a finding back to a wayfinder map on GitHub Issues from a session that was NOT walking the map. Use this whenever work outside a wayfinder route session turns out to touch a map: an MR or code review that cleared fog, a dark-factory or manual run that finished a wayfinder implementation ticket, a debugging session that answered a question the map was waiting on, a discovery that makes a "Not yet specified" patch specifiable, or a finding that contradicts something the map records as settled. Trigger it even when the session started as something else entirely and the map connection only became obvious at the end. Also trigger on "report back to the map", "the map should know this", "close this wayfinder ticket", "I cleared fog", "this belongs on map #N".
version: "0.1.0"
---

Wayfinder plans a large effort as a map issue with child decision tickets, and its route sessions resolve those tickets one at a time. But not every session that learns something about a map is a route session. A code review notices that a map's settled risk assumed mitigations that do not exist. A dark-factory run finishes an implementation ticket a map's Notes hand to another vehicle. A debugging session answers, incidentally, the exact question a ticket was waiting on.

Such a session was never locked out of GitHub. It could post a bare `gh issue comment`, which leaves no trailer for `harvest`, or use wayfinder's `wayfinder-feedback:` convention, which is harvested but carried to the **reflection brief** — the retro on the vehicle, not the route. Neither addresses the finding to the session that has to act on it.

This skill is the typed inbound path: a report aimed at the route, traced like any other run, carrying provenance for who produced it.

**Be honest about what is new here.** Closing a ticket you worked was always possible with `wayfinder_runs.py resolve`, which accepts any ticket carrying a `wayfinder:` label. Reporting improves the record rather than unlocking the act, and the sections below say where.

## Deposit or dispose

The distinction that governs everything here is whether **this session owned a ticket**.

| | Working report | Incidental report |
|---|---|---|
| The session | took a ticket off the map and did it | owned nothing; found something while doing other work |
| Example | dark-factory runs an implementation ticket | an MR review notices the map's risk note is stale |
| Target | the ticket | the map |
| Closes the ticket | yes | no, there is nothing it claimed |
| Outcome | `resolved` (or `partial`) | `reported` |

**A working report closes.** The session that did the work is the one that knows whether it is done, so closing belongs to it, not to a later wayfinder session that would only be guessing.

`resolve --force` closes it too, and did before this skill existed. Two reasons to prefer `report` anyway, both about the record rather than the act: it stamps `mode: report` with a `--source`, where `resolve` would stamp `mode: resolve` and attribute the run to a route session that never happened; and it leaves `--force` alone, which on `resolve` also suppresses the guard against posting a second, duplicate trailer. If you are a route session resolving your own claimed ticket, use `resolve` — this skill is not for you.

**An incidental report never closes and never decides.** It deposits; a later wayfinder session disposes. A reviewer who noticed something is not thereby entitled to rule it out of scope, graduate it into a ticket, or edit the map body. Naming what you found, precisely, is the whole contribution. Proposing is welcome; deciding is not yours.

If you are unsure which you are, ask whether you would have been able to name the ticket number before the work started. If yes, working. If the connection only became visible afterwards, incidental.

## What you are reporting

Read the ticket or map first. What the map already holds is context to build on, not ground to re-cover.

**A working report satisfies the ticket's `## Report back` block.** That block names the facts the map is owed, because later tickets depend on them. Where the shape was knowable at charting time, it is a list: client ids, a URL, where a secret lives, a row count. Answer each item explicitly, including the ones you could not get, and say why. A silently dropped item reads to the next session as a fact that was never needed.

Where the block is open-ended, or absent on an older ticket, report what the map does not yet hold: what you learned, what it changes, what is now takeable that was not.

**An incidental report leads with the finding and what it changes.** Then, in order of usefulness to whoever walks the map next:

- **Which `Not yet specified` patch it touches**, by name, if any. Do not edit the map body. Naming the patch is enough for a wayfinder session to graduate it.
- **Ticket candidates**, as proposals with a reason. Say what type each looks like in wayfinder's taxonomy (research, prototype, grilling, task) so the next session can act without re-deriving it. Do not create them.
- **Anything that contradicts a recorded decision.** This is the highest-value thing an outside session can carry, and the easiest to soften into uselessness. A map records decisions as settled precisely so nobody re-opens them, which means a genuine contradiction has to be stated plainly or it will be read as noise and skipped. Say what the map records, what you observed, and why they cannot both be true.

Keep it to what a reader needs. A report is not a session log, and the story of how you found something is rarely the part that matters.

## Posting

`wayfinder_runs.py report` posts the comment with a run trailer, so `harvest` counts the run instead of reporting the ticket as untraced.

```bash
W=~/.claude-shared-config/skills/wayfinder/tools/wayfinder_runs.py

# Working: owned #51, finished it, close it.
python3 $W report --ticket 51 --body-file report.md \
  --source "https://gitlab.example/group/repo/-/merge_requests/27" --close

# Incidental: owned nothing, deposit on map #38, close nothing.
python3 $W report --map 38 --body-file report.md \
  --source "KTP-1066 MR review" --fog-cleared 1
```

`--source` is required in both shapes and is the reason an outside run is trustworthy. A trailer found months later has to say what produced it: an MR url, a ticket key, a named session. "An agent said so" is not provenance.

Pass `--fog-cleared` when the finding makes a fog patch specifiable, and `--tickets-created` only if you actually created tickets, which an incidental report does not. `--dry-run` prints the exact comment and touches nothing; use it when you are unsure the body reads well.

Report friction the same way a route session does, with `--friction tag:note`, when this skill or wayfinder itself cost you something. The reflection ticket improves the vehicle from that evidence, and an outside session sees failure modes a route session never will.

## What this skill will not do

It does not resolve decisions, edit the map body, create tickets, or move anything between **Not yet specified**, **Horizon**, and **Out of scope**. Those are wayfinder's acts, taken by a session that loaded the whole map and oriented to the destination. A reporting session has neither.

If what you are holding is a decision rather than a finding, you are in the wrong place: hand it to a wayfinder session.

## Related

- `wayfinder` — the outbound loop: charting a map, walking its frontier, resolving its tickets. Read its SKILL.md when you need the map's structure, the ticket taxonomy, or the fog/horizon/out-of-scope boundaries.
