---
name: wayfinder
description: Plan a huge chunk of work (more than one agent session can hold) as a shared map of decision tickets on GitHub Issues (gabriel-amyot/klever-project-management, never Jira), and resolve them one at a time until the way to the destination is clear.
version: "0.3.0"
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
- **Frontier query**: `gh issue list --repo <repo> --state open --json number,title,parent,assignees,blockedBy,labels --jq '[.[] | select(.parent.number == <map>) | select((.assignees | length) == 0) | select(([.blockedBy.nodes[] | select(.state == "OPEN")] | length) == 0) | select((.labels | map(.name) | index("wayfinder:reflection")) == null)]'`. First in map order wins. Open blockers and any assignee both remove a ticket from the frontier, and the reflection ticket is excluded by label so it can never be picked as ordinary route work.
  - **The trap:** `blockedBy` is an **object** `{nodes: [...], totalCount: N}`, not an array. `(.blockedBy | length)` counts its two *keys* and returns `2` for every issue, blocked or not, so the frontier reads as **permanently empty**. Use `.blockedBy.nodes` filtered to `state == "OPEN"`. Verify with `gh api repos/<repo>/issues/<n>/dependencies/blocked_by --jq '[.[].number]'`, which is authoritative.
  - **The second trap (0.2.3):** `totalCount` counts **every** dependency edge, including ones whose blocker is already **CLOSED**. Filter on it and a ticket that was *ever* blocked never returns to the frontier, which contradicts the definition one paragraph above. Measured on a live map: the query reported a 2-ticket frontier where the real frontier was 6, hiding three takeable tickets including one due that day. Count only OPEN nodes.
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

## Horizon

<!-- see "Horizon": sharp enough to state, deliberately deferred past this destination; seeds the next map, never graduates here -->

- <the deferred work, stated sharply>: <why it waits until after this destination>

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

### Tickets

Each ticket is a **child issue** of the map; its GitHub issue number is its identity. Its body is the question, sized to one 100K token agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>

## Report back

<what the map is owed when this is done>
```

**The `## Report back` block is the ticket's half of a contract.** A ticket is often worked by a session that is not walking the map (see [Report back](#report-back)), and the moment the ticket is written is the only moment the map knows what it will be waiting for. Fill it two ways, depending on how much of the shape you can see:

- **Shape known**: list the facts later tickets depend on, by name. "The client ids, and where their secrets live." "The row count and the table it landed in." A named fact gets answered; a vague request for "findings" gets a paragraph that satisfies nobody.
- **Shape unknown**: say so, and ask the open question instead. "Tell the map what you learned about X that it does not already hold." This is the honest state for most grilling tickets, where the interesting part is what the conversation surfaces, not what you predicted it would.

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

**Not yet specified** excludes what's already decided (Decisions so far), what's already a live ticket, what's deferred to the **Horizon**, and what's out of scope.

## Horizon

Fog and out-of-scope are not the only two ways a thing can be missing from the route. There is a third: work you **will** do, deliberately **not now**. Moving this MCP off laptop-installed bundles and onto a hosted server is the shape of it. Nobody rejected that. Nobody is doing it before this destination is reached. It is the next stage, not a discard, and the map needs somewhere to say so.

**Why the distinction earns its own section.** Without it, deferred work has only two homes and both are wrong. Left in the fog, it re-surfaces as a ticket candidate every session, because the fog is the list of things that graduate. Filed as out of scope, the next agent reads an obvious improvement as rejected and re-opens the argument. Either way a later grilling burns a session re-deciding what was already decided. The Horizon exists so the deferral **holds** across sessions and readers.

The three sections split on two different axes, which is why they cannot collapse into two:

| Section | In scope for this destination? | Sharp enough to state? | Does it come back? |
|---|---|---|---|
| **Not yet specified** (fog) | yes | not yet | graduates into a ticket on **this** map |
| **Horizon** | no, it sits past the destination | yes | seeds a **future** map |
| **Out of scope** | no, ruled out | irrelevant | never |

Each boundary is one question. Against the fog, ask: *could I write the ticket today?* If no, it is fog. If yes, and you are still not writing it, ask the second question. Against out of scope, ask: *rejected, or queued?* Rejected is out of scope. Queued is Horizon.

**A horizon item never graduates inside this map.** That is the point of the section, not a limitation of it. The frontier stops at the destination, and a horizon item sits past it, so resolving a ticket can clear fog but can never promote a horizon line onto the frontier. If a resolution makes a horizon item urgent, the honest reading is that the **destination is wrong**. Redrawing the destination is its own decision, taken openly on the map, never a quiet promotion.

**When the map closes, the Horizon is the seed of the next map.** Do not delete it and do not fold it into Decisions so far, which records only the route actually walked. Carry each line into the next charting session, where it is the loose idea that session grills into a destination. A map that closes with a populated Horizon has produced two things: a cleared route, and the starting material for the map that follows.

**A live ticket can turn out to be horizon work**, the same way one can turn out to be out of scope. Close it, because a closed ticket is unambiguously off the frontier, and move one line into **Horizon**: the gist, why it waits, and a link to the closed ticket. Record the run with `--outcome horizon`, not `out_of_scope`, so the telemetry keeps the two apart.

## Out of scope

Fog only ever gathers _toward_ the destination. The destination fixes the scope, so work beyond it isn't fog and doesn't belong in **Not yet specified**. It gets its own **Out of scope** section on the map: work you've consciously **ruled out**. Scope, not sharpness, lands it here.

**Out of scope is a rejection, and the Horizon is a queue.** Both sit past the destination, so the section alone doesn't tell them apart. The reader needs to know which, because one is finished thinking and the other is pending work. Rule something out of scope only when you would argue against doing it. If you would do it in a later effort, it is Horizon.

Out-of-scope work never graduates (the frontier stops at the destination), so it returns only if the destination is redrawn, and then as a fresh effort, not a resumption.

Ruling something out of scope is a scoping act, not a step on the route. When a ticket that already exists turns out to sit past the destination (mis-scoped in while charting, or exposed by a resolution), **close it** (a closed ticket is unambiguously off the frontier) and leave one line in the **Out of scope** section: the gist plus why it's out of scope, linking the closed ticket. It stays out of **Decisions so far**, which records the route actually walked; a scope boundary isn't a step on it.

## Report back

The loop above is **outbound**: a route session claims a ticket, resolves it, records it. Work also flows the other way. A ticket gets done by another vehicle. A code review clears fog nobody was looking for. A debugging session answers, incidentally, the question a blocked ticket was waiting on.

Such a session can already close a ticket it owned: `resolve` accepts any ticket carrying a `wayfinder:` label. What it had no typed way to do is carry a finding to the **route** when it owned nothing. A bare comment leaves no trailer, and `wayfinder-feedback:` is harvested but addressed to the reflection brief, which judges the vehicle rather than advancing the map.

The **`wayfinder-report-back`** skill is that path, and it splits on whether the reporting session owned a ticket:

- **It owned one** (an implementation ticket handed to another vehicle, say): it satisfies the `## Report back` block, posts with a trailer, and **closes the ticket itself**. The session that did the work knows whether it is done; a later wayfinder session would be guessing. `resolve --force` would also close it, but records `mode: resolve`, attributing the run to a route session that never happened.
- **It owned nothing**: it deposits a finding on the map and closes nothing. It may name which **Not yet specified** patch it touches and propose ticket candidates, but it does not graduate fog, create tickets, or edit the map body. Those are this skill's acts, taken with the whole map loaded.

**What that means for a route session.** Read the map's recent comments, not only its body: a report may be sitting there holding fog to graduate, a ticket candidate to create, or a contradiction to a recorded decision. Disposing of deposited reports is route work like any other, and the run trailer marks them with `mode: report` so they are easy to find.

Write the `## Report back` block on every ticket you create, including the ones you expect to resolve yourself. Which tickets get handed off is not knowable at charting time, and the cost of the block is two lines.

## Telemetry: how the wayfinder improves itself

The spec you are reading is versioned, and every session leaves a trace of how well it served. That trace is what the next version is built from. Tool: `~/.claude-shared-config/skills/wayfinder/tools/wayfinder_runs.py`.

**Be honest about what this is.** It is best-effort by placement, not a gate. Nothing stops a session closing an issue in the GitHub UI and leaving no trace. What the design buys is that the traced path is the *easy* path, and an untraced run is **detected** (`harvest` reports it as a GAP) instead of vanishing.

### The run

One run is one session: one charting session, or one ticket resolution. Each leaves a single collapsed `wayfinder_run` block inside a comment the session already had to post, so the telemetry is the same action as the work:

- **Charting** → `wayfinder_runs.py chart --map <n> --tickets-created <k> --fog-patches <j> [--friction tag:note ...]`. Posts the trailer on the map and plants the reflection ticket.
- **Resolving** → `wayfinder_runs.py resolve --ticket <n> --body-file <answer> --outcome resolved [--tickets-created <k>] [--fog-graduated <j>] [--friction tag:note ...]`. Posts the answer with the trailer, then closes. Re-running after a failed close **resumes** (closes, no duplicate comment); it never needs `--force`.

`--outcome` is one of `resolved`, `out_of_scope`, `horizon`, `partial`, `abandoned`. `horizon` and `out_of_scope` both close a ticket without resolving it on the route, and they are kept apart on purpose: one was queued, the other was rejected, and a retro that cannot see the difference reads a deferral as a scoping mistake. There is deliberately **no self-assigned score**: a number an agent grades itself on is not evidence.

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
3. **Create the map** (label `wayfinder:map`): Destination and Notes filled in, Decisions-so-far empty, the fog sketched into **Not yet specified**. Anything the grilling surfaced as a clear next stage _after_ this destination goes straight into **Horizon**, so it is recorded as deferred from the first session rather than argued about again in the third.
4. **Create the tickets you can specify now** as child issues of the map, then wire blocking edges in a **second pass** (issues need ids before they can reference each other). Wiring sorts them into the frontier and the blocked; everything you can't yet specify stays in the fog: the **Not yet specified** section.
5. **Fire the research subagents.** For each `research` ticket you just created, spin up a subagent that calls the Skill tool with "research" to resolve it in parallel, capturing its findings on a throwaway `research/<name>` branch with a context pointer from the ticket.
6. **Close the run**: `wayfinder_runs.py chart --map <n> --tickets-created <k> --fog-patches <j> [--friction tag:note ...]`. Posts the charting trailer and plants the reflection ticket. A map with no reflection child is a visibly unfinished chart.
7. Stop: charting is one session's work; it hand-resolves nothing.

### Work through the map

User invokes with a map (URL or number). A ticket is **optional**: without one, you pick the next decision, not the user.

1. Load the **map**: the low-res view, not every ticket body.
2. **Orient the human before any write.** Post one short block: the map's name wrapping its link, where the route stands (decisions made, what sits on the frontier), the ticket you intend to take with its name and link, and the steps you plan for this session in two to four lines. This is a read-back, not a permission request: proceed unless the user redirects. When the user named the ticket themselves, the orientation still runs, just shorter.
3. Choose the ticket. If the user named one, use it. Otherwise take the first frontier ticket in order. **Claim it**: assign it to yourself before any work.
4. Resolve it. **Zoom as needed**: fetch the full body of any related or closed ticket on demand; call the Skill tool for whichever skills the `## Notes` block names. If in doubt, call the Skill tool twice, for "grilling" and "domain-modeling".
5. Record the resolution: write the answer to a file, then `wayfinder_runs.py resolve --ticket <n> --body-file <answer> --outcome <outcome> [--friction tag:note ...]`. That posts the answer as a **resolution comment** with the run trailer and **closes** the issue. Then **append a context pointer** to the map's Decisions-so-far (the tool prints the line to start from).
6. Add newly-surfaced tickets (create-then-wire); graduate any fog the answer has made specifiable, clearing each graduated patch from **Not yet specified** so it lives only as its new ticket. Pass the counts to `resolve` as `--tickets-created` and `--fog-graduated`. If the answer reveals that a ticket (this one or another) sits beyond the destination, close it off the route instead of resolving it: **rule it out of scope** if you would argue against doing it (`--outcome out_of_scope`), or **defer it to the Horizon** if you would do it in a later effort (`--outcome horizon`). If the decision invalidates other parts of the map, update or delete those tickets.
7. If `resolve` printed **RECURRING**, the spec is costing you now: run `wayfinder_runs.py reflect --map <n> --interim` and resolve the reflection ticket rather than carrying the friction into the next ticket.

The user may run unblocked tickets in parallel, so expect other sessions to be editing the same GitHub issues concurrently.

## This skill's own Horizon

Maps have a Horizon and so does this skill, on the same terms: sharp enough to state, deliberately not now, seed of a later version rather than a discard. Nothing here is rejected. Do not re-propose these as if they were new, and do not treat their absence as an oversight.

**A per-type quality bar for tickets, with a deterministic closeable check.** One body template per ticket type, plus a `wayfinder_runs.py` subcommand that answers closeable or not-closeable with a reason and no model judgement. The bar differs by type, which is what makes it worth encoding. A grilling ticket is closeable when its question is answered and the answer is recorded. A task's is that the work is done and the resulting facts are captured. A research ticket's is a fact found and cited. Deferred on 2026-09-10, for three reasons:

- **The taxonomies do not line up yet.** The types the bar was sketched over (grilling, task, research, implementation) are not this skill's four. `prototype` has no bar written for it, and `implementation` is not a wayfinder type at all, because wayfinder plans and does not build. Reconciling the two lists is a decision, not an implementation, so it belongs on a map.
- **Deterministic and meaningful pull in opposite directions here.** A check that takes no model judgement can assert that a heading exists and is non-empty. Specification quality is not heading presence. A green check that a bad ticket also passes is worse than no check, because it is trusted.
- **There is almost no run evidence.** Telemetry landed on 2026-09-10 and three maps exist. The reflection ticket is the designed venue for a spec change this size, and it should decide this one from friction the format actually caused, not ahead of it.
