# nx crawl: resumable multi-page fetch

Use `nx crawl` when a sync must fetch more than a few pages. It replaces the hand-built
`split`, `xargs -P` and `nohup` driver. Invocation is manual only: a crawl is long and costs money.

## Command

```bash
NX="python3 ~/.claude/skills/notion/nx.py"
$NX crawl --run <run_id> --ids <id-file> [--shard-size 3] [--parallel 5] [--executor shard|rest] [--dry-run]
$NX crawl --run <run_id>          # resume the same run; the id list is fixed at the first call
$NX crawl-status <run_id>         # progress and validation, no fetch
```

- The id file holds one Notion page id or URL per line. Lines that start with `#` are comments.
- The first call writes `runs/<run_id>/crawl-request.json`. It records the requested ids and the ids
  that are already current in the catalog (fresh and not `content_stale`). Use `--refetch` to fetch them too.
- Run with `--dry-run` first. It prints the counts and the number of shard commands.

## What it does

1. **Resume by default.** It fetches only the expected ids that do not have a valid staged record.
   A zero-byte staged file is an interrupted write. Crawl ignores it in the count and fetches the page again.
2. **Executor.** `shard` (default) runs `fetch-shard.sh` per shard under a bounded parallel pool.
   `rest` runs `nx_pull.py pull` and needs `NOTION_TOKEN`. A token does not prove access.
   Pages that are not shared with the integration return `no_access`. Use `rest` only after a
   small proven pull.
3. **Progress from staged records only.** Shard output files are never counted as pages.
   Cost is the sum of `total_cost_usd` from the shard result files.
4. **Validate before handoff.** Each staged record must have all keys, a valid id, a filename
   that matches the id, valid `coverage` and `access_state` values, and no credential or
   pre-signed URL. The values are never printed.
5. **Hand off, do not ingest.** Exit codes: `0` ready (prints `nx ingest <run_id>`),
   `3` incomplete (run crawl again with the same `--run`), `2` refused (validation failed or bad input).
   Crawl never adds `--full`. Only the caller can justify that the id list covered the whole workspace.

## Run it detached

A crawl can run longer than one tool call. Start it in the background (Bash `run_in_background`,
or `nohup ... > runs/<run_id>/crawl.log 2>&1 &`). If it stops, run the same command again. It resumes.

## Tests

`evals/run_nx_evals.py` covers resume, progress, credential refusal, filename and id mismatch,
catalog skip, and input guards. A fake executor (`NX_FETCH_SHARD`) keeps the cases offline.
