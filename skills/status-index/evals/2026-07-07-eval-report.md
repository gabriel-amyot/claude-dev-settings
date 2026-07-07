# status_index.py — eval report (2026-07-07)

Target: `~/.claude-shared-config/skills/status-index/status_index.py` (generates
STATUS_SNAPSHOT.yaml from `jira/ac/index.yaml`, weighted by acceptance-criteria points).

## Results

`run_status_evals.py` — **7/7 passing**.

Run: `python3 ~/.claude-shared-config/skills/status-index/evals/run_status_evals.py`
(`-v` for full dry-run YAML per case).

Coverage: 2/5 ACs done (40.0%), 0/5 (0.0%), 5/5 (100.0%), missing `jira/ac/index.yaml` entirely
(defaults, no crash), malformed YAML syntax (caught + warned to stderr, no crash, falls back to
defaults), a nonexistent ticket path (exit 1, clean error), and a 2-child epic with unequal story
points to pin the weighted-completion formula (`sum(completion_i * sp_i) / sum(sp_i)`).

## Pinned/surprising behaviors (report, not fixed)

1. **Ac-file path differs from the dispatch brief's assumption.** The brief said "jira/ac.yaml";
   the actual path the script reads is `jira/ac/index.yaml` (see `read_ac_yaml()`). The eval
   fixtures use the real path — a suite built against `jira/ac.yaml` would have silently tested
   the "file missing" fallback path for every case, defeating the purpose of the suite. Flagging
   in case anyone else built assumptions on the shorthand.
2. **`parent` field is the literal immediate-parent directory name, not the true epic/no-epic
   semantics.** For a leaf ticket at `tickets/KTP/no-epic/KTP-9001/`, the snapshot's `parent:`
   field is set to the string `"no-epic"` (not `null`, not the epic key). This is because
   `index_leaf_ticket`'s caller in `main()` does
   `parent_id = ticket_path.parent.name if ticket_path.parent.name != 'tickets' else None`
   — a single-level assumption that doesn't match this project's real two-level bucketing
   (`tickets/{PREFIX}/{EPIC-or-no-epic}/{TICKET-ID}/`, per this repo's CLAUDE.md schema). Every
   standalone (no-epic) leaf ticket indexed directly via the CLI gets `parent: no-epic` in its
   snapshot, which is not a meaningful epic reference. Tickets indexed recursively via a real
   epic's `index_epic()` call are unaffected (they get the correct epic id, since `index_epic`
   passes `parent_id=ticket_id` explicitly). Only the direct/leaf CLI invocation path is affected.
   Not fixed — reporting per instructions to flag, not patch, target scripts.
3. Malformed YAML does not crash the CLI: `read_ac_yaml()` wraps the `yaml.safe_load` in
   try/except, prints a `Warning: Error reading ...` to stderr, and returns `None`, which the
   caller treats identically to "no ac.yaml file" (title falls back to ticket id, completion 0.0).
