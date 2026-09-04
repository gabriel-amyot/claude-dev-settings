---
name: insights
description: "Analyze persisted intent trees for cross-session patterns and health. Modes: full analysis, per-ticket graph, recurring patterns, health benchmarks. Use when: 'session insights', 'session patterns', 'session health', 'cross-session analysis', 'what do my sessions look like'."
---

# Session Insights

Analyze persisted intent trees from closed sessions. This skill reads `intent-tree.md` files from `sessions/archive/` and computes cross-session metrics.

**Status:** Stub. Minimal implementation until 10+ intent trees accumulate.

**Schema contract:** See `sessions/schema.yaml` `intent_tree_format` section for the required fields.

## Modes

### Full analysis (`/session:insights`)

Read all `intent-tree.md` files from `sessions/archive/`. Compute:

- **Session count:** total closed sessions with intent trees
- **Aggregate node counts:** total DONE / OPEN / ABANDONED / HANDOFF / TICKET across all sessions
- **Mean efficiency:** average `efficiency_estimate` across sessions
- **Ticket coverage:** which tickets appear across multiple sessions (cross-session work)
- **Orphaned handoffs:** handoffs generated but never picked up (older than 7 days)

Render as a summary table.

### Per-ticket graph (`/session:insights --ticket KTP-XXX`)

Filter intent trees to those where `tickets_referenced` includes the given ticket. Show:

- Which sessions touched this ticket
- Handoff chains (session A → handoff → session B → handoff → session C)
- Cumulative DONE/OPEN ratio across sessions
- Total time spent (sum of session durations)

### Recurring patterns (`/session:insights --patterns`)

Scan intent tree node labels across all sessions. Identify sub-intents that appear in 3+ sessions:

- Same label or semantically similar labels → potential skill candidate
- Same ticket appearing as OPEN across 3+ sessions → potential stuck work
- Same theme in handoffs appearing repeatedly → potential workflow gap

Present as a ranked list with frequency counts.

### Health benchmarks (`/session:insights --health`)

Compute per-session and aggregate:

- **Efficiency distribution:** histogram of efficiency_estimate values
- **Sessions below 50%:** flag as low-efficiency, show root causes (drift, re-reads)
- **Context health distribution:** fresh / aging / compacted ratio
- **Mean session duration:** from timeline data
- **Orphaned handoff age:** how long handoffs sit before pickup

## Input contract

Each `intent-tree.md` must have YAML frontmatter with:

**Required:**
- `session_slug` (string)
- `intent` (string)
- `closed` (ISO timestamp)
- `node_counts` (object: done, open, abandoned, handoff, ticket)
- `tickets_referenced` (array of strings)

**Optional:**
- `efficiency_estimate` (number, percentage)
- `context_health` (string: fresh | aging | compacted)
- `handoffs_generated` (array of filenames)
- `created` (ISO timestamp)
- `verdict` (string: CLOSE | RESTART | ABANDON)

Files missing required fields are skipped with a warning.

## Current implementation

Until 10+ intent trees exist, all modes return:

```
Session Insights
═══════════════════
{N} intent tree(s) found in sessions/archive/.

Minimum 10 trees needed for meaningful analysis.
Current trees: {list filenames}

Run /session:check --close on more sessions to accumulate data.
```

Once the threshold is reached, implement the full analysis described above.
