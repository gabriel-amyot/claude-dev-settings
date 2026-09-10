---
name: wayfinder
description: Plan a huge chunk of work (more than one agent session can hold) as a shared map of decision tickets on GitHub Issues (gabriel-amyot/klever-project-management, never Jira), and resolve them one at a time until the way to the destination is clear.
version: "0.2.0"
disable-model-invocation: true
---

A loose idea has arrived, too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on GitHub Issues, then works its **decision tickets** (questions whose resolution is a decision, not slices of a build to execute) one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting: it shapes every ticket. It might be a spec to hand off and iterate on, a decision to lock before planning starts, or a change made in place like a data-structure migration. The map is domain-agnostic: engineering work, course content, whatever fits the shape.

## Plan, don't do

Wayfinder is **planning** by default: each ticket resolves a decision, and the map is done when the way is clear, with nothing left to decide before someone goes and does the thing. The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off. An effort can override this in its **Notes**, carrying execution into the map itself, but absent that, produce decisions, not deliverables.

## Refer by name

Every map and ticket is an issue, so it has a **name**: its title. In everything the human reads (narration, the map's Decisions-so-far), refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. The id and URL don't vanish; a name wraps its link, but they ride _inside_ the name, never stand in for it.

## The Map

The map is a single GitHub issue on `gabriel-amyot/klever-project-management`, labelled `wayfinder:map`, the canonical artifact. Its tickets are child issues of the map.

The map is an **index**, not a store. It lists the decisions made and points at the tickets that hold their detail; a decision lives in exactly one place, its ticket, so the map never restates it, only gists it and links.

**The tracker is GitHub Issues on `gabriel-amyot/klever-project-management`. This is not configurable and there is no fallback.** Never Jira, never a local-markdown tracker, never the issue tracker of whatever repo you happen to be working in. Wayfinder tickets are internal decisions; Jira is the board colleagues read, and a decision ticket does not belong there. A `jira_skill.py create` is mechanically blocked without an explicit audience decision (see JIRA_AGENT_RULES Rule 7).

Every `gh` command below needs `--repo gabriel-amyot/klever-project-management`, because you will usually be running inside a different repo. Do not let `gh` infer it from `git remote`.

### Wayfinding operations

- **Map**: `gh issue create --repo gabriel-amyot/klever-project-management --label wayfinder:map --title "<destination>" --body-file <file>`. Use `--body-file`, not `--body`, so the markdown survives.
- **Child ticket**: `gh issue create --repo <repo> --parent <map-number> --label wayfinder:<type> --title "<question>" --body-file <file>`. Native as of `gh` 2.100.0. To re-parent later: `gh issue edit <n> --parent <map>` or `gh issue edit <map> --add-sub-issue <n>`.
- **Blocking**: `gh api --method POST repos/gabriel-amyot/klever-project-management/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`. **The trap:** `issue_id` is the blocker's numeric *database* id, from `gh api repos/gabriel-amyot/klever-project-management/issues/<n> --jq .id`. It is NOT the `#number` and NOT the `node_id`. Passing the `#number` silently targets the wrong issue.
- **Frontier query**: `gh issue list --repo <repo> --state open --json number,title,parent,assignees,blockedBy,labels --jq '[.[] | select(.parent.number == <map>) | select((.assignees | length) == 0) | select((.blockedBy.totalCount // 0) == 0) | select((.labels | map(.name) | index("wayfinder:reflection")) == null)]'`. First in map order wins. Open blockers and any assignee both remove a ticket from the frontier, and the reflection ticket is excluded by label so it can never be picked as ordinary route work.
  - **The trap:** `blockedBy` is an **object** `{nodes: [...], totalCount: N}`, not an array. `(.blockedBy | length)` counts its two *keys* and returns `2` for every issue, blocked or not, so the frontier reads as **permanently empty**. Use `.blockedBy.totalCount`. Verify with `gh api repos/<repo>/issues/<n>/dependencies/blocked_by --jq '[.[].number]'`, which is authoritative.
- **Claim**: `gh issue edit <n> --repo <repo> --add-assignee @me`. The session's first write, before any work.
- **Resolve**: `wayfinder_runs.py resolve` (see [Telemetry](#telemetry-how-the-wayfinder-improves-itself)). It posts the answer comment, appends the run trailer, and closes the issue in one command; you then append the gist plus link to the map's Decisions-so-far. The two raw commands it replaces are `gh issue comment <n> --repo <repo> --body-file <answer>` then `gh issue close <n> --repo <repo>` — use them only when the tool cannot run, and know that the run goes untraced.
- **Labels**: create them once on first use — `wayfinder:map`, `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, `wayfinder:task`, `wayfinder:reflection`. `gh label create <name> --repo <repo>` fails loudly if it already exists, which is fine.

### The map body

The whole map at low resolution, loaded once per session. Open tickets are **not** listed: they are open child issues, found by query.

```markdown
## Destination

<what reaching the end of this map looks like: the spec, decision, or change this effort is finding its way to. One or two lines; every session orients to it before choosing a ticket.>

## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Decisions so far

<!-- the index: one line per closed ticket, enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [<closed ticket title>](link): <one-line gist of the answer>

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't ticket yet; graduates as the frontier advances -->

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

### Tickets

Each ticket is a **child issue** of the map; its GitHub issue number is its identity. Its body is the question, sized to one 100K token agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Each ticket carries a `wayfinder:<type>` label, one of `research`, `prototype`, `grilling`, `task` (see [Ticket Types](#ticket-types)).

A session **claims** a ticket by assigning it to the dev driving the map, **first**, before any work, so concurrent sessions skip it. That assignee _is_ the claim: an open, unassigned ticket is unclaimed.

Blocking uses GitHub's **native issue dependencies**: essential because it renders the frontier _visually_ in GitHub's own UI, so the human sees what's takeable without opening the map. There is no body-convention fallback; GitHub supports this natively. A ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unclaimed children, the edge of the known.

The answer isn't part of the body; it's recorded on resolution (see [Work through the map](#work-through-the-map)). Assets created while resolving a ticket are linked from the issue, not pasted in.

## Ticket Types

Every ticket is either **HITL** (human in the loop, worked _with_ a human who speaks for themselves) or **AFK**, driven by the agent alone. A HITL ticket only resolves through that live exchange; the agent never stands in for the human's side of it (a grilling agent that answers its own questions has broken this).

- **Research** (AFK): Reading documentation, third-party APIs, or local resources like knowledge bases to surface a fact a decision waits on. Resolved by a subagent that calls the Skill tool with "research". Use when knowledge outside the current working directory is required.
- **Prototype** (HITL): Raise the fidelity of the discussion by making a cheap, rough, concrete artifact to react to (an outline, a rough take, a stub, or UI/logic code) by calling the Skill tool with "prototype". Links the prototype as an asset. Use when "how should it look" or "how should it behave" is the key question.
- **Grilling** (HITL): Conversation. The default case. Always call the Skill tool twice, for "grilling" and "domain-modeling".
- **Task** (HITL or AFK): Manual work that must happen before a _decision_ can be made: nothing to decide, prototype, or research, but the discussion is blocked until it's done. Signing up for a service so its API can be judged, provisioning access, moving data so its shape can be seen. This is the one type that _does_ rather than decides, and it earns its place by unblocking a decision, not by delivering the destination. The agent drives it alone where it can (AFK); otherwise it hands the human a precise checklist (HITL). Resolved when the work is done; the answer records what was done and any resulting facts (credentials location, new URLs, row counts) later tickets depend on.
- **Reflection** (HITL): One per map, planted at charting time, never on the frontier. It is the retro on the **vehicle**, not a step on the route: how did the wayfinder itself perform, and what changes in its spec. See [Telemetry](#telemetry-how-the-wayfinder-improves-itself).

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the live tickets lies the **fog of war**: the dim view of decisions and investigations you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever's now specifiable into fresh tickets, one at a time, until the way to the destination is clear and no tickets remain.

The map's **Not yet specified** section is where that dim view is written down: the suspected question, the area to revisit later. It's the undiscovered frontier _toward_ the destination: everything here is in scope, just not sharp enough to ticket. Write as loosely or as fully as the view allows; it doubles as a signpost for collaborators reading where the effort is headed.

**Fog or ticket?** The test is whether you can state the question precisely now, _not_ whether you can answer it now.

- **Ticket when** the question is already sharp, even if it's blocked and you can't act on it yet.
- **Not yet specified when** you can't yet phrase it that sharply. Don't pre-slice the fog into ticket-sized pieces: it's coarser than a ticket, and one patch may graduate into several tickets, or none, once the frontier reaches it.

**Not yet specified** excludes what's already decided (Decisions so far), what's already a live ticket, and what's out of scope (the next section).

## Out of scope

Fog only ever gathers _toward_ the destination. The destination fixes the scope, so work beyond it is **out of scope**: it isn't fog, and it doesn't belong in **Not yet specified**. It gets its own **Out of scope** section on the map: work you've consciously ruled out of _this_ effort. Scope, not sharpness, lands it here.

Out-of-scope work never graduates (the frontier stops at the destination), so it returns only if the destination is redrawn, and then as a fresh effort, not a resumption.

Ruling something out of scope is a scoping act, not a step on the route. When a ticket that already exists turns out to sit past the destination (mis-scoped in while charting, or exposed by a resolution), **close it** (a closed ticket is unambiguously off the frontier) and leave one line in the **Out of scope** section: the gist plus why it's out of scope, linking the closed ticket. It stays out of **Decisions so far**, which records the route actually walked; a scope boundary isn't a step on it.

## Telemetry: how the wayfinder improves itself

The spec you are reading is versioned, and every session leaves a trace of how well it served. That trace is what the next version is built from. Tool: `~/.claude-shared-config/skills/wayfinder/tools/wayfinder_runs.py`.

**Be honest about what this is.** It is best-effort by placement, not a gate. Nothing stops a session closing an issue in the GitHub UI and leaving no trace. What the design buys is that the traced path is the *easy* path, and an untraced run is **detected** (`harvest` reports it as a GAP) instead of vanishing.

### The run

One run is one session: one charting session, or one ticket resolution. Each leaves a single collapsed `wayfinder_run` block inside a comment the session already had to post, so the telemetry is the same action as the work:

- **Charting** → `wayfinder_runs.py chart --map <n> --tickets-created <k> --fog-patches <j> [--friction tag:note ...]`. Posts the trailer on the map and plants the reflection ticket.
- **Resolving** → `wayfinder_runs.py resolve --ticket <n> --body-file <answer> --outcome resolved [--tickets-created <k>] [--fog-graduated <j>] [--friction tag:note ...]`. Posts the answer with the trailer, then closes. Re-running after a failed close **resumes** (closes, no duplicate comment); it never needs `--force`.

`--outcome` is one of `resolved`, `out_of_scope`, `partial`, `abandoned`. There is deliberately **no self-assigned score**: a number an agent grades itself on is not evidence.

### Friction is the evidence

`--friction` is what fought **the spec**, not what was hard about the decision. Every entry is `tag:note` over a closed vocabulary, because RECURRING keys on the tag and free prose never recurs:

| Tag | Means |
|---|---|
| `spec-wrong` | an instruction in this file is factually incorrect (the `blockedBy` trap was one) |
| `spec-missing` | no guidance existed for a situation that arose |
| `spec-ambiguous` | guidance existed but was read two ways |
| `tooling` | `gh`, the GitHub API, or the CLI fought back |
| `sizing` | the ticket or the map was the wrong size |
| `process` | the workflow shape (claim, frontier, one-per-session) got in the way |

`--friction` omitted means the spec held. Say so by omitting it, not by inventing an entry.

### Human feedback

Any comment on a wayfinder issue whose first line starts `wayfinder-feedback:` is picked up by `harvest` and carried into the reflection brief. One line, written where the human already is.

### The reflection ticket

`wayfinder:reflection`, HITL, planted by `chart` as a child of the map and excluded from the frontier query by label, so it is the map's terminal act by construction rather than by maintaining a blocking edge per ticket.

Resolve it with `wayfinder_runs.py reflect --map <n>` first, which prints every run, the friction grouped by tag, the untraced GAPs, and the spec versions the map was worked under. It **refuses while route tickets are still open** unless you pass `--interim`. Reflection is **repeatable**: an interim retro does not consume the map's final one, and a map that grows new tickets after a reflection simply earns another.

Run it early when `resolve` prints **RECURRING** (the same friction tag three or more times across all harvested maps). That is the spec actively costing you, and waiting for a 35-ticket map to finish wastes the signal.

The resolution must produce a concrete `SKILL.md` diff **and** a `CHANGELOG.md` entry with a bumped `version:`, or record explicitly that it produces neither.

### Boundaries

- **This telemetry owns `SKILL.md` and `CHANGELOG.md` only.** Session knowledge, cross-skill patterns and CLAUDE.md rules route to `/gab-operationalize` exactly as they already do. One backlog each, no competing truth.
- **GitHub is the source of truth.** `runs/` is a derived cross-map cache. Only `harvest` and `reflect` write it, and both hold one lock across the map file *and* the index, so concurrent sessions cannot publish a mixed generation. `chart` and `resolve` only read it.
- **Posting posture is inherited, not new.** This skill has always posted resolution comments with a bare `gh issue comment` on Gabriel's own planning repo, outside the `/post-comment` pipeline. `wayfinder_runs.py` wraps that identical call and changes nothing about it. Moving wayfinder onto `/post-comment` would be a change to its core loop and is Gabriel's call, not a telemetry decision.

## Invocation

Two modes. Either way, **never resolve more than one ticket per session**, with the exception of research tickets.

### Chart the map

User invokes with a loose idea.

1. **Name the destination.** Call the Skill tool twice, for "grilling" and "domain-modeling", to pin down what this map is finding its way to: the spec, decision, or change. The destination fixes the scope, so it's settled first.
2. **Map the frontier.** Grill again, **breadth-first** this time: fan out across the whole space rather than deep on any one thread, surfacing the open decisions and the first steps takeable now. **If this surfaces no fog** (the way to the destination is already clear, the whole journey small enough for one session), you don't need a map. Stop and ask the user how they'd like to proceed.
3. **Create the map** (label `wayfinder:map`): Destination and Notes filled in, Decisions-so-far empty, the fog sketched into **Not yet specified**.
4. **Create the tickets you can specify now** as child issues of the map, then wire blocking edges in a **second pass** (issues need ids before they can reference each other). Wiring sorts them into the frontier and the blocked; everything you can't yet specify stays in the fog: the **Not yet specified** section.
5. **Fire the research subagents.** For each `research` ticket you just created, spin up a subagent that calls the Skill tool with "research" to resolve it in parallel, capturing its findings on a throwaway `research/<name>` branch with a context pointer from the ticket.
6. **Close the run**: `wayfinder_runs.py chart --map <n> --tickets-created <k> --fog-patches <j> [--friction tag:note ...]`. Posts the charting trailer and plants the reflection ticket. A map with no reflection child is a visibly unfinished chart.
7. Stop: charting is one session's work; it hand-resolves nothing.

### Work through the map

User invokes with a map (URL or number). A ticket is **optional**: without one, you pick the next decision, not the user.

1. Load the **map**: the low-res view, not every ticket body.
2. Choose the ticket. If the user named one, use it. Otherwise take the first frontier ticket in order. **Claim it**: assign it to yourself before any work.
3. Resolve it. **Zoom as needed**: fetch the full body of any related or closed ticket on demand; call the Skill tool for whichever skills the `## Notes` block names. If in doubt, call the Skill tool twice, for "grilling" and "domain-modeling".
4. Record the resolution: write the answer to a file, then `wayfinder_runs.py resolve --ticket <n> --body-file <answer> --outcome <outcome> [--friction tag:note ...]`. That posts the answer as a **resolution comment** with the run trailer and **closes** the issue. Then **append a context pointer** to the map's Decisions-so-far (the tool prints the line to start from).
5. Add newly-surfaced tickets (create-then-wire); graduate any fog the answer has made specifiable, clearing each graduated patch from **Not yet specified** so it lives only as its new ticket. Pass the counts to `resolve` as `--tickets-created` and `--fog-graduated`. If the answer reveals that a ticket (this one or another) sits beyond the destination, **rule it out of scope** rather than resolving it on the route (`--outcome out_of_scope`). If the decision invalidates other parts of the map, update or delete those tickets.
6. If `resolve` printed **RECURRING**, the spec is costing you now: run `wayfinder_runs.py reflect --map <n> --interim` and resolve the reflection ticket rather than carrying the friction into the next ticket.

The user may run unblocked tickets in parallel, so expect other sessions to be editing the same GitHub issues concurrently.
