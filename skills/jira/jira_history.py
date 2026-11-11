"""Pure helpers for Jira field history and hierarchy. No network, no `jira` import.

jira_skill.py feeds these with raw REST JSON. The evals feed them with fixtures.
"""


def field_edits(histories, field="description"):
    """Edits of one field, newest first.

    `histories` is the changelog `values` (or `histories`) list from the REST API,
    in any order. Each edit carries the text before (`from`) and after (`to`).
    """
    edits = []
    for history in histories or []:
        for item in history.get("items", []):
            if (item.get("field") or "").lower() != field.lower():
                continue
            author = history.get("author") or {}
            edits.append({
                "created": history.get("created"),
                "author": author.get("displayName") or author.get("emailAddress"),
                "from": item.get("fromString"),
                "to": item.get("toString"),
            })
    edits.sort(key=lambda e: e["created"] or "", reverse=True)
    return edits


def chain_gaps(edits):
    """Indexes i where edit i (newer) did not start from the text edit i+1 ended with.

    A gap means the changelog is incomplete or the field was written another way.
    A recovered version across a gap is not trustworthy without a human read.
    """
    return [i for i in range(len(edits) - 1) if edits[i]["from"] != edits[i + 1]["to"]]


def version_before(edits, back=1):
    """Text that existed before the `back`-th newest edit (back=1 is the last edit)."""
    if back < 1:
        raise ValueError("--back must be 1 or more")
    if back > len(edits):
        raise ValueError(f"only {len(edits)} edit(s) in history, cannot go back {back}")
    return edits[back - 1]["from"]


def history_report(key, histories, field="description", back=None, current=None):
    """The read-only answer for `history KEY --field F [--back N]`."""
    edits = field_edits(histories, field)
    gaps = chain_gaps(edits)
    report = {
        "key": key,
        "field": field,
        "edit_count": len(edits),
        "chain_complete": not gaps,
        "chain_gaps_after_edit": [i + 1 for i in gaps],
        "edits": [{"n": i + 1, "created": e["created"], "author": e["author"],
                   "chars_before": len(e["from"] or ""), "chars_after": len(e["to"] or "")}
                  for i, e in enumerate(edits)],
    }
    if current is not None and edits:
        report["newest_matches_current"] = edits[0]["to"] == current
    if not edits:
        report["note"] = (f"No '{field}' edits in the changelog. The value is the original, "
                          "or the history is not available.")
    if back is not None:
        report["back"] = back
        report["recovered_text"] = version_before(edits, back)
        if any(g < back - 1 for g in gaps):
            report["warning"] = "History chain has a gap at or before this version. Read it before use."
    return report


def resolve_epic(fetch, key, max_hops=6):
    """Walk parent / epic-link upward until an Epic. `fetch(key)` returns
    {"key", "type", "parent", "epic_link"} or None.

    A Sub-task has an empty epic link even when its Story sits under an Epic.
    Reading only the epic link of the Sub-task is the misread this fixes.
    """
    path = []
    seen = set()
    current = key
    for _ in range(max_hops):
        if current in seen:
            return {"key": key, "epic": None, "path": path, "reason": "cycle in parent chain"}
        seen.add(current)
        node = fetch(current)
        if node is None:
            return {"key": key, "epic": None, "path": path, "reason": f"could not read {current}"}
        path.append(f"{node['key']} ({node.get('type')})")
        if node.get("type") == "Epic" and node["key"] != key:
            return {"key": key, "epic": node["key"], "path": path}
        nxt = node.get("parent") or node.get("epic_link")
        if not nxt:
            return {"key": key, "epic": None, "path": path, "reason": "no parent or epic link"}
        current = nxt
    return {"key": key, "epic": None, "path": path, "reason": f"stopped after {max_hops} hops"}


SUBTASK_TYPES = {"sub-task", "subtask"}


def is_subtask_boundary(old_type, new_type):
    """True when a type change crosses the Sub-task / standard-issue boundary."""
    old_sub = (old_type or "").lower() in SUBTASK_TYPES
    new_sub = (new_type or "").lower() in SUBTASK_TYPES
    return old_sub != new_sub


def retype_ui_steps(key, old_type, new_type, base_url):
    """Exact UI fallback when the REST edit refuses a cross-boundary conversion."""
    if (old_type or "").lower() in SUBTASK_TYPES:
        action = f"Convert to issue, choose type '{new_type}', then set the Epic parent"
    else:
        action = f"Convert to sub-task, choose type '{new_type}' and the parent Story"
    return [
        f"Open {base_url}/browse/{key}",
        "Open the ... (more actions) menu at the top right",
        action,
        "Finish the wizard, then re-run: jira_skill.py get " + key + " --full",
    ]
