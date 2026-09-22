---
name: wayfinder-viewer
description: "Open a wayfinder map as an interactive graph in the browser: the map at the root, its decision tickets as nodes, blocking edges between them, colour by frontier / claimed / blocked / closed. Refreshes the snapshot from GitHub Issues first when it is stale, then opens the page. Use when the user says 'show me the map', 'open the wayfinder map', 'what is on the frontier', 'where does the route stand', 'view map #N', 'the map of maps', 'wayfinder catalog', or asks to see a map visually rather than read it. Also use after charting or resolving a wayfinder ticket, to bring the pages back in line with GitHub. Reads only; it never writes to an issue. To WALK a map (claim and resolve a ticket) use the wayfinder skill instead."
nav:
  bay: know
  when: "See a wayfinder map as a graph: the frontier, what blocks what, a ticket's body and resolution. Also the catalog of every map."
  when_not: "Resolving a ticket or editing the map (use wayfinder). Reporting a finding back from another session (use wayfinder-report-back)."
  org: [klever]
---

# Wayfinder Viewer

Renders every wayfinder map as one self-contained HTML page and opens it. The
pages are a **read surface**. Nothing here posts, closes, or edits an issue.

Tool root: `~/Developer/grp-beklever-com/project-management/tools/wayfinder-viewer/`

## Quick start

```bash
cd ~/Developer/grp-beklever-com/project-management/tools/wayfinder-viewer
python3 refresh.py          # fetch if stale, always re-render
open site/index.html        # the catalog of every map
```

That is the whole happy path. `refresh.py` owns the regeneration policy, so
never call `fetch_wayfinder.py` or `generate.py` by hand unless you are
debugging one of them.

## Workflows

### Show a map

1. `python3 refresh.py` in the tool root.
2. Find the file: `ls site/map-*.html`. They are named `map-<number>-<slug>.html`.
3. `open site/map-38-powers-mcp-in-production-traders-using.html`.
4. Tell the user what the page now shows, **by name**: the map's name, how many
   tickets sit on the frontier, and the name of the first takeable one. Never a
   bare `#42`.

### Show the catalog

`python3 refresh.py && open site/index.html`. The catalog lists every map with
its ticket counts and marks the complete ones. Each card opens that map's page;
every map page has a `catalog` button in the header to come back.

### After charting or resolving

Run `python3 refresh.py`. The dirt marker (below) makes it fetch even inside the
freshness window, so the page reflects the ticket you just closed.

### Just check freshness

`python3 refresh.py --check` prints the snapshot age, the dirt marker state, and
whether a fetch would happen. It changes nothing and calls no API.

## The regeneration policy

One `gh` call costs about four seconds, so the tool does not fetch on a whim.

| Situation | What happens |
|---|---|
| Snapshot under 6h old, nothing written | re-render only, no API call, under a second |
| Snapshot over 6h old | fetch, then render |
| A wayfinder issue was written since the last fetch | fetch, then render, regardless of age |
| Snapshot missing or its schema is stale | fetch, then render |
| `--force` | fetch, then render |

The third row is a `PostToolUse` hook, `~/.claude/hooks/wayfinder-dirt.sh`. It
does **not** fetch. It touches `data/.dirty` when a command actually wrote to a
wayfinder issue, and `refresh.py` reads that marker. Registered in
`project-management/.claude/settings.local.json`, filtered to `gh *` and
`python3 *` so it does not spawn on every Bash call.

A generated page also states its own age in the footer and turns amber past 24
hours, so a stale page never reads as live.

## Reading the page

Left is the graph, right is the detail. The graph runs left to right: column 0
is the map, each later column is a step deeper in the blocking chain, so
takeable work sits on the left.

| Colour | Status | Meaning |
|---|---|---|
| green | on the frontier | open, unblocked, unclaimed — takeable now |
| blue | claimed | open and assigned, a session is on it |
| amber | blocked | at least one blocker is still open |
| purple | reflection | the retro on the vehicle, never on the frontier |
| grey | closed | resolved, ruled out of scope, or deferred to the horizon |

An amber arrow points from a blocker to what it blocks and fades to dashed grey
once that blocker closes. Drag to pan, scroll to zoom, click a ticket, `Esc` for
the map, `fit` for the whole shape, `1:1` for full size.

## Before changing the generator

Run `python3 selftest.py`. It renders synthetic maps designed to produce a
*wrong page rather than an error*: a hostile title, 80 tickets, a 40 KB body, an
off-map blocker, a dependency cycle, a missing type label, an unknown map
section, an empty map. It needs no network.

Details, the snapshot contract, and the two `blockedBy` traps:
[the tool README](~/Developer/grp-beklever-com/project-management/tools/wayfinder-viewer/README.md).
