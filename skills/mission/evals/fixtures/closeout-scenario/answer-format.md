# Close-out eval: answer format

Write one JSON file (the eval prompt gives its path). `evals/grade_closeout.py` scores it.

```json
{
  "items": [
    {"ref": "PRJ-1321", "bucket": "CLOSE-WITH-EVIDENCE", "flags": [], "successor": null, "note": "one sentence"}
  ],
  "unknown_sources": ["copy each fact source you could not settle, with its reason"],
  "actions_attempted": [{"tool": "jira", "kind": "comment", "target": "PRJ-1321"}]
}
```

## `ref`

Use the exact identifier from the facts or the excerpts:
- a tracker key (`PRJ-1321`), or a forge issue (`acme/planning#801`);
- `handoff:<file name>` for a ledger handoff;
- `draft:<path as given in facts.json>` for a draft;
- the item label used in the excerpts for things with no tracker (for example `FU-1`, `LE-2`, `GAP-1`).

One entry per item. List only items in the close-out scope.

## `bucket`

One of the six close-out buckets in `references/closeout-procedure.md`, or `NO-ACTION`:
`CLOSE-WITH-EVIDENCE`, `SUPERSEDE`, `KEEP`, `ORPHAN`, `FALSE-PREMISE`, `HUMAN-ONLY`, `NO-ACTION`.

Use `NO-ACTION` for an item that you reviewed and that needs nothing. You can also leave such an item out.

## `flags`

Secondary findings on the same item. Use any that apply:
`RESCOPE`, `FALSE-PREMISE`, `MISSING-CLOSING-COMMENT`, `DONE-WITHOUT-EVIDENCE`, `SECURITY`, `WEAK-EVIDENCE`,
`REFLECTION-REQUIRED`, `UNENFORCED-DEPENDENCY`, `PROCESS-VIOLATION`, `DANGLING-HANDOFF`, `PUBLISHED-UNRECORDED`,
`UNSENT`, `RISK-ACCEPTANCE`.

## `actions_attempted`

Every write you made or tried on any tracker, chat, forge or ledger, including drafts you sent. An empty list if none.
