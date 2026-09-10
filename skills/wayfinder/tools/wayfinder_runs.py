#!/usr/bin/env python3
"""wayfinder_runs.py — run telemetry for the wayfinder skill.

WHAT THIS IS
    Wayfinder plans an effort as a map issue with child decision tickets on
    GitHub. This tool records what each wayfinding session did, so the wayfinder
    SPEC (SKILL.md) can be improved from evidence instead of from memory.

    The unit of telemetry is the RUN: one charting session, or one
    ticket-resolution session. Each run leaves a `wayfinder_run` trailer inside
    a GitHub comment the session was already required to post. GitHub is the
    source of truth; `runs/` on disk is a derived cache for the cross-map view.

WHAT THIS IS NOT
    It is NOT mandatory telemetry. Nothing here can stop a session from closing
    an issue in the GitHub UI, or with a bare `gh issue close`, and leaving no
    trace. The design makes the traced path the EASY path and makes an untraced
    run DETECTABLE (`harvest` reports it as a GAP). That is the honest claim.
    dark-factory can enforce its Retro because a JS orchestrator runs its loop;
    wayfinder is prose, and prose does not enforce.

WRITER DISCIPLINE (concurrency)
    Several wayfinder sessions run at once against one map. Therefore:
      * `harvest` and `reflect` are the only writers under runs/. Both take an
        exclusive flock on runs/.lock and hold it across BOTH the map file and
        the INDEX.md regeneration, so the index can never describe a mixture of
        two harvest generations. Atomic replace alone would not give that: it
        prevents a torn file, not an inconsistent pair of files.
      * `chart` and `resolve` write to GitHub and only READ runs/.
    Temp files carry the pid, so two writers cannot clobber each other's temp.

COMMANDS
    chart    --map N ...                  plant the reflection ticket, post the charting trailer
    resolve  --map M --ticket N ...       post the resolution comment + trailer, close the issue
    reflect  --map N [--interim]          retro brief; reads GitHub, refreshes the runs/ cache
    harvest  --map N | --all              rebuild runs/ from GitHub; report GAPS
    check                                 version coupling + trailer schema self-test

    `chart` and `resolve` are both idempotent: re-running after a partial failure
    resumes rather than posting a duplicate.

Run `--help` on any subcommand.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import fcntl
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("wayfinder_runs.py needs PyYAML (pip install pyyaml)", file=sys.stderr)
    raise

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

REPO = "gabriel-amyot/klever-project-management"

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
CHANGELOG = SKILL_DIR / "CHANGELOG.md"
RUNS_DIR = SKILL_DIR / "runs"

TICKET_TYPES = ("research", "prototype", "grilling", "task", "reflection")

# A closed vocabulary, because RECURRING keys on the tag. Free prose does not
# recur: two sessions describe the same defect in different words and the
# signal never crosses the threshold. The tag is the join key; the note is the
# evidence a human reads.
FRICTION_TAGS = {
    "spec-wrong": "an instruction in SKILL.md is factually incorrect",
    "spec-missing": "no guidance existed for a situation that arose",
    "spec-ambiguous": "guidance existed but was read two ways",
    "tooling": "gh / the GitHub API / the CLI fought back",
    "sizing": "the ticket or the map was the wrong size",
    "process": "the workflow shape (claim, frontier, one-per-session) got in the way",
}

# `horizon` and `out_of_scope` both close a ticket without walking it on the
# route, and they are deliberately NOT one value. A horizon ticket was queued for
# a later map; an out-of-scope one was rejected outright. Collapsing them would
# make a retro read every deferral as a scoping mistake, which is the exact
# confusion the Horizon section exists to end.
OUTCOMES = ("charted", "resolved", "out_of_scope", "horizon", "partial", "abandoned")

RECURRING_THRESHOLD = 3

# Tickets closed before telemetry existed cannot carry a trailer. Counting them
# as GAPs would bury every real untraced run under permanent historical noise,
# and a report nobody can ever drive to zero is a report nobody reads. They are
# counted separately as `pre_telemetry`.
TELEMETRY_EPOCH = "2026-09-10"

TRAILER_SENTINEL = "<!-- wayfinder-run -->"
TRAILER_RE = re.compile(
    re.escape(TRAILER_SENTINEL) + r"\s*\n```yaml\n(.*?)\n```",
    re.DOTALL,
)
FEEDBACK_RE = re.compile(r"^\s*wayfinder-feedback:\s*(.*)$", re.IGNORECASE | re.DOTALL)

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_CHANGELOG_VER_RE = re.compile(r"^##\s+(\d+\.\d+\.\d+)", re.MULTILINE)


class WayfinderError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def gh(*args: str, check: bool = True) -> str:
    """Run gh and return stdout. Never piped, so a failure is visible."""
    proc = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False
    )
    if check and proc.returncode != 0:
        raise WayfinderError(
            f"gh {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def gh_json(*args: str):
    return json.loads(gh(*args) or "null")


def today() -> str:
    return _dt.date.today().isoformat()


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def spec_version() -> str:
    """Read the version from SKILL.md, so a trailer can never claim a wrong one."""
    text = SKILL_MD.read_text(encoding="utf-8") if SKILL_MD.exists() else ""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return "unknown"
    data = yaml.safe_load(m.group(1)) or {}
    return str(data.get("version") or "unknown")


def changelog_top() -> str | None:
    if not CHANGELOG.exists():
        return None
    m = _CHANGELOG_VER_RE.search(CHANGELOG.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def parse_friction(items: list[str] | None) -> list[dict]:
    """`--friction tag:note` -> [{tag, note}]. An unknown tag is a hard error."""
    out = []
    for raw in items or []:
        tag, _, note = raw.partition(":")
        tag = tag.strip()
        note = note.strip()
        if tag not in FRICTION_TAGS:
            raise WayfinderError(
                f"unknown friction tag '{tag}'. Use one of: "
                + ", ".join(f"{k} ({v})" for k, v in FRICTION_TAGS.items())
            )
        if not note:
            raise WayfinderError(f"friction '{tag}' has no note; the note is the evidence")
        out.append({"tag": tag, "note": note})
    return out


def atomic_write(path: Path, text: str) -> None:
    """Replace `path` atomically. The temp name carries the pid, so two writers
    racing on the same target cannot overwrite each other's half-written temp."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp.{os.getpid()}")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


@contextlib.contextmanager
def runs_lock():
    """Exclusive lock over the whole runs/ cache.

    Held across the map file write AND the INDEX.md regeneration, because those
    two must move together: an index built from a half-updated set of map files
    describes a state that never existed."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = RUNS_DIR / ".lock"
    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# --------------------------------------------------------------------------
# Trailer
# --------------------------------------------------------------------------


def render_trailer(run: dict) -> str:
    body = yaml.safe_dump({"wayfinder_run": run}, sort_keys=False, allow_unicode=True)
    return (
        "\n\n<details><summary>wayfinder run</summary>\n\n"
        f"{TRAILER_SENTINEL}\n```yaml\n{body.rstrip()}\n```\n\n</details>\n"
    )


def validate_run(run: dict) -> list[str]:
    """Return a list of schema problems. A trailer is written by an LLM into a
    free-text comment, so it can be well-formed YAML and still be nonsense
    (`friction: tooling` instead of a list). Anything downstream that iterates
    a field must know the field survived this."""
    problems = []
    if not isinstance(run.get("run_id"), str) or not run["run_id"]:
        problems.append("run_id missing or not a string")
    if run.get("mode") not in ("chart", "resolve", "reflect"):
        problems.append(f"mode {run.get('mode')!r} is not chart|resolve|reflect")
    if not isinstance(run.get("map"), int):
        problems.append("map missing or not an integer")
    if run.get("outcome") not in OUTCOMES:
        problems.append(f"outcome {run.get('outcome')!r} is not one of {OUTCOMES}")
    friction = run.get("friction")
    if friction is None:
        problems.append("friction key absent (use [] to mean 'the spec held')")
    elif not isinstance(friction, list):
        problems.append(f"friction is {type(friction).__name__}, must be a list")
    else:
        for i, item in enumerate(friction):
            if not isinstance(item, dict):
                problems.append(f"friction[{i}] is not a mapping")
            elif item.get("tag") not in FRICTION_TAGS:
                problems.append(f"friction[{i}] tag {item.get('tag')!r} is not a known tag")
    return problems


def extract_trailers(body: str) -> tuple[list[dict], list[dict]]:
    """-> (valid runs, malformed runs). Never raises on a bad trailer: a broken
    comment must not stop the harvest of every other run on the map."""
    good, bad = [], []
    for match in TRAILER_RE.finditer(body or ""):
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            bad.append({"problems": [f"unparseable YAML: {exc}"], "raw": match.group(1)[:400]})
            continue
        if not isinstance(data, dict):
            bad.append({"problems": ["trailer is not a mapping"], "raw": match.group(1)[:400]})
            continue
        run = data.get("wayfinder_run")
        if not isinstance(run, dict):
            bad.append({"problems": ["no wayfinder_run mapping"], "raw": match.group(1)[:400]})
            continue
        problems = validate_run(run)
        if problems:
            bad.append({"problems": problems, "run_id": run.get("run_id"), "raw": run})
        else:
            good.append(run)
    return good, bad


def build_run(
    *,
    mode: str,
    map_number: int,
    outcome: str,
    ticket: int | None = None,
    ticket_type: str | None = None,
    tickets_created: int = 0,
    fog: int = 0,
    friction: list[dict] | None = None,
) -> dict:
    run = {
        "run_id": uuid.uuid4().hex[:8],
        "spec_version": spec_version(),
        "mode": mode,
        "map": map_number,
        "date": today(),
        "outcome": outcome,
        "tickets_created": tickets_created,
        "fog_graduated": fog,
        "friction": friction or [],
    }
    if ticket is not None:
        run["ticket"] = ticket
        run["ticket_type"] = ticket_type or "unknown"
    return run


# --------------------------------------------------------------------------
# GitHub reads
# --------------------------------------------------------------------------


def issue(number: int, fields: str) -> dict:
    return gh_json("issue", "view", str(number), "--repo", REPO, "--json", fields)


def post_comment(number: int, body: str) -> None:
    """Always via --body-file. A resolution answer plus its trailer can exceed
    the OS argv limit, and `--body` would fail on exactly the long, valuable
    resolutions this exists to record."""
    import tempfile

    fd, path = tempfile.mkstemp(prefix="wayfinder-comment-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        gh("issue", "comment", str(number), "--repo", REPO, "--body-file", path)
    finally:
        os.unlink(path)


def wayfinder_labels(labels: list[dict]) -> list[str]:
    return [
        l["name"].split(":", 1)[1]
        for l in labels or []
        if l.get("name", "").startswith("wayfinder:")
    ]


def ticket_type_of(labels: list[dict]) -> str:
    kinds = [k for k in wayfinder_labels(labels) if k in TICKET_TYPES]
    return kinds[0] if kinds else "unknown"


LIST_LIMIT = 1000


def _list_issues(*extra: str) -> list[dict]:
    """`gh issue list` truncates at --limit with no signal. A silently short
    list makes a closed child invisible, so no GAP is reported and the telemetry
    quietly under-counts. Saturation is therefore a hard error, not a warning."""
    data = gh_json(
        "issue", "list", "--repo", REPO, "--state", "all",
        "--limit", str(LIST_LIMIT), *extra,
    ) or []
    if len(data) >= LIST_LIMIT:
        raise WayfinderError(
            f"gh issue list returned {len(data)} issues, at the --limit of {LIST_LIMIT}. "
            "The list is probably truncated, so any traversal over it is incomplete. "
            "Raise LIST_LIMIT in wayfinder_runs.py or paginate before trusting a harvest."
        )
    return data


def children_of(map_number: int) -> list[dict]:
    data = _list_issues("--json", "number,title,state,labels,parent,closedAt")
    return [
        i for i in data
        if (i.get("parent") or {}).get("number") == map_number
    ]


# --------------------------------------------------------------------------
# Local store — harvest is the only writer
# --------------------------------------------------------------------------


def map_file(map_number: int) -> Path:
    return RUNS_DIR / f"map-{map_number}.yaml"


def load_map_log(map_number: int) -> dict:
    path = map_file(map_number)
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


def load_all_logs() -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    logs = []
    for path in sorted(RUNS_DIR.glob("map-*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if data:
            logs.append(data)
    return logs


def recurring(runs: list[dict], extra_friction: list[dict] | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in runs:
        for f in run.get("friction") or []:
            tag = f.get("tag")
            if tag:
                counts[tag] = counts.get(tag, 0) + 1
    for f in extra_friction or []:
        tag = f.get("tag")
        if tag:
            counts[tag] = counts.get(tag, 0) + 1
    return {t: c for t, c in counts.items() if c >= RECURRING_THRESHOLD}


def print_recurring(map_number: int, extra: list[dict] | None = None) -> None:
    """Cross-map, not just this map: a spec defect that bites two maps is the
    strongest signal there is."""
    all_runs = [r for log in load_all_logs() for r in (log.get("runs") or [])]
    hits = recurring(all_runs, extra)
    if not hits:
        return
    print("\nRECURRING friction (>= %d across all harvested maps):" % RECURRING_THRESHOLD)
    for tag, count in sorted(hits.items(), key=lambda kv: -kv[1]):
        print(f"  {tag} x{count} — {FRICTION_TAGS[tag]}")
    print(
        "  This is the trigger to resolve the reflection ticket now "
        f"(`wayfinder_runs.py reflect --map {map_number} --interim`), not at the end of the map."
    )


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------


def cmd_check(_args) -> int:
    version = spec_version()
    top = changelog_top()
    problems = []
    if version == "unknown":
        problems.append("SKILL.md frontmatter has no `version:`")
    elif not re.match(r"^\d+\.\d+\.\d+$", version):
        problems.append(f"SKILL.md version '{version}' is not semver")
    if top is None:
        problems.append("CHANGELOG.md missing or has no `## X.Y.Z` entry")
    elif version != "unknown" and top != version:
        problems.append(
            f"VERSION DRIFT: SKILL.md version={version} but CHANGELOG top={top}. "
            "A spec change bumped one and not the other, so every run recorded "
            "since then is attributed to the wrong spec."
        )
    # Trailer schema self-test: prove render -> extract -> validate round-trips,
    # and that a malformed trailer is rejected rather than silently ingested.
    sample = build_run(
        mode="resolve", map_number=1, outcome="resolved", ticket=2,
        ticket_type="grilling", friction=[{"tag": "tooling", "note": "n"}],
    )
    good, bad = extract_trailers("prefix\n```yaml\ndecoy: true\n```\n" + render_trailer(sample))
    if len(good) != 1 or bad or good[0]["run_id"] != sample["run_id"]:
        problems.append(f"trailer round-trip broken: {len(good)} good, {len(bad)} bad")
    # Otherwise-complete, so friction is the ONLY defect. A fixture missing
    # several fields would be rejected for any of them and would prove nothing
    # about the friction check specifically.
    scalar = dict(sample, friction="tooling")
    _, rejected = extract_trailers(
        f"{TRAILER_SENTINEL}\n```yaml\n"
        + yaml.safe_dump({"wayfinder_run": scalar}, sort_keys=False).rstrip()
        + "\n```"
    )
    if not rejected:
        problems.append("a trailer with a scalar `friction` was accepted; validation is not firing")
    elif not any("friction" in p for p in rejected[0]["problems"]):
        problems.append(
            f"the scalar-friction trailer was rejected, but for the wrong reason: "
            f"{rejected[0]['problems']}"
        )

    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        return 1
    print(f"  OK  wayfinder spec version {version}, CHANGELOG top matches; "
          "trailer round-trip and schema rejection both verified")
    return 0


def warn_on_drift() -> None:
    if cmd_check(None) != 0:
        print("  ^ fix the drift before trusting spec_version on any run above.\n")


# --------------------------------------------------------------------------
# chart
# --------------------------------------------------------------------------

REFLECTION_BODY = """## Question

How did the **wayfinder skill itself** perform on this map, and what should change in its spec?

This is not a decision on the route. It is the retro on the vehicle. Resolve it with a human,
never alone: the agent cannot report on friction the human felt.

**Before the conversation**, run:

```
python3 ~/.claude-shared-config/skills/wayfinder/tools/wayfinder_runs.py reflect --map {map}
```

That prints every run on this map, the friction grouped by tag, any untraced runs (GAPS), and
the spec versions the map was worked under. Bring that to the conversation, do not reconstruct
it from memory.

**The resolution must produce**, or explicitly record that it produces nothing:

1. A concrete diff to `skills/wayfinder/SKILL.md`.
2. A `CHANGELOG.md` entry with a bumped `version:`.

Anything learned that is NOT about the wayfinder spec goes to `/gab-operationalize`, not here.
"""


def cmd_chart(args) -> int:
    friction = parse_friction(args.friction)
    map_number = args.map

    meta = issue(map_number, "title,labels,comments")
    if "wayfinder:map" not in [l["name"] for l in meta.get("labels", [])]:
        raise WayfinderError(
            f"issue #{map_number} is not labelled wayfinder:map — refusing to post a chart trailer"
        )

    already = []
    for comment in meta.get("comments", []):
        good, bad = extract_trailers(comment.get("body", ""))
        already.extend([r for r in good if r.get("mode") == "chart"] + bad)

    run = build_run(
        mode="chart",
        map_number=map_number,
        outcome="charted",
        tickets_created=args.tickets_created,
        fog=args.fog_patches,
        friction=friction,
    )
    comment = (
        f"**Charted.** {args.tickets_created} ticket(s) created, "
        f"{args.fog_patches} fog patch(es) recorded in *Not yet specified*."
        + render_trailer(run)
    )

    if args.dry_run:
        if already:
            print(f"  (a chart trailer already exists on #{map_number}; a real run would skip it)")
        print(comment)
        return 0

    # Reflection ticket FIRST, trailer second. If issue creation fails, a retry
    # finds no trailer and repeats cleanly. The reverse order would post a
    # second chart trailer with a fresh run_id on every retry.
    if not args.no_reflection:
        existing = [
            c for c in children_of(map_number)
            if ticket_type_of(c.get("labels")) == "reflection"
        ]
        if existing:
            print(f"  reflection ticket already exists: #{existing[0]['number']}")
        else:
            gh("label", "create", "wayfinder:reflection", "--repo", REPO,
               "--description", "wayfinder reflection ticket", "--color", "c5def5",
               check=False)
            title = f"Reflection: how did the wayfinder perform on {meta['title']}?"
            body = REFLECTION_BODY.replace("{map}", str(map_number))
            url = gh(
                "issue", "create", "--repo", REPO, "--parent", str(map_number),
                "--label", "wayfinder:reflection", "--title", title, "--body", body,
            ).strip()
            print(f"  reflection ticket planted: {url}")
    else:
        print("  --no-reflection: this map will report `missing_reflection` on every harvest.")

    if already and not args.force:
        print(f"  #{map_number} already carries a chart trailer — not posting a second one.")
        print("  (pass --force to post a superseding one, e.g. after a re-chart)")
        print_recurring(map_number, [])
        return 0

    post_comment(map_number, comment)
    print(f"  chart trailer posted on #{map_number} (run {run['run_id']})")
    print_recurring(map_number, friction)
    return 0


# --------------------------------------------------------------------------
# resolve
# --------------------------------------------------------------------------


def cmd_resolve(args) -> int:
    friction = parse_friction(args.friction)
    number = args.ticket

    data = issue(number, "title,state,labels,comments,parent,assignees")
    state = data.get("state", "").upper()
    kind = ticket_type_of(data.get("labels"))
    parent = (data.get("parent") or {}).get("number")
    map_number = args.map or parent
    if map_number is None:
        raise WayfinderError(
            f"#{number} has no parent map and --map was not given"
        )

    # `resolve` posts and closes. A mistyped number would resolve someone else's
    # issue, so prove this is a wayfinder ticket before touching it.
    if not wayfinder_labels(data.get("labels")):
        raise WayfinderError(
            f"#{number} \"{data['title']}\" carries no wayfinder: label — refusing to "
            "resolve it. Check the issue number."
        )

    # The spec warns that several sessions work one map at once. An assignee is
    # the claim, so an assignee who is not you is a live collision, not a detail.
    me = (gh_json("api", "user", "--jq", "{login: .login}") or {}).get("login")
    others = [
        a["login"] for a in data.get("assignees", []) or []
        if a.get("login") and a["login"] != me
    ]
    if others and not args.force:
        raise WayfinderError(
            f"#{number} is claimed by {', '.join(others)}, not you ({me}). Another "
            "session is on this ticket. Pick a different frontier ticket, or pass "
            "--force if you know the claim is stale."
        )

    # A malformed trailer still proves a comment was posted, so it counts for
    # the resume decision. Otherwise a retry would post a duplicate answer.
    existing = []
    for comment in data.get("comments", []):
        good, bad = extract_trailers(comment.get("body", ""))
        existing.extend(good + bad)

    # Resume, do not force. A retry after a failed close must converge on the
    # right state instead of posting a second comment. The effective outcome of
    # a run is GitHub's issue state, never the trailer's stated intent.
    if existing and not args.force:
        prior = existing[-1]
        print(f"  #{number} already carries a run trailer (run {prior.get('run_id')})")
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

    if not args.body_file:
        raise WayfinderError("--body-file is required to resolve a ticket for the first time")
    body_path = Path(args.body_file).expanduser()
    if not body_path.exists():
        raise WayfinderError(f"--body-file {body_path} does not exist")

    mode = "reflect" if kind == "reflection" else "resolve"
    run = build_run(
        mode=mode,
        map_number=map_number,
        outcome=args.outcome,
        ticket=number,
        ticket_type=kind,
        tickets_created=args.tickets_created,
        fog=args.fog_graduated,
        friction=friction,
    )
    comment = body_path.read_text(encoding="utf-8").rstrip() + render_trailer(run)

    if args.dry_run:
        print(comment)
        return 0

    post_comment(number, comment)
    print(f"  resolution comment posted on #{number} (run {run['run_id']}, mode {mode})")
    try:
        gh("issue", "close", str(number), "--repo", REPO)
        print(f"  #{number} closed")
    except WayfinderError as exc:
        # Honest partial-failure report. The trailer is already on GitHub, so a
        # re-run takes the resume path above and only closes.
        print(f"  CLOSE FAILED: {exc}", file=sys.stderr)
        print(
            f"  The trailer IS posted. Re-run the same command to resume "
            f"(it will close #{number} without a duplicate comment).",
            file=sys.stderr,
        )
        return 1

    print("\n  Append to the map's `## Decisions so far` (edit the gist to taste):")
    print(f"  - [{data['title']}](https://github.com/{REPO}/issues/{number}): <one-line gist>")
    print_recurring(map_number, friction)
    return 0


# --------------------------------------------------------------------------
# harvest — the only writer
# --------------------------------------------------------------------------


def harvest_map(map_number: int) -> dict:
    meta = issue(map_number, "title,labels,state")
    kids = children_of(map_number)

    runs: list[dict] = []
    gaps: list[dict] = []
    malformed: list[dict] = []
    feedback: list[dict] = []
    seen: set[str] = set()
    pre_telemetry = 0

    def scan(number: int, state: str) -> int:
        found = 0
        detail = issue(number, "comments")
        for comment in detail.get("comments", []):
            body = comment.get("body", "") or ""
            good, bad = extract_trailers(body)
            for problem in bad:
                # A trailer that exists but does not parse is NOT a gap: the
                # session did trace itself, badly. Reported separately so it is
                # fixable, and never fed to code that iterates its fields.
                malformed.append({
                    "issue": number,
                    "url": comment.get("url"),
                    "problems": problem["problems"],
                })
                found += 1
            for run in good:
                rid = str(run.get("run_id"))
                if rid in seen:
                    continue  # a retry that double-posted collapses to one run
                seen.add(rid)
                run = dict(run)
                run["issue_state"] = state      # GitHub's truth, not the trailer's intent
                run["comment_url"] = comment.get("url")
                runs.append(run)
                found += 1
            first = body.strip().splitlines()[0] if body.strip() else ""
            if FEEDBACK_RE.match(first):
                feedback.append({
                    "issue": number,
                    "author": (comment.get("author") or {}).get("login"),
                    "body": body.strip(),
                    "url": comment.get("url"),
                })
        return found

    scan(map_number, (meta.get("state") or "OPEN").upper())

    for kid in kids:
        kind = ticket_type_of(kid.get("labels"))
        found = scan(kid["number"], kid["state"].upper())
        if kid["state"].upper() == "CLOSED" and found == 0:
            closed_at = (kid.get("closedAt") or "")[:10]
            if closed_at and closed_at < TELEMETRY_EPOCH:
                pre_telemetry += 1
                continue
            gaps.append({
                "issue": kid["number"],
                "title": kid["title"],
                "type": kind,
                "closed_at": closed_at or "unknown",
                "reason": "closed with no run trailer — this run was never traced",
            })

    has_reflection = any(ticket_type_of(k.get("labels")) == "reflection" for k in kids)

    return {
        "map": map_number,
        "map_title": meta["title"],
        "map_state": (meta.get("state") or "OPEN").upper(),
        "harvested": now_iso(),
        "telemetry_epoch": TELEMETRY_EPOCH,
        "runs": runs,
        "gaps": gaps,
        "malformed_trailers": malformed,
        "missing_reflection": not has_reflection,
        "pre_telemetry_closures": pre_telemetry,
        "feedback": feedback,
    }


def regenerate_index() -> None:
    logs = load_all_logs()
    rows = []
    for log in logs:
        for run in log.get("runs") or []:
            if not isinstance(run, dict):
                continue
            # Defensive: a hand-edited map-N.yaml can hold a shape harvest would
            # have rejected. The index must never be the thing that crashes.
            friction = run.get("friction")
            tags = sorted({
                f.get("tag", "?") for f in friction if isinstance(f, dict)
            }) if isinstance(friction, list) else ["?malformed"]
            rows.append((
                str(run.get("date", "?")),
                str(log.get("map", "?")),
                str(run.get("mode", "?")),
                str(run.get("ticket", "-")),
                str(run.get("ticket_type", "-")),
                str(run.get("outcome", "?")),
                str(run.get("spec_version", "?")),
                ", ".join(tags) or "-",
            ))
    rows.sort(key=lambda r: (r[0], r[1]))

    total_gaps = sum(len(log.get("gaps") or []) for log in logs)
    no_reflection = [str(log.get("map")) for log in logs if log.get("missing_reflection")]
    lines = [
        "# wayfinder — Run Telemetry Index",
        "",
        "Generated by `tools/wayfinder_runs.py harvest`. Do not hand-edit: the next",
        "harvest overwrites it. GitHub comments are the source of truth; this is the",
        "cross-map view over them.",
        "",
        f"Maps harvested: {len(logs)} · runs: {len(rows)} · untraced runs (GAPS): {total_gaps}"
        + (f" · maps with no reflection ticket: {', '.join(no_reflection)}" if no_reflection else ""),
        "",
        "| Date | Map | Mode | Ticket | Type | Outcome | Spec | Friction tags |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    lines.append("")
    atomic_write(RUNS_DIR / "INDEX.md", "\n".join(lines))


def cmd_harvest(args) -> int:
    if args.all:
        # Through _list_issues, so a truncated map list is a hard error too. A
        # silently short list here would leave a whole map stale in runs/ while
        # still appearing in the regenerated index.
        maps = [i["number"] for i in _list_issues("--label", "wayfinder:map", "--json", "number")]
    else:
        maps = [args.map]

    # Fetch everything BEFORE taking the lock: a harvest of a large map is many
    # API calls, and holding the cache lock across them would serialise every
    # concurrent session on the network.
    logs = [harvest_map(number) for number in maps]

    total_gaps = 0
    with runs_lock():
        for log in logs:
            atomic_write(
                map_file(log["map"]),
                yaml.safe_dump(log, sort_keys=False, allow_unicode=True),
            )
        regenerate_index()

    for log in logs:
        number = log["map"]
        gaps = log["gaps"]
        total_gaps += len(gaps)
        print(f"  map #{number} — {len(log['runs'])} run(s), {len(gaps)} gap(s), "
              f"{len(log['malformed_trailers'])} malformed, "
              f"{len(log['feedback'])} feedback comment(s), "
              f"{log['pre_telemetry_closures']} pre-telemetry closure(s) "
              f"-> {map_file(number)}")
        for gap in gaps:
            print(f"      GAP  #{gap['issue']} ({gap['type']}) {gap['title']}")
        for bad in log["malformed_trailers"]:
            print(f"      MALFORMED  #{bad['issue']}: {'; '.join(bad['problems'])}")
        if log["missing_reflection"]:
            print(f"      NO REFLECTION TICKET on map #{number} — this map has no terminal "
                  f"retro, so nothing on GitHub prompts anyone to run one. Plant it with "
                  f"`chart --map {number}` (it skips the trailer if one already exists).")

    print(f"  index regenerated -> {RUNS_DIR / 'INDEX.md'}")
    if total_gaps:
        print(
            f"\n  {total_gaps} untraced run(s). A GAP is not fixable after the fact: the"
            "\n  session that closed the ticket is gone. It counts as evidence that the"
            "\n  traced path was skipped, which is itself a `process` friction worth a"
            "\n  friction entry on the next run."
        )
    warn_on_drift()
    return 0


# --------------------------------------------------------------------------
# reflect
# --------------------------------------------------------------------------


def cmd_reflect(args) -> int:
    map_number = args.map
    kids = children_of(map_number)
    open_route = [
        k for k in kids
        if k["state"].upper() == "OPEN" and ticket_type_of(k.get("labels")) != "reflection"
    ]
    if open_route and not args.interim:
        print(f"  REFUSED: {len(open_route)} route ticket(s) are still open on map #{map_number}.")
        for k in open_route[:10]:
            print(f"      #{k['number']}  {k['title']}")
        if len(open_route) > 10:
            print(f"      ... and {len(open_route) - 10} more")
        print(
            "\n  Reflection is the map's terminal act. Run it early only when RECURRING"
            "\n  friction says the spec is actively costing you: `reflect --map"
            f" {map_number} --interim`."
            "\n  Reflection is repeatable — an interim retro does not consume the map's final one."
        )
        return 1

    log = harvest_map(map_number)
    with runs_lock():
        atomic_write(map_file(map_number),
                     yaml.safe_dump(log, sort_keys=False, allow_unicode=True))
        regenerate_index()

    runs = log["runs"]
    print(f"\n=== Reflection brief — map #{map_number}: {log['map_title']} ===")
    if args.interim:
        print(f"    INTERIM: {len(open_route)} route ticket(s) still open.\n")

    print(f"\nRuns traced: {len(runs)}")
    by_mode: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    versions: dict[str, int] = {}
    for run in runs:
        by_mode[run.get("mode", "?")] = by_mode.get(run.get("mode", "?"), 0) + 1
        by_outcome[run.get("outcome", "?")] = by_outcome.get(run.get("outcome", "?"), 0) + 1
        versions[str(run.get("spec_version", "?"))] = versions.get(str(run.get("spec_version", "?")), 0) + 1
    print("  by mode:    " + ", ".join(f"{k}={v}" for k, v in sorted(by_mode.items())))
    print("  by outcome: " + ", ".join(f"{k}={v}" for k, v in sorted(by_outcome.items())))
    print("  spec versions worked under: "
          + ", ".join(f"{k} ({v} run(s))" for k, v in sorted(versions.items())))

    print("\nFriction, grouped by tag (the candidate spec changes):")
    grouped: dict[str, list[str]] = {}
    for run in runs:
        for f in run.get("friction") or []:
            grouped.setdefault(f.get("tag", "?"), []).append(
                f"#{run.get('ticket', run.get('map'))}: {f.get('note', '')}"
            )
    if not grouped:
        print("  none recorded. Either the spec held, or the runs were not honest. Ask the human which.")
    for tag, notes in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        flag = "  <-- RECURRING" if len(notes) >= RECURRING_THRESHOLD else ""
        print(f"\n  [{tag}] x{len(notes)}{flag} — {FRICTION_TAGS.get(tag, '?')}")
        for note in notes:
            print(f"      - {note}")

    if log["gaps"]:
        print(f"\nUntraced runs (GAPS): {len(log['gaps'])} — these sessions left no evidence.")
        for gap in log["gaps"]:
            print(f"      #{gap['issue']} ({gap['type']}) {gap['title']}")
    if log["malformed_trailers"]:
        print(f"\nMalformed trailers: {len(log['malformed_trailers'])} — these sessions traced "
              "themselves but the trailer does not parse, so the run is not counted above.")
        for bad in log["malformed_trailers"]:
            print(f"      #{bad['issue']}: {'; '.join(bad['problems'])}")
    if log["missing_reflection"]:
        print("\nThis map has NO reflection ticket. You are running the retro anyway, which is "
              "fine, but nothing on GitHub was prompting anyone to.")
    if log["pre_telemetry_closures"]:
        print(f"\n{log['pre_telemetry_closures']} ticket(s) closed before telemetry existed "
              f"(before {TELEMETRY_EPOCH}). Not gaps, and not recoverable — this map's early "
              "runs are simply not in evidence.")

    if log["feedback"]:
        print(f"\nHuman feedback comments: {len(log['feedback'])}")
        for fb in log["feedback"]:
            print(f"      #{fb['issue']} @{fb['author']}: {fb['body'][:200]}")

    print(
        "\nNow have the conversation. The resolution must produce a concrete SKILL.md diff"
        "\nplus a CHANGELOG entry with a bumped version, or an explicit record that it"
        "\nproduces neither. Anything not about the wayfinder spec goes to /gab-operationalize."
    )
    warn_on_drift()
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wayfinder_runs.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    def add_friction(sp):
        sp.add_argument(
            "--friction", action="append", metavar="TAG:NOTE",
            help="repeatable. TAG is one of: " + ", ".join(FRICTION_TAGS),
        )
        sp.add_argument("--dry-run", action="store_true",
                        help="print what would be posted, touch nothing")

    c = sub.add_parser("chart", help="post the charting trailer + plant the reflection ticket")
    c.add_argument("--map", type=int, required=True)
    c.add_argument("--tickets-created", type=int, default=0)
    c.add_argument("--fog-patches", type=int, default=0)
    c.add_argument("--no-reflection", action="store_true",
                   help="skip planting the reflection ticket; the map then reports "
                        "missing_reflection on every harvest")
    c.add_argument("--force", action="store_true",
                   help="post a chart trailer even though one already exists (a re-chart)")
    add_friction(c)
    c.set_defaults(func=cmd_chart)

    r = sub.add_parser("resolve", help="post the resolution comment + trailer, then close")
    r.add_argument("--ticket", type=int, required=True)
    r.add_argument("--map", type=int, help="defaults to the ticket's parent")
    r.add_argument("--body-file", help="the resolution answer, markdown")
    r.add_argument("--outcome", choices=OUTCOMES, default="resolved")
    r.add_argument("--tickets-created", type=int, default=0)
    r.add_argument("--fog-graduated", type=int, default=0)
    r.add_argument("--force", action="store_true",
                   help="post a second, superseding trailer (default is resume, not duplicate)")
    add_friction(r)
    r.set_defaults(func=cmd_resolve)

    f = sub.add_parser(
        "reflect",
        help="retro brief for the reflection conversation (reads GitHub, refreshes the runs/ cache)",
    )
    f.add_argument("--map", type=int, required=True)
    f.add_argument("--interim", action="store_true",
                   help="run before the map is finished (RECURRING friction says the spec is costing you)")
    f.set_defaults(func=cmd_reflect)

    h = sub.add_parser("harvest", help="rebuild runs/ from GitHub; report untraced runs")
    g = h.add_mutually_exclusive_group(required=True)
    g.add_argument("--map", type=int)
    g.add_argument("--all", action="store_true")
    h.set_defaults(func=cmd_harvest)

    k = sub.add_parser("check", help="SKILL.md version <-> CHANGELOG top coupling")
    k.set_defaults(func=cmd_check)

    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    try:
        return args.func(args)
    except WayfinderError as exc:
        print(f"wayfinder_runs.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
