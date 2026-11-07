"""Shared helpers for the skill-proposal triage scripts.

Every script takes a run directory. All inputs and outputs live in that run directory,
so a crashed session can resume from disk. Layout (each file is optional until its phase):

    <run>/STATE.json                 phase, status, done batches, skill counts
    <run>/inventory.tsv              P1: date, name, file, trigger snippet (newest first)
    <run>/batches/batch-aa.txt       P1: one proposal file name per line
    <run>/brief.md                   P1: reviewer rubric rendered from the template
    <run>/groups.json                P1/P2: {"<group name>": ["<proposal name>", ...]}
    <run>/results/batch-aa.json      P2: Claude first pass, one JSON array per batch
    <run>/codex/out-batch-aa.json    P3: Codex second pass (JSON array, may have prose around it)
    <run>/codex/out-groups.json      P4: Codex review of the groups
    <run>/codex/out-overall.md       P4: Codex review of the whole triage
    <run>/final-verdicts.json        P5: Codex verdict wins on conflict, human decisions applied
    <run>/decisions.json             P5: exported from the HTML page by the human
    <run>/triage.html                P5: the review page
"""
import datetime
import glob
import json
import os
import re

PHASES = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
PHASE_NAMES = {
    "P0": "Preflight", "P1": "Inventory and split", "P2": "Claude pass", "P3": "Codex batch pass",
    "P4": "Codex groups and overall", "P5": "Render and decide", "P6": "Apply",
    "P7": "Manifest and sweep", "P8": "Merge and report",
}
VERDICT_CLASSES = ["BUILD", "UPDATE", "MERGE", "SOP", "ARCHIVE", "HOLD"]
DEFAULT_PROPOSALS = os.path.expanduser("~/.claude/skill-proposals")
PROPOSAL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+\.md$")


def proposal_name(fn):
    return fn[11:-3] if PROPOSAL_RE.match(fn) else fn[:-3]


def read_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def extract_json(text, opener="["):
    """Parse JSON from model output that may carry prose or a code fence around it."""
    closer = "]" if opener == "[" else "}"
    text = text.strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except ValueError:
            pass
    start, end = text.find(opener), text.rfind(closer)
    if start < 0 or end <= start:
        raise ValueError(f"no JSON {opener}...{closer} block found")
    return json.loads(text[start:end + 1])


def load_state(run):
    return read_json(os.path.join(run, "STATE.json"), {}) or {}


def save_state(run, **changes):
    state = load_state(run)
    state.update(changes)
    state["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    write_json(os.path.join(run, "STATE.json"), state)
    return state


def load_claude(run):
    out = {}
    for f in sorted(glob.glob(os.path.join(run, "results", "*.json"))):
        for o in read_json(f, []) or []:
            if isinstance(o, dict) and o.get("file"):
                out[o["file"]] = o
    return out


def load_codex(run, problems=None):
    out = {}
    for f in sorted(glob.glob(os.path.join(run, "codex", "out-batch-*.json"))):
        try:
            with open(f) as fh:
                data = extract_json(fh.read(), "[")
        except (OSError, ValueError) as ex:
            if problems is not None:
                problems.append(f"codex parse failed: {os.path.basename(f)}: {ex}")
            continue
        for o in data:
            if isinstance(o, dict) and o.get("file"):
                out[o["file"]] = o
    return out


def load_groups(run):
    for p in (os.path.join(run, "groups.json"), os.path.join(run, "codex", "groups.json")):
        g = read_json(p)
        if isinstance(g, dict):
            return g
    return {}


def load_codex_groups(run):
    p = os.path.join(run, "codex", "out-groups.json")
    try:
        with open(p) as fh:
            return extract_json(fh.read(), "{")
    except (OSError, ValueError):
        return {}


def batch_files(run):
    """Return {batch_id: [file, ...]} from batches/*.txt, or the flat batch-* layout."""
    out = {}
    paths = sorted(glob.glob(os.path.join(run, "batches", "batch-*.txt")))
    if not paths:
        paths = sorted(p for p in glob.glob(os.path.join(run, "batch-*")) if os.path.isfile(p)
                       and "." not in os.path.basename(p))
    for p in paths:
        bid = os.path.basename(p).split(".")[0]
        with open(p) as fh:
            out[bid] = [ln.strip() for ln in fh if ln.strip()]
    return out


def verdict_class(v):
    return (v or "pending").split(":")[0].strip().upper() or "PENDING"


def count_installed_skills(roots=None):
    """Count user skills the way the drift alarm does: ~/.claude/skills/*/SKILL.md, _archive excluded.
    Plugin skills are a separate namespace; pass extra roots to include them."""
    roots = roots or [os.path.expanduser("~/.claude/skills")]
    seen = set()
    for r in roots:
        for skill in glob.glob(os.path.join(r, "*", "SKILL.md")):
            d = os.path.dirname(skill)
            if "/_archive" in d:
                continue
            seen.add(os.path.realpath(d))
    return len(seen)
