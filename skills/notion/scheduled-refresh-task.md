# Cowork recurring task — Notion mirror freshness refresh

Paste the **Task prompt** below into a Cowork recurring task. Set the working directory to
`~/Developer/grp-beklever-com/notion-checkout` so the project-scoped `.mcp.json` is in scope.

**Suggested cadence:** daily, off the hour (e.g. 06:17). Hourly is defensible only once
`$NOTION_TOKEN` exists and step 1 can run through `nx_pull.py` for free — see "Cadence" below.

---

## Task prompt

```
Refresh the freshness state of the local Notion mirror at
~/Developer/grp-beklever-com/notion-checkout. Do NOT re-pull page bodies unless a page is
proven out of date.

NX="python3 ~/.claude/skills/notion/nx.py"

Step 1 — cheap global probe. ONE Notion search, sorted by last_edited_time descending,
limit 20. Compare the newest result against workspace_watermark in LEDGER.yaml.
  - If nothing in the workspace is newer than the watermark, the whole mirror is current.
    Report "mirror current, no work" and STOP. Do not proceed to step 2.

Step 2 — targets. Run: $NX plan-refresh --volatile
That emits the volatile pages (operational SOPs, runbooks, prod/access procedures) whose
freshness has lapsed. These are the only pages this task is allowed to act on.

Step 3 — timestamp probe ONLY. For each target, read its last_edited_time. Do NOT fetch
bodies in this step. Write results to /tmp/nx-probe-results.json as:
  {"results":[{"id":"...","last_edited_time":"...","access_state":"accessible"}]}
access_state must be "accessible" or "restricted" — those two values only.
Then run: $NX apply-freshness /tmp/nx-probe-results.json

Step 4 — bounded re-pull. Only for pages apply-freshness flagged content_stale:
  RUN=refresh-$(date +%Y%m%d-%H%M%S)
  bash ~/.claude/skills/notion/fetch-shard.sh "$PWD" "$RUN" sh-1 <up to 3 ids>
  # one shard per 3 ids, at most 5 shards per run
  $NX ingest $RUN

HARD RULES
- NEVER pass --full to ingest. Completeness cannot be proven through the MCP: notion-search
  has no pagination and caps at 25 results. Claiming a full sync would be false.
- Cap the run at 15 page bodies. If more than 15 are content_stale, re-pull the first 15 and
  say plainly in the report how many were left.
- Write files with Bash (python3 heredoc), NEVER the Write tool. worktree-guard.sh blocks the
  Write tool in this repo and a blocked write silently loses the page.
- Never print a page body. Report titles, counts and ids only.
- If a fetched page contains a real credential, do NOT ingest it. Name the page in the report.
- Strip any S3 pre-signed URL carrying X-Amz-Security-Token or X-Amz-Signature and mark that
  page partial.
- If the Notion MCP is unavailable or unauthenticated, STOP and report that. Do not fall back
  to reading pages/ by hand.

REPORT (short, no page bodies)
  probe: current | N pages newer than watermark
  volatile targets checked: N
  content_stale found: N
  re-pulled: N (deferred: N)
  partials: N
  problems: <credentials withheld, restricted pages, or none>
```

---

## Cadence

The mirror's own freshness model calls a page `fresh` for 7 days and `stale` after 30. Hourly
polling checks 168 times inside the `fresh` window for documents that change on a human cadence.

- **While the MCP is the only path:** daily. Each run is a session spin-up, so hourly costs roughly
  $35-145/month in usage to detect changes that take days to happen.
- **Once `$NOTION_TOKEN` exists:** step 1 and step 3 can both run through `nx_pull.py` with no model
  in the loop, at which point hourly is free and worth it. The token is blocked on a Klever Notion
  admin — see `sessions/active/prompts/2026-08-12-notion-workspace-access-token.md`.

## Open question — which Notion credential does Cowork use?

Unverified: whether a Cowork task honours the project-scoped `.mcp.json` in `notion-checkout`, or
whether it reaches Notion through the **claude.ai account connector** instead.

This matters. If Cowork uses the account connector, then disabling that connector to stop 29 Notion
tool names loading into every Claude Code session will also break this scheduled task.

**Order of operations: get this task running first, confirm it works, and only then disable the
claude.ai Notion connector.** If the task breaks when you disable it, the connector was the
credential path and it has to stay.
