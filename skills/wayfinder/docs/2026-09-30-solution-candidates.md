# Wayfinder — solution candidates for the nine survivors

**Date:** 2026-09-30
**Input:** `2026-09-30-failure-modes-survivors.md` (S1..S9, adjudicated). The failure modes are settled and are not re-litigated here.
**Scope of the change surface:** `SKILL.md`, `tools/wayfinder_runs.py`, optionally one Claude Code hook. No server, no daemon, no cron, no new service.

Two solutions per mode, eighteen total. Where the second branch is weaker, it says so.

Shared conventions used by several sketches below:

```python
def _section(body: str, heading: str) -> str:
    """The text under a `## <heading>` up to the next `##`. Empty when absent."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", body or "",
                  re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""
```

---

## S1 — The documented frontier query is truncated at 30 and returns zero

> **This mode must not be fixed alone.** Both S1 solutions make map #22's real frontier visible, and the first ticket in map order is **#171, the closing gate**, which S2 proves is unblocked only because its four declared edges do not exist. Shipping S1 without an S2 solution hands the closing gate to the next session as its first pick. S1 + S2-A is the minimum safe unit.

### S1-A — `frontier` subcommand; delete the hand-written query from the spec

- **Name:** frontier-subcommand
- **Kind:** `tool-fix` + `spec-change`

**What it does.** Moves the frontier computation out of `SKILL.md` prose and into `wayfinder_runs.py frontier --map N`, which reads through `_list_issues` and therefore inherits the existing `--limit 1000` plus the saturation hard error. The spec's query block is replaced by a one-line tool invocation. The three historical traps (`blockedBy` as an object, `totalCount` counting closed blockers, the missing `--limit`) become code that `check` can exercise, instead of a jq string a human retypes.

**The change.** New function next to `children_of` (`wayfinder_runs.py` ~line 370), and a new subcommand:

```python
def frontier(map_number: int) -> list[dict]:
    """Open, unassigned, no OPEN blocker, not the reflection ticket.

    Computed through _list_issues, so the --limit 1000 saturation error that
    protects every other traversal protects this one too. The spec used to
    carry this as a jq one-liner and it broke three times."""
    kids = [
        k for k in _list_issues("--json", "number,title,state,labels,parent,assignees")
        if (k.get("parent") or {}).get("number") == map_number
        and (k.get("state") or "").upper() == "OPEN"
        and ticket_type_of(k.get("labels")) != "reflection"
        and not (k.get("assignees") or [])
    ]
    out = []
    for k in kids:
        data = gh_json("issue", "view", str(k["number"]), "--repo", REPO,
                       "--json", "blockedBy") or {}
        nodes = (data.get("blockedBy") or {}).get("nodes") or []
        k["open_blockers"] = [n["number"] for n in nodes
                              if (n.get("state") or "").upper() == "OPEN"]
        if not k["open_blockers"]:
            out.append(k)
    return out


def cmd_frontier(args) -> int:
    picks = frontier(args.map)
    if not picks:
        print(f"  map #{args.map} has an EMPTY frontier. Before concluding the map is "
              "finished, run `audit --map %d`: a zero frontier has three known causes "
              "that are not completion." % args.map)
        return 0
    print(f"\n=== Frontier — map #{args.map} ===  (first in map order wins)\n")
    for k in picks:
        print(f"  [{ticket_type_of(k.get('labels'))}] {k['title']}")
        print(f"      https://github.com/{REPO}/issues/{k['number']}")
    return 0
```

Parser, next to the other subcommands (~line 1186):

```python
    fr = sub.add_parser("frontier", help="the open, unblocked, unclaimed children of a map")
    fr.add_argument("--map", type=int, required=True)
    fr.set_defaults(func=cmd_frontier)
```

`SKILL.md:35` loses its query and its two trap paragraphs, and becomes:

```markdown
- **Frontier query**: `wayfinder_runs.py frontier --map <n>`. First in map order wins.
  Open blockers and any assignee both remove a ticket from the frontier, and the
  reflection ticket is excluded by label so it can never be picked as ordinary route
  work. The query is in the tool, not here, because the hand-written version broke
  three times (`blockedBy` is an object not an array; `totalCount` counts closed
  blockers; `gh issue list` truncates at 30 without `--limit`). `wayfinder_runs.py
  check` exercises all three.
```

**Failure it closes.** The 2026-09-30 measurement: spec query verbatim = 0 tickets, real frontier = 2. Also closes the recurrence pattern — the line cannot break a fourth time by being retyped, because there is nothing to retype.

**What it does NOT close.** A session that ignores the tool and writes its own `gh issue list` anyway. It also does not make the two tickets it now surfaces *safe* to take (that is S2). The per-ticket `blockedBy` fetch is one API call per unassigned child; on a 40-child map that is noticeable latency, not a correctness problem.

**Cost.** ~40 lines of Python, ~10 lines of spec deleted and 6 added. Per session: one extra subprocess, a few seconds.

**New failure modes it introduces.** The frontier is now only as correct as one code path with no test — a silent regression in `frontier()` is invisible where the jq string at least sat in front of a reader. Pair it with the parity/fixture test in S1-B or a `check` case. Second: the "EMPTY frontier" hint points at `audit`, which only exists if S7-B ships; if it does not, reword the hint.

### S1-B — golden-fixture parity test for the frontier filter

- **Name:** frontier-fixture-test
- **Kind:** `tool-gate`

**What it does.** Adds a canned JSON fixture of issues with a hand-declared expected frontier, and makes `wayfinder_runs.py check` run the frontier filter over it. The fixture contains one issue per historical trap: an issue with only a CLOSED blocker (must be ON the frontier), an issue with an OPEN blocker (must be off), an assigned unblocked issue (off), the reflection ticket (off), and enough filler rows that a 30-item truncation would drop the expected picks. Detection at read time, complementary to S1-A's prevention at write time.

**The change.** A pure filter extracted from `frontier()` so it can be tested without the network, plus a `check` case:

```python
def _frontier_filter(kids: list[dict], map_number: int) -> list[dict]:
    """Pure: the same predicate frontier() applies, over data already fetched."""
    return [
        k for k in kids
        if (k.get("parent") or {}).get("number") == map_number
        and (k.get("state") or "").upper() == "OPEN"
        and ticket_type_of(k.get("labels")) != "reflection"
        and not (k.get("assignees") or [])
        and not [n for n in ((k.get("blockedBy") or {}).get("nodes") or [])
                 if (n.get("state") or "").upper() == "OPEN"]
    ]


FRONTIER_FIXTURE = [
    {"number": 1, "state": "OPEN", "parent": {"number": 99}, "assignees": [],
     "labels": [{"name": "wayfinder:grilling"}],
     "blockedBy": {"nodes": [{"number": 7, "state": "CLOSED"}], "totalCount": 1}},
    {"number": 2, "state": "OPEN", "parent": {"number": 99}, "assignees": [],
     "labels": [{"name": "wayfinder:task"}],
     "blockedBy": {"nodes": [{"number": 8, "state": "OPEN"}], "totalCount": 1}},
    {"number": 3, "state": "OPEN", "parent": {"number": 99},
     "assignees": [{"login": "someone"}], "labels": [{"name": "wayfinder:task"}],
     "blockedBy": {"nodes": [], "totalCount": 0}},
    {"number": 4, "state": "OPEN", "parent": {"number": 99}, "assignees": [],
     "labels": [{"name": "wayfinder:reflection"}],
     "blockedBy": {"nodes": [], "totalCount": 0}},
    {"number": 5, "state": "CLOSED", "parent": {"number": 99}, "assignees": [],
     "labels": [{"name": "wayfinder:research"}],
     "blockedBy": {"nodes": [], "totalCount": 0}},
]
FRONTIER_EXPECTED = [1]
```

Appended inside `cmd_check`, before the `if problems:` block (~line 488):

```python
    got = [k["number"] for k in _frontier_filter(FRONTIER_FIXTURE, 99)]
    if got != FRONTIER_EXPECTED:
        problems.append(
            f"frontier filter returned {got}, expected {FRONTIER_EXPECTED}. "
            "Fixture row 1 is the closed-blocker case (0.2.3 trap), row 2 the open "
            "blocker, row 3 the claim, row 4 the reflection."
        )
```

**Failure it closes.** Both previously-patched traps regress loudly rather than silently. It does **not** by itself close today's `--limit` instance: the limit lives in `_list_issues`, not in the filter. Add one line to the `_list_issues` docstring test only if the limit is ever parameterised.

**What it does NOT close.** The truncation bug itself — the fixture is handed pre-fetched data. This is the weaker of the two branches on its own, and its value is entirely as a companion to S1-A: it turns S1-A's new untested code path into a tested one.

**Cost.** ~30 lines, all in `check`. Zero per-session cost (`check` runs from `warn_on_drift` after harvest/reflect, which is where it already runs).

**New failure modes it introduces.** A fixture drifts from reality. If GitHub changes the `blockedBy` shape a third time, the fixture encodes the old shape and `check` goes green against a filter that is now wrong in production — a green test that could not have failed. Mitigate by keeping the fixture's shape a verbatim copy of one live `gh issue view --json blockedBy` payload, with the date it was captured in a comment.

---

## S2 — Declared blocking edges do not exist, and the closing gate is takeable

### S2-A — `block` subcommand with mandatory read-back

- **Name:** verified-block
- **Kind:** `tool-fix`

**What it does.** Replaces the raw `gh api ... blocked_by` call in `SKILL.md:34` with `wayfinder_runs.py block --child N --blocker M`. The tool resolves the blocker's database id itself, so the documented footgun (passing `#number` where the database id is wanted) becomes unreachable. After the POST it re-reads the child's `blockedBy` and raises if the edge is absent. An edge is either verified or it is an error; there is no third state in which a session believes it wired something.

**The change.** New section in `wayfinder_runs.py` after `children_of`:

```python
def blocker_db_id(number: int) -> int:
    """The DATABASE id, not the #number and not the node_id. The dependencies
    endpoint accepts a #number silently and wires the wrong issue."""
    return int(gh_json("api", f"repos/{REPO}/issues/{number}", "--jq", ".id"))


def blocked_by_numbers(number: int) -> list[int]:
    data = gh_json("issue", "view", str(number), "--repo", REPO,
                   "--json", "blockedBy") or {}
    return [n["number"] for n in ((data.get("blockedBy") or {}).get("nodes") or [])]


def cmd_block(args) -> int:
    child, blocker = args.child, args.blocker
    if child == blocker:
        raise WayfinderError(f"#{child} cannot block itself")
    before = blocked_by_numbers(child)
    if blocker in before:
        print(f"  #{blocker} already blocks #{child} — verified, nothing posted")
        return 0
    gh("api", "--method", "POST",
       f"repos/{REPO}/issues/{child}/dependencies/blocked_by",
       "-F", f"issue_id={blocker_db_id(blocker)}")
    after = blocked_by_numbers(child)
    if blocker not in after:
        raise WayfinderError(
            f"the POST was accepted but #{blocker} is NOT in #{child}'s blockedBy "
            f"(now {after}). The edge did not take. Do not draw it as enforced and "
            "do not treat #%d as blocked." % child
        )
    print(f"  edge VERIFIED: #{blocker} blocks #{child}")
    return 0
```

Parser:

```python
    b = sub.add_parser("block", help="wire a blocking edge and verify it took")
    b.add_argument("--child", type=int, required=True, help="the ticket that becomes blocked")
    b.add_argument("--blocker", type=int, required=True, help="the ticket that must close first")
    b.set_defaults(func=cmd_block)
```

`SKILL.md:34` becomes:

```markdown
- **Blocking**: `wayfinder_runs.py block --child <n> --blocker <m>`. It resolves the
  blocker's database id, posts the edge, then re-reads `blockedBy` and fails loudly if
  the edge did not take. Never wire an edge with a raw `gh api` call: `issue_id` wants
  the numeric *database* id and silently targets the wrong issue when given a `#number`,
  and nothing then re-reads it. An unverified edge is not an edge; do not draw it on a
  diagram as enforced.
```

**Failure it closes.** The four declared-but-absent edges into #171 (cutover acceptance). Any one of them wired through this command would have failed loudly at charting time on 2026-09-29 rather than being drawn as a solid edge in the run report.

**What it does NOT close.** The four edges that are already missing — this is prevention only, so map #22 needs a repair pass (`block` four times, once the command exists). It also does nothing about an edge that is correctly wired and later deleted in the GitHub UI.

**Cost.** ~35 lines plus 8 lines of parser and spec. Per session: two extra API calls per edge at charting, which is the only time edges are written.

**New failure modes it introduces.** The read-back uses `gh issue view --json blockedBy` while the write uses the REST dependencies endpoint. Codex measured that REST endpoint returning 404 during the review, so the two surfaces disagree at least sometimes. If the GraphQL read lags the REST write, the command will raise on an edge that did in fact take, and the session will retry and create a duplicate. Add a single 2-second sleep-and-retry before raising, and make the error text say "verify by hand before re-running".

### S2-B — edge manifest in the map body, audited

- **Name:** edge-manifest
- **Kind:** `spec-change` + `tool-gate`

**What it does.** The map body gains a machine-readable fenced block declaring every intended edge. `wayfinder_runs.py edges --map N` diffs the declaration against GitHub and reports `MISSING` / `EXTRA`; `--apply` wires the missing ones through the same verified path as S2-A. This makes the *intent* a durable artifact instead of prose in a run report, so a drift that happens later (an edge deleted in the UI, a `--force` resolve) is detectable at any time, not just at write time.

**The change.** In the map body template (`SKILL.md:46-74`), after `## Decisions so far`:

````markdown
## Edges

<!-- the declared blocking graph. `wayfinder_runs.py edges --map <n>` diffs this
     against GitHub; `--apply` wires what is missing. One line per edge. -->

```wayfinder-edges
<blocked-ticket> <- <blocker-ticket>
```
````

Tool:

```python
EDGE_BLOCK_RE = re.compile(r"```wayfinder-edges\n(.*?)\n```", re.DOTALL)
EDGE_LINE_RE = re.compile(r"^\s*#?(\d+)\s*<-\s*#?(\d+)\s*$", re.MULTILINE)


def declared_edges(map_number: int) -> set[tuple[int, int]]:
    body = (issue(map_number, "body") or {}).get("body") or ""
    m = EDGE_BLOCK_RE.search(body)
    if not m:
        return set()
    return {(int(c), int(b)) for c, b in EDGE_LINE_RE.findall(m.group(1))}


def cmd_edges(args) -> int:
    want = declared_edges(args.map)
    if not want:
        print(f"  map #{args.map} declares no edges (no ```wayfinder-edges block).")
        return 0
    missing, extra = [], []
    for child in sorted({c for c, _ in want}):
        have = set(blocked_by_numbers(child))
        declared = {b for c, b in want if c == child}
        missing += [(child, b) for b in sorted(declared - have)]
        extra += [(child, b) for b in sorted(have - declared)]
    for child, blocker in missing:
        print(f"  MISSING  #{blocker} should block #{child} and does not")
        if args.apply:
            cmd_block(argparse.Namespace(child=child, blocker=blocker))
    for child, blocker in extra:
        print(f"  EXTRA    #{blocker} blocks #{child} but the map does not declare it")
    if missing and not args.apply:
        print("\n  The map's dependency graph is a fiction where it says MISSING. "
              "Re-run with --apply, or fix the declaration.")
        return 1
    return 0
```

**Failure it closes.** The same four edges, plus the class the run report exhibited: a diagram whose legend claims enforcement with nothing checking it. With a manifest, the diagram is generated from checked data.

**What it does NOT close.** A wrong declaration. If the charting session writes `171 <- 130` and meant `171 <- 131`, the audit goes green on the wrong graph. It also requires every existing map to grow the block by hand.

**Cost.** ~45 lines plus a template section. Per session: one `edges --map N` call at orientation, one API call per declared child.

**New failure modes it introduces.** `EXTRA` will fire constantly and legitimately on any map where a human wired an edge in the UI, training readers to ignore the output — the classic warning-fatigue failure. Make `EXTRA` informational and non-exit-code-bearing, as sketched. Second: `--apply` is a write driven by a body that anyone can edit; a careless edit plus `--apply` blocks the wrong tickets and the frontier silently shrinks.

---

## S3 — `resolve` closes an open ticket on any prior trailer and discards the answer

### S3-A — classify the prior trailer before resuming (the minimal correct patch)

- **Name:** resume-on-resolution-only
- **Kind:** `tool-fix`

**What it does.** The resume branch currently treats *any* trailer, valid or malformed, as proof of a prior resolution. It should treat only a prior **resolution** as one: a trailer whose `mode` is `resolve` or `reflect`. A `mode: report` trailer is by definition not a resolution, so a ticket carrying one falls through to the normal path, which reads `--body-file`, posts the answer, and closes. A malformed trailer cannot be classified, so it refuses and asks for a human instead of guessing in the destructive direction. This is the patch a person can apply today.

**The change.** `wayfinder_runs.py`, replacing lines 644-666 in `cmd_resolve`:

```python
    # A prior trailer is only evidence of a prior RESOLUTION when it says so.
    # A `mode: report` trailer is a session that reported and deliberately did
    # not resolve; resuming on it would close the ticket and throw away the
    # answer file we were asked to post.
    prior_resolutions, unclassifiable = [], []
    for comment in data.get("comments", []):
        good, bad = extract_trailers(comment.get("body", ""))
        prior_resolutions += [r for r in good if r.get("mode") in ("resolve", "reflect")]
        unclassifiable += bad

    if unclassifiable and not args.force:
        raise WayfinderError(
            f"#{number} carries {len(unclassifiable)} malformed trailer(s), so this "
            "tool cannot tell whether it was already resolved. Resuming would close "
            "the issue and discard your answer; posting would risk a duplicate. Read "
            "the comments, then re-run with --force to post anyway."
        )

    if prior_resolutions and not args.force:
        prior = prior_resolutions[-1]
        print(f"  #{number} already carries a RESOLUTION trailer (run {prior.get('run_id')}, "
              f"mode {prior.get('mode')})")
        if state == "OPEN":
            if args.dry_run:
                print("  would RESUME: close the issue, no second comment")
                return 0
            gh("issue", "close", str(number), "--repo", REPO)
            print("  RESUMED: issue closed. No duplicate comment posted.")
        else:
            print("  already recorded and closed — nothing to do.")
        print_recurring(map_number, [])
        return 0
```

**Failure it closes.** The live precondition on #127, #160 and #161: each is open, each carries a `mode: report` trailer, and each is currently one ordinary `resolve` call away from being closed with its answer discarded and a success message printed.

**What it does NOT close.** A genuine retry after a failed close where the *answer changed* between the two runs — the second answer is still dropped, because a prior resolve trailer still triggers resume. That is S3-B's case. It also does not repair the state of #127/#160/#161, which remain open with a resolved-shaped trailer (S6-B's territory).

**Cost.** ~20 lines, a single function. No per-session cost. This is the smallest safe change in the whole document.

**New failure modes it introduces.** The malformed-trailer branch is a new hard refusal on a path that previously always succeeded. A map with one badly-formed historical trailer now blocks every future resolve on that ticket until someone reads it or passes `--force`, and `--force` posts a second trailer — so the escape hatch from a false refusal is itself a duplicate. Acceptable only because malformed trailers are rare and reported by `harvest`.

### S3-B — content-addressed idempotency

- **Name:** deterministic-run-id
- **Kind:** `tool-fix`

**What it does.** Replaces "has this ticket been resolved before?" with "has *this exact answer* already been posted?". The `run_id` for a resolve becomes a hash of the ticket number and the body-file contents rather than a random uuid. The resume branch fires only when a trailer with that exact id already exists on the issue — which is true precisely when the previous attempt posted this answer and then failed to close. Idempotency by identity instead of by inference about mode.

**The change.** In `build_run` (~line 285) and `cmd_resolve`:

```python
import hashlib

def resolve_run_id(ticket: int, body: str) -> str:
    """Deterministic, so a retry of the SAME answer recognises itself and a
    DIFFERENT answer does not. A random id cannot tell those two apart, which
    is why the old resume branch had to guess from `mode`."""
    return hashlib.sha256(f"{ticket}\n{body}".encode("utf-8")).hexdigest()[:8]
```

`cmd_resolve` reads the body file *before* the resume decision, not after it:

```python
    if not args.body_file:
        raise WayfinderError("--body-file is required to resolve a ticket")
    body_path = Path(args.body_file).expanduser()
    if not body_path.exists():
        raise WayfinderError(f"--body-file {body_path} does not exist")
    answer = body_path.read_text(encoding="utf-8").rstrip()
    rid = resolve_run_id(number, answer)

    posted_ids = set()
    for comment in data.get("comments", []):
        good, _ = extract_trailers(comment.get("body", ""))
        posted_ids.update(str(r.get("run_id")) for r in good)

    if rid in posted_ids:
        print(f"  this exact answer is already posted on #{number} (run {rid})")
        if state == "OPEN":
            gh("issue", "close", str(number), "--repo", REPO)
            print("  RESUMED: issue closed. No duplicate comment posted.")
        print_recurring(map_number, [])
        return 0
```

with `build_run` accepting `run_id=` and defaulting to the uuid for non-resolve modes.

**Failure it closes.** The same three live tickets, and additionally the retry-with-a-changed-answer case that S3-A leaves open. Note it also makes `--body-file` mandatory on every resolve, which removes the "returns before reading `--body-file`" shape entirely.

**What it does NOT close.** A retry where the answer was edited by one whitespace character now posts a second comment instead of resuming — the hash is exact. And a genuine second resolution of a ticket that was already properly resolved and closed will still post (the close is a no-op, the comment is not).

**Cost.** ~25 lines, touching more of `cmd_resolve` than S3-A. No per-session cost.

**New failure modes it introduces.** Editing the answer file between a failed close and the retry — which is the natural human reaction to a failure — produces a duplicate answer comment where the old code produced none. That is a visible, recoverable failure rather than a silent data loss, so it is the right direction, but it will happen. Second: two trailers on one ticket with the same deterministic id would collapse to one run in `harvest`'s `seen` set, which is correct but worth knowing.

---

## S4 — Claims are never released, so the frontier starves

### S4-A — an `unclaim` verb plus a spec obligation

- **Name:** unclaim-verb
- **Kind:** `tool-fix` + `spec-change`

**What it does.** Gives the harness the release path it does not have. `wayfinder_runs.py unclaim --ticket N --reason "<why>"` removes your assignment, posts a one-line comment recording the release, and prints that the ticket is back on the frontier. The spec gains the matching obligation: a session that claims a ticket and does not resolve it releases the claim before it ends.

**The change.**

```python
def cmd_unclaim(args) -> int:
    me = (gh_json("api", "user", "--jq", "{login: .login}") or {}).get("login")
    data = issue(args.ticket, "title,assignees,labels")
    if not wayfinder_labels(data.get("labels")):
        raise WayfinderError(f"#{args.ticket} carries no wayfinder: label")
    holders = [a["login"] for a in data.get("assignees") or [] if a.get("login")]
    if me not in holders:
        print(f"  #{args.ticket} is not claimed by you ({me}); holders: {holders or 'none'}")
        return 0
    gh("issue", "edit", str(args.ticket), "--repo", REPO, "--remove-assignee", me)
    post_comment(args.ticket,
                 f"Claim released by @{me}. Reason: {args.reason}\n\n"
                 "This ticket is back on the frontier.")
    print(f"  #{args.ticket} unclaimed — back on the frontier")
    return 0
```

```python
    u = sub.add_parser("unclaim", help="release a claim without resolving the ticket")
    u.add_argument("--ticket", type=int, required=True)
    u.add_argument("--reason", required=True,
                   help="one line: why the claim is being released")
    u.set_defaults(func=cmd_unclaim)
```

`SKILL.md:97`, appended to the claim paragraph:

```markdown
A claim you do not resolve must be **released**: `wayfinder_runs.py unclaim --ticket <n>
--reason "<why>"`. An assignment is the only thing removing a ticket from the frontier,
and `resolve` is otherwise the only path that clears one, so an unreleased claim starves
the map until a human edits GitHub by hand.
```

**Failure it closes.** Nothing that already happened — all ten stale claims on map #22 were left by sessions that are gone. It closes the *next* one, for any session that ends deliberately rather than by dying.

**What it does NOT close.** The actual observed mechanism. Nine of the ten claims were made in a 22-second scripted batch and the tenth has sat 16 days; none of those sessions was in a position to call an unclaim verb at the end. A verb that depends on the dying session's discipline does not address death. This is the weaker of the two branches, and it earns its place only as the manual repair tool S4-B's detection needs.

**Cost.** ~25 lines. Per session: one command when a claim is abandoned deliberately.

**New failure modes it introduces.** A session unclaims a ticket another session is actively working — the command checks only that *you* hold the claim, and every agent session is the same GitHub identity (`gabriel-amyot`), so "you" does not distinguish sessions. The comment it posts is the only trace of who released what.

### S4-B — claim age as data; stale claims re-enter the frontier report

- **Name:** claim-ttl
- **Kind:** `tool-fix`

**What it does.** Reads the assignment timestamp from the issue timeline and treats a claim older than a TTL (default 24 hours) as stale. `frontier` then prints two blocks: the clean frontier, and a `STALE CLAIMS` block listing tickets whose claim has expired, with the age in hours. Detection at read time, requiring no discipline from the session that abandoned the claim — which is the only kind of solution the observed evidence supports.

**The change.**

```python
CLAIM_TTL_HOURS = 24


def claim_age_hours(number: int) -> float | None:
    """Hours since the most recent `assigned` event. None when never assigned.

    --paginate with --jq applies the filter per page, so collect every page's
    timestamps and take the max in Python rather than asking jq for `last`."""
    stamps = gh_json(
        "api", f"repos/{REPO}/issues/{number}/timeline", "--paginate",
        "--jq", '[.[] | select(.event == "assigned") | .created_at]',
    ) or []
    if isinstance(stamps, dict):
        stamps = []
    flat = [s for s in stamps if isinstance(s, str)]
    if not flat:
        return None
    when = max(_dt.datetime.fromisoformat(s.replace("Z", "+00:00")) for s in flat)
    return (_dt.datetime.now(_dt.timezone.utc) - when).total_seconds() / 3600.0
```

In `cmd_frontier`, after printing the clean frontier:

```python
    claimed = [
        k for k in _list_issues("--json", "number,title,state,labels,parent,assignees")
        if (k.get("parent") or {}).get("number") == args.map
        and (k.get("state") or "").upper() == "OPEN"
        and (k.get("assignees") or [])
        and ticket_type_of(k.get("labels")) != "reflection"
    ]
    stale = []
    for k in claimed:
        age = claim_age_hours(k["number"])
        if age is not None and age > CLAIM_TTL_HOURS:
            stale.append((age, k))
    if stale:
        print(f"\n=== STALE CLAIMS (> {CLAIM_TTL_HOURS}h) — map #{args.map} ===")
        print("  A claim is a session saying 'I am on this'. These sessions are gone.\n")
        for age, k in sorted(stale, reverse=True, key=lambda p: p[0]):
            print(f"  {age/24:.0f}d  {k['title']}")
            print(f"      https://github.com/{REPO}/issues/{k['number']}")
        print("\n  Release one with `unclaim --ticket <n> --reason \"stale claim\"`, "
              "then take it. Do NOT take it while it is still assigned: the assignee "
              "is the claim, and two sessions on one ticket is the case claiming exists "
              "to prevent.")
```

**Failure it closes.** All ten. #127 shows as a 16-day claim and nine show as ~1-day-old batch claims the moment the TTL passes. The starvation becomes visible in the same output the session already reads to pick a ticket.

**What it does NOT close.** It reports; it does not release. A session still has to act (via S4-A). It also cannot distinguish an abandoned claim from a long-running legitimate HITL ticket waiting on a human — both look identical at 48 hours.

**Cost.** ~35 lines. Per session: one timeline API call per assigned open child — on map #22, ten calls, a few seconds.

**New failure modes it introduces.** Claim theft. A HITL grilling ticket waiting three days on Gabriel's availability reads as stale and gets taken by an agent, which is exactly the collision the claim mechanism exists to prevent. Mitigate by making the TTL type-aware (longer for `grilling` and `prototype`, which are HITL by definition) or by treating any comment activity on the ticket as refreshing the claim. Second: `--paginate` on a long timeline is slow and rate-limit-visible on a large map.

---

## S5 — Stale premises: finished work advertised as frontier

### S5-A — extract external references and print them at pick time

- **Name:** premise-refs
- **Kind:** `tool-fix` + `spec-change`

**What it does.** Regex-scrapes each frontier candidate's body for external references — Jira keys, GitLab MR URLs, GitHub PR URLs, other issue numbers — and prints them under the ticket in `frontier` output. The spec's Work-through-the-map step 3 gains: verify every listed reference's current state before claiming. The extraction is deterministic; the verification is the session's, which is where it has to be, because "is this Jira ticket's state still compatible with this question" is not a check a regex can make.

**The change.** In `wayfinder_runs.py`:

```python
PREMISE_PATTERNS = (
    ("jira", re.compile(r"\b((?:KTP|INS|SPV|PER)-\d+)\b")),
    ("mr",   re.compile(r"(https://[^\s)]*?/-/merge_requests/\d+)")),
    ("pr",   re.compile(r"(https://github\.com/[^\s)]+/pull/\d+)")),
    ("gh",   re.compile(r"(?<![\w/])#(\d+)\b")),
)


def premise_refs(body: str) -> list[tuple[str, str]]:
    """Every external thing this ticket's question hangs on. Deterministic
    extraction only; whether the reference has moved is the session's call."""
    out = []
    for kind, pattern in PREMISE_PATTERNS:
        for hit in dict.fromkeys(pattern.findall(body or "")):
            out.append((kind, hit))
    return out
```

and in `cmd_frontier`, per ticket:

```python
        body = (issue(k["number"], "body") or {}).get("body") or ""
        refs = premise_refs(body)
        if refs:
            print("      PREMISES (verify each is still true BEFORE claiming):")
            for kind, ref in refs:
                print(f"        {kind}: {ref}")
```

`SKILL.md:245` (Work through the map, step 3) becomes:

```markdown
3. Choose the ticket. If the user named one, use it. Otherwise take the first frontier
   ticket in order. **Check its premises before you claim it**: `frontier` lists every
   external reference in the ticket body (Jira keys, MRs, PRs, sibling issues). Read the
   current state of each. A ticket whose premise has moved — the MR merged, the Jira
   ticket closed, the question already answered elsewhere — is not route work; report
   what happened and close it rather than doing work that is already done. Then **claim
   it**: assign it to yourself before any work.
```

**Failure it closes.** Both telemetry instances. #29 ("already merged a week before this session was dispatched") and #28 ("executed by another vehicle on 2026-09-18") both carried the external reference in their bodies; nothing made the session look at it before starting.

**What it does NOT close.** A premise with no reference in the body — a decision that went stale because of a conversation, not a tracked artifact. And it is a prompt, not a gate: a session in a hurry reads past it.

**Cost.** ~20 lines plus one body fetch per frontier candidate. Spec: one rewritten step.

**New failure modes it introduces.** The `gh` pattern will match every `#123` in prose, including the ticket's own siblings and any number-shaped text, producing noise that trains readers to skip the block. Restrict `gh` matching to the `## Question` and `## Report back` sections, or drop the `gh` pattern and keep only Jira/MR/PR, which are the ones that went stale in both observed instances.

### S5-B — a declared `## Premises` block, mechanically checked

- **Name:** premises-block
- **Kind:** `spec-change` + `tool-gate`

**What it does.** Ticket authors write premises as structured lines instead of leaving them implicit in prose, and `wayfinder_runs.py premises --ticket N` checks the mechanically-checkable ones (GitHub issues and PRs via `gh`) against their live state, printing `HOLDS` / `VIOLATED` / `MANUAL`. `frontier` runs it on the ticket it is about to offer. Prevention at write time: the ticket records what it depends on at the moment its author knew.

**The change.** Ticket template (`SKILL.md:80-88`) gains an optional section:

```markdown
## Premises

<!-- optional. What must still be true for this question to be worth answering.
     One per line, `<kind>: <ref> — <what must hold>`. kind is gh | pr | jira.
     `wayfinder_runs.py premises --ticket <n>` checks the gh and pr lines. -->

- gh: #29 — must still be OPEN; if it closed, this work is already done
- jira: KTP-1003 — must not be Done
```

Tool:

```python
PREMISE_LINE_RE = re.compile(
    r"^\s*-\s*(gh|pr|jira):\s*(\S+?)\s*(?:—|-{1,2})\s*(.+?)\s*$", re.MULTILINE)


def cmd_premises(args) -> int:
    body = (issue(args.ticket, "body") or {}).get("body") or ""
    lines = PREMISE_LINE_RE.findall(_section(body, "Premises"))
    if not lines:
        print(f"  #{args.ticket} declares no premises.")
        return 0
    violated = 0
    for kind, ref, expectation in lines:
        if kind == "gh":
            state = (gh_json("issue", "view", ref.lstrip("#"), "--repo", REPO,
                             "--json", "state") or {}).get("state", "?")
            print(f"  gh {ref} is {state} — expected: {expectation}")
            violated += state.upper() == "CLOSED"
        elif kind == "pr":
            state = (gh_json("pr", "view", ref, "--json", "state") or {}).get("state", "?")
            print(f"  pr {ref} is {state} — expected: {expectation}")
            violated += state.upper() in ("MERGED", "CLOSED")
        else:
            print(f"  MANUAL  {kind} {ref} — {expectation}")
    if violated:
        print(f"\n  {violated} premise(s) may have moved. This ticket's question may "
              "already be answered. Do not claim it until you have read them.")
        return 1
    return 0
```

**Failure it closes.** The same two instances, and more sharply: #29's premise ("built, awaiting merge") is exactly a `pr: <url> — must not be merged` line, and the check would have returned `MERGED` before the session started.

**What it does NOT close.** Every ticket that already exists, none of which has the block. The `jira` kind stays `MANUAL` unless the check shells out to `jira_skill.py`, which couples wayfinder to a Klever-specific tool it currently has no dependency on.

**Cost.** ~40 lines plus a template section. Per session: one command, a handful of API calls.

**New failure modes it introduces.** The block is optional, so the tickets most likely to go stale are the ones whose author did not bother. A `VIOLATED` with a non-zero exit will be wired into something as a gate eventually, and a wrongly-written premise line then blocks legitimate work. Also: `gh pr view <url>` on a GitLab MR URL fails, so the `pr` kind silently covers only GitHub while most Klever work is on GitLab — the kind list needs a `mr` entry that is honestly `MANUAL`.

---

## S6 — `report --outcome resolved` without `--close` inflates the resolved count

### S6-A — refuse the contradictory combination at write time

- **Name:** resolved-implies-closed
- **Kind:** `tool-gate`

**What it does.** Makes `report --ticket N --outcome resolved` without `--close` a hard error. A resolution that leaves the ticket open is a contradiction: either the work is done and the ticket closes, or it is not and the outcome is `partial`. The same rule applies to `out_of_scope` and `horizon`, which both close by definition per `SKILL.md:146`.

**The change.** In `cmd_report`, after the ticket branch resolves `outcome` (~line 774):

```python
CLOSING_OUTCOMES = ("resolved", "out_of_scope", "horizon")

    if number is not None and outcome in CLOSING_OUTCOMES and not args.close:
        raise WayfinderError(
            f"--outcome {outcome} without --close records a closing outcome on a "
            f"ticket that stays OPEN. `reflect` totals on outcome alone, so this "
            "run would be counted as finished work while #%d sits on the board. "
            "Pass --close if the work is done, or --outcome partial if it is not."
            % number
        )
```

and remove the default from the ticket path so the caller must state it:

```python
    rb.add_argument("--outcome", choices=OUTCOMES, default=None,
                    help="required with --ticket. Ignored for an incidental report, "
                         "which is always 'reported'.")
```

with `outcome = args.outcome or "partial"` replaced by an explicit error when `--ticket` is given and `--outcome` is absent.

**Failure it closes.** The #127 record (`outcome: resolved`, `issue_state: OPEN`) could not have been written. The default `--outcome resolved` is what produced it, and removing the default removes the whole class.

**What it does NOT close.** The corrupted corpus that already exists. The interim reflection on #204 still reports "12 resolved" with at least one open among them, and every repair reasoned from that distribution is still built on it. S6-B is required for that.

**Cost.** ~12 lines. Zero per-session cost.

**New failure modes it introduces.** A legitimate case is now blocked: a session that finished a ticket but cannot close it (permissions, a close that failed) has no honest outcome left except `partial`, which understates what happened. Also, removing the default breaks any existing wrapper or muscle-memory invocation of `report --ticket` — a loud break, but a break.

### S6-B — `reflect` totals on the effective outcome

- **Name:** effective-outcome
- **Kind:** `tool-fix`

**What it does.** `harvest` already records GitHub's real `issue_state` on every run. `reflect` ignores it and totals on `outcome` alone. This makes `reflect` derive an *effective* outcome from both, so a closing outcome recorded against an open ticket is counted in its own bucket and printed as a contradiction. Detection at read time, and it repairs the existing corpus without touching a single write path.

**The change.** Near `recurring()` (~line 411):

```python
CLOSING_OUTCOMES = ("resolved", "out_of_scope", "horizon")


def effective_outcome(run: dict) -> str:
    """GitHub's state overrides the trailer's claim. A run that says `resolved`
    on a ticket that is still OPEN did not resolve anything; counting it as a
    resolution corrupts the only corpus the spec repairs are reasoned from."""
    outcome = run.get("outcome", "?")
    if (run.get("ticket") is not None
            and outcome in CLOSING_OUTCOMES
            and (run.get("issue_state") or "").upper() == "OPEN"):
        return f"{outcome}!STILL-OPEN"
    return outcome
```

In `cmd_reflect` (~line 1055), replace the `by_outcome` accumulation and add a call-out:

```python
        eff = effective_outcome(run)
        by_outcome[eff] = by_outcome.get(eff, 0) + 1
...
    contradicted = [r for r in runs if effective_outcome(r).endswith("!STILL-OPEN")]
    if contradicted:
        print(f"\nCONTRADICTED OUTCOMES: {len(contradicted)} run(s) claim a closing "
              "outcome on a ticket GitHub still reports as OPEN. They are counted in "
              "their own bucket above, not as resolutions.")
        for r in contradicted:
            print(f"      #{r.get('ticket')}  outcome={r.get('outcome')}  "
                  f"state=OPEN  run {r.get('run_id')}  {r.get('comment_url')}")
```

**Failure it closes.** The #127 miscount, and every past and future instance of it, from data already on disk. Re-running `reflect --map 22 --interim` after this patch reports the true resolved count, which is the input the repairs for every other mode on this list depend on.

**What it does NOT close.** The reverse error: a ticket closed in the UI with a `partial` trailer still reports `partial`. And it does not stop the bad write happening (S6-A).

**Cost.** ~20 lines. Zero per-session cost; runs inside `reflect`, which is already a read.

**New failure modes it introduces.** The `!STILL-OPEN` suffix creates new bucket labels, so any downstream reader (a human comparing two reflection briefs, a future script) sees the outcome distribution change shape between versions with no migration note. Put the change in `CHANGELOG.md` and keep the raw `outcome` visible in the contradicted list, as sketched.

---

## S7 — Tickets created outside the index

Neither solution touches the trailer-leakage third of this mode. `SKILL.md:177` states plainly that telemetry is "best-effort by placement, not a gate", and the 21% GAP rate is the accepted cost of that stated choice. Turning it into a gate is a different argument, and nothing in the survivor set makes it.

### S7-A — `new-ticket` subcommand with parent and label read-back

- **Name:** guarded-create
- **Kind:** `tool-fix` + `spec-change`

**What it does.** Wraps `gh issue create` so the two properties that break things — the parent link and the `wayfinder:<type>` label — cannot be omitted, and are re-read after creation to prove they took. The spec's ticket-creation line points at this instead of at raw `gh`. It deliberately does **not** inspect the body: the skill's own Horizon already rejected heading-presence as a quality proxy, and a green check a bad ticket also passes is worse than no check.

**The change.**

```python
def cmd_new_ticket(args) -> int:
    if args.type not in TICKET_TYPES:
        raise WayfinderError(
            f"--type {args.type!r} is not one of {TICKET_TYPES}. A ticket with no "
            "recognised type label is refused by resolve and report later."
        )
    parent_meta = issue(args.map, "labels,title")
    if "map" not in wayfinder_labels(parent_meta.get("labels")):
        raise WayfinderError(
            f"#{args.map} \"{parent_meta['title']}\" is not labelled wayfinder:map. "
            "A ticket whose parent is not a map is a child of no map and is "
            "invisible to every frontier query."
        )
    body_path = Path(args.body_file).expanduser()
    if not body_path.exists():
        raise WayfinderError(f"--body-file {body_path} does not exist")

    gh("label", "create", f"wayfinder:{args.type}", "--repo", REPO, check=False)
    url = gh("issue", "create", "--repo", REPO, "--parent", str(args.map),
             "--label", f"wayfinder:{args.type}", "--title", args.title,
             "--body-file", str(body_path)).strip()
    number = int(url.rstrip("/").rsplit("/", 1)[-1])

    check = issue(number, "parent,labels")
    if (check.get("parent") or {}).get("number") != args.map:
        raise WayfinderError(
            f"{url} was created but its parent is "
            f"{(check.get('parent') or {}).get('number')!r}, not #{args.map}. Fix it "
            f"with `gh issue edit {number} --repo {REPO} --parent {args.map}` before "
            "continuing: it is currently invisible to the frontier."
        )
    if ticket_type_of(check.get("labels")) != args.type:
        raise WayfinderError(f"{url} was created without its wayfinder:{args.type} label")
    print(f"  created and verified: {url}  (parent #{args.map}, type {args.type})")
    return 0
```

`SKILL.md:33` becomes:

```markdown
- **Child ticket**: `wayfinder_runs.py new-ticket --map <n> --type <research|prototype|
  grilling|task> --title "<question>" --body-file <file>`. It creates the issue, then
  re-reads it to prove the parent link and the type label took. A ticket with no parent
  is a child of no map and is invisible to every frontier query; a ticket with no type
  label is refused by `resolve` and `report`. To re-parent later: `gh issue edit <n>
  --repo <repo> --parent <map>`.
```

**Failure it closes.** #208 (`wayfinder:grilling`, no parent, subject is map #22's own shipped artifact) could not have been created this way. Also the two telemetry instances of a missing type label on #127 and #35.

**What it does NOT close.** Ticket creation by a session that does not know wayfinder exists — which is precisely how #208 arrived, from a cross-model review. A gate on a command only binds callers of that command.

**Cost.** ~40 lines plus a spec line. Per session: two extra API calls per ticket created.

**New failure modes it introduces.** A gate that is more work than the bypass is not a gate. `gh issue create` is one line and this is one line with more flags; the margin is thin, and a session under context pressure will reach for the shorter one. Second: the URL-to-number parse assumes `gh issue create` keeps printing a bare URL on stdout — if that output format changes, creation succeeds and the tool raises, which reads as a failure when it was not one.

### S7-B — repo-wide orphan sweep in `audit`

- **Name:** orphan-sweep
- **Kind:** `tool-gate`

**What it does.** A new `audit` subcommand sweeps the whole repo for any issue carrying a `wayfinder:` label and checks two invariants: it has a parent, and that parent is a `wayfinder:map`; and it carries a recognised type label. Because the sweep is repo-wide rather than map-scoped, it sees exactly the tickets no map-scoped query can — which is the definition of the failure.

**The change.**

```python
def cmd_audit(args) -> int:
    issues = _list_issues("--json", "number,title,state,labels,parent")
    maps = {i["number"] for i in issues if "map" in wayfinder_labels(i.get("labels"))}
    problems: list[tuple[dict, str]] = []
    for i in issues:
        kinds = wayfinder_labels(i.get("labels"))
        if not kinds or "map" in kinds:
            continue
        parent = (i.get("parent") or {}).get("number")
        if parent is None:
            problems.append((i, "NO PARENT — a child of no map, invisible to every "
                                "frontier query"))
        elif parent not in maps:
            problems.append((i, f"parent #{parent} is not labelled wayfinder:map"))
        if not any(k in TICKET_TYPES for k in kinds):
            problems.append((i, "no wayfinder:<type> label — resolve and report will "
                                "refuse this ticket"))
    if not problems:
        print(f"  {len(issues)} issue(s) swept, {len(maps)} map(s). No orphans, "
              "no untyped wayfinder tickets.")
        return 0
    for i, why in problems:
        print(f"  ORPHAN  #{i['number']} [{i['state']}] {i['title']}")
        print(f"          {why}")
    print(f"\n  {len(problems)} problem(s). Re-parent with "
          f"`gh issue edit <n> --repo {REPO} --parent <map>`.")
    return 1
```

```python
    a = sub.add_parser("audit", help="repo-wide sweep for orphaned or untyped wayfinder tickets")
    a.set_defaults(func=cmd_audit)
```

**Failure it closes.** #208 is found today, retroactively — the one thing S7-A cannot do. It also catches any future orphan regardless of which tool or which session created it.

**What it does NOT close.** Nothing is repaired automatically; the sweep reports. And a ticket created with no wayfinder label at all is invisible to the sweep too, because the sweep keys on the label.

**Cost.** ~30 lines. Per run: one `_list_issues` call over the whole repo (153 open issues today, well inside the 1000 limit). Run it from `harvest --all`, or on demand.

**New failure modes it introduces.** Exit code 1 on any orphan makes `audit` unusable in any chain until the backlog is zero, and the backlog includes historical tickets nobody intends to re-parent. Either fix the backlog first or add `--strict` and default to exit 0. Second: the repo is a general planning repo, so a non-wayfinder issue that happens to carry a `wayfinder:` label for filing reasons reads as an orphan forever.

---

## S8 — Cross-map blindness lets sibling maps ratify contradicting architecture

### S8-A — declare siblings; load their decisions at orientation

- **Name:** sibling-decisions
- **Kind:** `spec-change` + `tool-fix`

**What it does.** The map body gains a `## Sibling maps` section listing the map numbers whose scope touches this one, and `wayfinder_runs.py neighbours --map N` prints each sibling's `## Decisions so far` index. Work-through-the-map step 1 loads it. This is retrieval, not judgement: the session that is about to ratify a design has the neighbouring ratified decisions in context, which is the condition that was absent when #148 named PostgreSQL + PostGIS while sibling map #13 had already ratified BigQuery.

**The change.** Map body template, after `## Notes`:

```markdown
## Sibling maps

<!-- maps whose scope touches this one. `wayfinder_runs.py neighbours --map <n>` prints
     their Decisions-so-far so a resolution here cannot contradict a ratified decision
     there without someone seeing it. One line each, name wrapping the link. -->

- [<sibling map title>](link): <the boundary in one line>
```

Tool:

```python
def cmd_neighbours(args) -> int:
    body = (issue(args.map, "body") or {}).get("body") or ""
    section = _section(body, "Sibling maps")
    numbers = sorted({int(n) for n in re.findall(r"/issues/(\d+)", section)}
                     | {int(n) for n in re.findall(r"(?<![\w/])#(\d+)", section)})
    if not numbers:
        print(f"  map #{args.map} declares no sibling maps. If another map's scope "
              "touches this one, list it under `## Sibling maps` — a contradiction "
              "between two ratified decisions is only visible to a reader holding both.")
        return 0
    for n in numbers:
        sib = issue(n, "title,body,labels")
        if "map" not in wayfinder_labels(sib.get("labels")):
            print(f"\n  #{n} \"{sib['title']}\" is not a wayfinder:map — skipped")
            continue
        print(f"\n=== #{n} — {sib['title']} — Decisions so far ===")
        decisions = _section(sib.get("body") or "", "Decisions so far").strip()
        print(decisions or "  (none recorded)")
    return 0
```

`SKILL.md:244` (step 1 of Work through the map) becomes:

```markdown
1. Load the **map**: the low-res view, not every ticket body. Then load its neighbours:
   `wayfinder_runs.py neighbours --map <n>` prints the Decisions-so-far of every map
   listed under `## Sibling maps`. A decision on this map that contradicts a ratified
   decision on a sibling is the most expensive kind of wrong, because both are recorded
   as settled.
```

**Failure it closes.** The census collision. Map #13's ratified BigQuery + Dataform decision would have been in the session's context before #148 closed naming PostgreSQL + PostGIS.

**What it does NOT close.** The aggravating detail — the design's own §2.1 *flagged* the collision and nobody took it. Loading the sibling decisions does not route a flagged conflict to an owner; that is S8-B. It also depends on someone declaring the sibling in the first place.

**Cost.** ~30 lines plus a template section. Per session: one command, one API call per sibling.

**New failure modes it introduces.** Context cost. Printing every sibling's full decisions index at orientation on a mature map pushes a large block into a session that then has less room for the actual ticket, which is the resource wayfinder exists to conserve. Cap the output (most recent N decisions per sibling) if the index grows past a screen.

### S8-B — `wayfinder-conflict:` routing, harvested and surfaced until claimed

- **Name:** conflict-routing
- **Kind:** `spec-change` + `tool-fix`

**What it does.** Adds a second first-line comment convention alongside `wayfinder-feedback:`. A session that notices a contradiction with another map posts `wayfinder-conflict: #<other-map> — <one line>`. `harvest` collects them into the map log; `reflect` and `frontier` print OPEN CONFLICTS until a later comment on the same issue starts `wayfinder-conflict-routed: #<ticket>`, naming the ticket that now owns it. The pair is deterministic: a conflict is open until a routed line names an issue. This attacks the routing gap directly rather than the visibility gap.

**The change.** Next to `FEEDBACK_RE` (~line 111):

```python
CONFLICT_RE = re.compile(r"^\s*wayfinder-conflict:\s*(.*)$", re.IGNORECASE | re.DOTALL)
ROUTED_RE = re.compile(r"^\s*wayfinder-conflict-routed:\s*#?(\d+)", re.IGNORECASE)
```

In `harvest_map`'s `scan()`, beside the feedback branch (~line 869):

```python
            if CONFLICT_RE.match(first):
                conflicts.append({
                    "issue": number,
                    "author": (comment.get("author") or {}).get("login"),
                    "body": body.strip()[:500],
                    "url": comment.get("url"),
                    "routed_to": None,
                })
            routed = ROUTED_RE.match(first)
            if routed:
                for c in conflicts:
                    if c["issue"] == number and c["routed_to"] is None:
                        c["routed_to"] = int(routed.group(1))
                        break
```

with `conflicts: list[dict] = []` declared beside `feedback` and `"conflicts": conflicts` added to the returned dict. In `cmd_reflect` and `cmd_harvest`:

```python
    open_conflicts = [c for c in log.get("conflicts") or [] if c["routed_to"] is None]
    if open_conflicts:
        print(f"\nOPEN CROSS-MAP CONFLICTS: {len(open_conflicts)} — a decision here "
              "contradicts a ratified decision elsewhere and nobody owns it yet.")
        for c in open_conflicts:
            print(f"      #{c['issue']} @{c['author']}: {c['body'].splitlines()[0]}")
            print(f"        {c['url']}")
        print("      Route each one: create the ticket that owns it, then comment "
              "`wayfinder-conflict-routed: #<ticket>` on the issue above.")
```

`SKILL.md`, in the Report back or Telemetry section:

```markdown
### Cross-map conflicts

A resolution that contradicts a ratified decision on **another** map is not this map's
business to settle, and it must not be left in prose inside a closed ticket. Post a
comment whose first line is `wayfinder-conflict: #<other-map> — <one line>`. `harvest`
collects it and `reflect` prints it as an OPEN CONFLICT on every run until someone
creates the ticket that owns it and comments `wayfinder-conflict-routed: #<ticket>`.
A conflict a closed ticket carried silently is the failure this exists to end.
```

**Failure it closes.** The exact aggravating detail: §2.1 flagged the collision, the ticket closed anyway, and nothing carried the flag forward. With this, closing #148 would have left a standing OPEN CONFLICT that every subsequent harvest and reflection reprints.

**What it does NOT close.** A conflict nobody notices. It routes a *flagged* conflict; the noticing is still human or model work, which is why it pairs with S8-A's retrieval rather than replacing it.

**Cost.** ~40 lines plus a spec section. Per session: none beyond what `harvest` already scans.

**New failure modes it introduces.** An unrouted conflict prints forever, on every harvest of every map, which is warning fatigue by construction — and the nagging is the mechanism, so softening it defeats it. Second: the routed line is unverified. Anyone can silence a conflict by naming any issue number, including one that has nothing to do with it, and nothing checks that the named ticket exists or is open.

---

## S9 — The outcome vocabulary forces mislabelling

### S9-A — `resolve --no-close`, plus the missing outcome

- **Name:** route-run-without-closing
- **Kind:** `tool-fix` + `spec-change`

**What it does.** Both observed mislabels come from the same place: `resolve` always closes, so a route session that deliberately leaves a ticket open has no honest command and reaches for `report`, which means "a session that was not walking the map". Adding `--no-close` lets a route run record itself as a route run. Separately, adds `parent_retired` to `OUTCOMES` for the case `partial` was forced to cover.

**The change.** `OUTCOMES` (~line 95):

```python
OUTCOMES = ("charted", "resolved", "out_of_scope", "horizon", "partial", "abandoned",
            "reported", "parent_retired")
```

with the comment extended:

```python
# `parent_retired` is not `partial`. A partial answer is progress on a live
# question; a retired parent means the question stopped mattering. A retro that
# cannot see the difference reads a cancelled branch as unfinished work.
```

`build_run` records the fact rather than the intent:

```python
    run["closed"] = closed
```

`cmd_resolve`, around the close (~line 693):

```python
    if args.no_close:
        print(f"  #{number} left OPEN by --no-close. The run is recorded as route work; "
              "the ticket stays on the board and off the frontier while you hold the claim.")
    else:
        try:
            gh("issue", "close", str(number), "--repo", REPO)
```

Parser:

```python
    r.add_argument("--no-close", action="store_true",
                   help="record a route run without closing: the session worked the "
                        "ticket on the route and deliberately leaves the question open")
```

Guard against the S6 shape recurring here:

```python
    if args.no_close and args.outcome in CLOSING_OUTCOMES:
        raise WayfinderError(
            f"--outcome {args.outcome} with --no-close is a contradiction: a closing "
            "outcome on a ticket that stays open. Use --outcome partial."
        )
```

Spec (`SKILL.md:186`) adds `parent_retired` to the outcome list with its one-line meaning, and the Work-through-the-map step 5 gains a sentence on `--no-close`.

**Failure it closes.** Run `e2953c70` on #127: a route session correcting a claimed ticket and deliberately leaving it open, filed as `mode: report` and thereby attributed to a session that was not walking the map. And run `fa622ea1` on #63, where the note says outright that `partial` "is the least-wrong outcome and does not say this".

**What it does NOT close.** The next situation the vocabulary does not have a word for. This is an extension, so it fixes the two observed gaps and nothing structural. `resolve` still exposes seven outcomes with no semantic check tying an outcome to what actually happened, beyond the two guards above.

**Cost.** ~20 lines plus three spec lines. Zero per-session cost.

**New failure modes it introduces.** `--no-close` plus the S4 claim problem is a starvation engine: a route session can now leave a ticket open *and* claimed, with a trailer saying it was worked, and nothing brings it back. Do not ship `--no-close` without S4-B's stale-claim detection. Second: a new outcome value changes the shape of `by_outcome` across spec versions, so two reflection briefs are no longer directly comparable.

### S9-B — split the one axis into two: disposition × closure

- **Name:** two-axis-outcome
- **Kind:** `tool-fix` + `spec-change`

**What it does.** The current `--outcome` conflates three independent things: what happened to the question, whether the ticket closed, and who did the work. This makes closure a *derived* fact (the tool knows whether it closed the issue) and reduces the declared field to one small orthogonal axis, `--disposition ∈ {answered, deferred, rejected, none}`, with a free-text `--disposition-note` for the long tail. `mode` continues to carry who did the work. A situation the vocabulary has no word for lands in the note rather than forcing a wrong value.

**The change.**

```python
DISPOSITIONS = {
    "answered": "the question this ticket asked now has an answer on the route",
    "deferred": "the question still matters, just not before this destination",
    "rejected": "the question was ruled out of scope",
    "none":     "no disposition: the run touched the ticket without settling it",
}
```

`build_run` emits both axes and derives the third:

```python
    run["disposition"] = disposition
    run["closed"] = closed              # what the tool actually did, not a claim
    if note:
        run["disposition_note"] = note
```

`reflect` groups on the pair:

```python
    by_disposition: dict[str, int] = {}
    for run in runs:
        key = f"{run.get('disposition', '?')}/{'closed' if run.get('closed') else 'open'}"
        by_disposition[key] = by_disposition.get(key, 0) + 1
```

with a back-compat mapping so the existing corpus still reads:

```python
LEGACY_OUTCOME_MAP = {
    "resolved": ("answered", True), "out_of_scope": ("rejected", True),
    "horizon": ("deferred", True), "partial": ("answered", False),
    "abandoned": ("none", False), "reported": ("none", None),
    "charted": ("none", None),
}
```

**Failure it closes.** Both instances, and the class: `mode: report` for route work becomes impossible because mode and disposition are separate, and the retired-parent case is `deferred` with a note rather than a wrong `partial`. It also subsumes S6 — a closing disposition with `closed: False` is a contradiction the data itself exposes, with no gate needed.

**What it does NOT close.** Nothing about the *quality* of the classification. A session that picks `answered` for a run that answered nothing is still unchecked.

**Cost.** ~70 lines across `build_run`, `validate_run`, both write commands, `reflect`, and the legacy map, plus a full spec rewrite of the outcome section and a CHANGELOG major bump. The largest single change in this document.

**New failure modes it introduces.** It invalidates the corpus at exactly the moment the corpus is being used to repair everything else on this list. Forty-two runs are recorded under the old vocabulary; every reflection comparing before and after now goes through `LEGACY_OUTCOME_MAP`, and the map is a guess in two of its seven rows (`partial` → `answered/open` is an interpretation, not a translation). This is the more correct model and the wrong thing to ship first. Revisit it at the reflection ticket, from friction the extended vocabulary actually causes.

---

## Sequencing and conflicts

### Must ship together

- **S1 (either branch) + S2-A.** Non-negotiable and stated in S1 above. Fixing the frontier query makes the real frontier visible, and the first ticket in map order is #171, the closing gate, unblocked only because four declared edges do not exist. S1 alone hands the closing gate to the next session as its first pick.
- **S1-A + S1-B.** S1-A moves the frontier predicate into untested code; S1-B is the test. Shipping S1-A alone trades a visible-but-wrong jq string for an invisible-and-maybe-wrong function.
- **S2-A + S2-B.** S2-B's `--apply` calls `cmd_block`, so the manifest needs the verified writer. S2-A stands alone; S2-B does not.
- **S4-B + S4-A.** Detection without a release verb leaves the reader with a list and no action. S4-A alone addresses a mechanism the evidence does not show (deliberate session end), so it is the dependent half, not the lead.
- **S9-A + S4-B.** `--no-close` lets a session leave a ticket open *and* claimed. Without stale-claim detection that is a new starvation path, strictly worse than the mislabelling it fixes.

### Mutually exclusive

- **S9-A and S9-B.** One extends the vocabulary, the other replaces it. Shipping A then B means migrating `parent_retired` twice.
- **S3-A and S3-B** overlap but do not conflict: B subsumes A's case. Pick one. A is the patch for today; B is the better model if `cmd_resolve` is being reworked anyway.
- **S6-A and S9-B** overlap: S9-B's derived `closed` field makes S6-A's guard structural. If S9-B is ever chosen, S6-A becomes dead code.

### Free (under ~10 lines, no behaviour risk)

Nothing in this document is under ten lines except the S6-A guard (~12) and the S9-A `OUTCOMES` addition (~3, but it drags the rest of S9-A behind it). **S6-B at ~20 lines is the closest thing to free that matters**: it changes no write path, touches only a printed total, and repairs the existing corpus from data already on disk.

### Data repair, required regardless

**The ten stale claims on map #22 need a manual release pass whatever S4 solution ships.** #127, #130, #149, #160, #161, #169, #202, #205, #206, #207 are all open, assigned, and unblocked. S4-A releases them one at a time once it exists; S4-B only reports them. Until the pass runs, the map's real frontier stays at two tickets against a true frontier of twelve, and every other fix operates on a starved board. Do the repair in the same session as the first wave, and record it — it is a `process` friction entry, not a silent tidy-up.

Two smaller repairs ride along: wire the four missing edges into #171 with `block` once S2-A exists, and re-parent #208 to whichever map owns it (or close it).

### Recommended first wave — four solutions

1. **S3-A (resume-on-resolution-only)** — a live data-loss bug with a currently-satisfied precondition on three open tickets, fixed in twenty lines with no dependency on anything else here.
2. **S1-A (frontier-subcommand)** — the highest-expected-cost mode, firing right now, and the only solution that attacks the recurrence pattern by deleting the line that has broken three times rather than patching it a third.
3. **S2-A (verified-block)** — ships with S1-A by necessity, and it is the write-time fix, so it makes every future edge trustworthy rather than only repairing #171's four.
4. **S6-B (effective-outcome)** — twenty read-only lines that correct the telemetry corpus every other repair on this list is reasoned from; leaving it out means designing the remaining fixes against a distribution known to be wrong.

The stale-claim data repair runs alongside these four. S1-B follows immediately as S1-A's test.

### Traps worth naming before anyone implements

- **S4-B's TTL is claim theft waiting to happen.** Grilling and prototype tickets are HITL by definition and legitimately sit for days. A flat 24-hour TTL marks them stale and invites a second session onto a live ticket — the exact collision claiming exists to prevent. Make the TTL type-aware before enabling it.
- **S7-A is a gate thinner than its bypass.** `gh issue create` stays one command away. A creation gate only binds sessions that already intend to comply; #208 came from a session that did not know wayfinder existed, and no write gate reaches it. S7-B is the branch that actually sees that case.
- **S8-B nags forever by design.** An unrouted conflict reprints on every harvest of every map. That is the mechanism, and softening it removes the value — but it is also how a warning becomes wallpaper. Ship it only with the intent to drive the list to zero.
- **S9-B is correct and badly timed.** It invalidates forty-two runs of telemetry at the moment that corpus is the input to every other repair, and two rows of its legacy mapping are interpretation rather than translation.
