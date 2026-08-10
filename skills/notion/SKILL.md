---
name: notion
description: Read and refresh the local Notion checkout. Answers Notion questions from a local mirror at zero MCP cost, and refreshes it through an isolated headless session that never pollutes the calling context. Use whenever a Notion page, Notion URL, or Notion-documented procedure comes up ("the Notion doc says", "check Notion", "is that Notion page current", "pull that Notion page"), or when a Bibliothèque page cites a notion: source and the body is needed.
nav:
  bay: know
  when: "Any Notion page lookup, or refreshing the local Notion mirror."
  when_not: "Curated knowledge questions (use bibliotheque-librarian). Jira (use jira)."
  org: klever
---

# Notion

The Klever Notion workspace is mirrored locally. **Reads are local and free** — no MCP, no network,
no tool definitions in your context. Only `sync` and `freshness` touch Notion, in a separate process.

## Read protocol — this is the whole skill, do not skip it

**Never `Read`, `cat`, `grep`, or `Glob` anything under the mirror's `pages/` directory.**

Not as a style preference. A mirrored Notion page runs to tens of thousands of tokens, and the
mirror holds hundreds of them. One direct `Read` of a page body can consume more context than the
entire task you are doing. That is the specific failure this skill exists to prevent, and it is the
one an agent falls into by reflex, because reading a file feels cheaper than running a command.

Every read goes through `nx`, which bounds the output and stamps it with freshness:

```bash
NX="python3 ~/.claude/skills/notion/nx.py"     # tool lives with the skill

$NX search "daily agency advertiser check"     # rung 1  ~40 tokens per hit
$NX card <id>                                  # rung 2  ~200 tokens
$NX get <id> --heading "Prerequisites"         # rung 3  bounded slice
```

**Mirror root:** `$NOTION_CHECKOUT` if set, else `~/Developer/grp-beklever-com/notion-checkout`.
When someone points you at a different mirror, set that variable — do not fall back to reading its
files by hand:

```bash
NOTION_CHECKOUT=/path/to/mirror $NX search "terms"
```

If `nx` is unavailable or errors, say so and stop. Reading `pages/` by hand is not the fallback.

## Mode: lookup (default)

Someone asked something a Notion page would answer.

```bash
$NX search "daily agency advertiser check"    # rung 1
$NX card <id>                                 # rung 2
$NX get <id> --heading "Prerequisites"        # rung 3
```

Climb only as far as the question needs. Most questions die at rung 2.

**Report the freshness state you were given.** Every rung stamps it. If you relay a fact from a
page, relay its state with it: "per the Notion SOP (fetched 3d ago)". If the state is `stale` or
`content_stale`, say so in the same breath, or offer to run `freshness` on it.

If `search` returns nothing, the page may postdate the last sync. Say that, and offer `fetch`.
Do not conclude the page does not exist.

## Mode: fetch — pull one page you do not have

For a Notion URL or id the mirror lacks. Runs one isolated headless session.

```bash
cd ~/Developer/grp-beklever-com/notion-checkout
RUN=fetch-$(date +%Y%m%d-%H%M%S)
mkdir -p runs/$RUN/staging
claude -p "Use the notion MCP. Fetch the page <URL_OR_ID> and every child block. \
Write ONE json file to runs/$RUN/staging/page.json with keys: id,title,url,breadcrumb, \
last_edited_time,coverage,access_state,markdown. Set coverage=partial if any cursor or \
database was left unfinished. Do not summarize. Do not print the body. \
Reply with only: the page title, byte count, and coverage." \
  --permission-mode acceptEdits
$NX ingest $RUN
```

The headless session holds the page. This session gets three facts back. That is the whole point.

## Mode: sync — refresh the mirror

```bash
cd ~/Developer/grp-beklever-com/notion-checkout
$NX plan-refresh --older-than 30 > /tmp/nx-plan.json   # what needs re-pulling
```

Then dispatch the headless session with that plan, one page per staged file, and `ingest` the run.
Add `--full` to `ingest` only when the run genuinely walked the whole workspace.

**Cheap global probe first.** Ask Notion for pages sorted by `last_edited_time` descending, limit
~20. Compare the newest against `workspace_watermark` in `LEDGER.yaml`. If nothing is newer, the
mirror is current and a full crawl is wasted work.

## Mode: freshness — is this page current?

Answers "are you sure that's still true?" without re-fetching bodies.

```bash
$NX plan-refresh --volatile > /tmp/nx-targets.json
# headless session reads each target's last_edited_time ONLY (not the body), writes:
#   {"results":[{"id":"...","last_edited_time":"...","access_state":"accessible"}]}
$NX apply-freshness /tmp/nx-probe-results.json
```

Pages whose live edit time beats ours get flagged `content_stale`. Reads then carry that flag
until the body is re-pulled.

## Mode: status

```bash
$NX status
```

Reports mirror age, page counts, freshness spread, and any **stale volatile pages** — operational
docs that drift under people's feet. Those are the ones worth acting on.

## The freshness discipline

The tempting rule is "trust local, check only when the user doubts it." That rule fails: an agent
holding stale data has no reason to doubt it, so nothing ever triggers a check.

What replaces it:

1. **Every read is stamped.** Staleness travels with the fact, so a stale answer is visibly stale.
2. **`volatile` pages self-report.** Operational SOPs stale past 30 days surface in `status` and get
   probed without anyone asking. Mark them: `$NX mark <id> --volatile`.
3. **Doubt is cheap to resolve.** `freshness` reads timestamps, not bodies.

## Boundaries

- **The mirror is source text, not truth.** Distilled knowledge lives in the Bibliothèque. When a
  raw page contradicts a curated one, that is a finding to surface, not a conflict to silently
  resolve in favour of whichever is longer.
- **The MCP scoping is context hygiene, not a security boundary.** It keeps Notion tools out of
  normal sessions. It does not restrict what the Notion credential can reach.
- **Never ingest a page containing a credential.** Report it instead.
- **`coverage: partial` is not a failure to hide.** A partial page that says so is usable. A partial
  page claiming completeness is a trap.
