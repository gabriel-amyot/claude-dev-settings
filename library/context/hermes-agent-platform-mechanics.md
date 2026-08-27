# Hermes Agent Platform — Mechanics & Patterns

Cross-org operational knowledge about the Nous **hermes-agent** runtime (local install at
`~/.hermes`, CLI `~/.local/bin/hermes`). Learned building the personal "Gravel" first-responder
(2026-07). Load when standing up / operating any Hermes-based agent.

## Profiles & the gateway
- A **profile** is a full independent HERMES_HOME. The **default profile IS `~/.hermes`**;
  named profiles live at `~/.hermes/profiles/<name>/` (own SOUL.md, memories, skills, config,
  `.env`). `hermes profile create <name>`; run as `hermes -p <name> …`; bare `hermes` = default.
- **The profile that OWNS the always-on gateway is the context that cron jobs AND the kanban
  dispatcher execute as** — there is no per-job profile field. So to run a named profile's
  rituals/ingest/dispatch as that profile, the launchd service must run under it. `hermes -p
  <name> gateway install` bakes `--profile <name>` + `HERMES_HOME=…/profiles/<name>` into the
  plist (`ai.hermes.gateway`), so the always-on work runs as the named profile while bare
  `hermes` stays the default assistant.
- Multiplex (`gateway.multiplex_profiles`) lets one gateway serve several profiles, but cron
  still runs under the gateway-owning profile — multiplex does NOT give per-profile cron.

## Cron
- Jobs store is root-anchored/shared (`~/.hermes/cron/jobs.json`) but executes in the
  gateway-owning profile's context. `hermes -p <p> cron create "<cron>" --script X --no-agent
  --name … --deliver local`.
- `--script` resolves the basename against the **active profile's** `scripts/` dir
  (`HERMES_HOME/scripts/`), NOT `~/.hermes/scripts` (help text is misleading). `.sh`/`.bash` run
  via bash; `.py` via **system python3**. If a script needs libs only in the Hermes venv
  (`~/.hermes/hermes-agent/venv/bin/python`, e.g. googleapiclient), point `--script` at a `.sh`
  wrapper that execs the venv python on the `.py`.
- `--no-agent` = the script IS the job (stdout delivered verbatim, no LLM) — use for
  deterministic, quota-free, model-free jobs.

## Inter-agent coordination (no MCP needed)
- The **shared kanban board** (`~/.hermes/kanban.db`, root-anchored across profiles) is the
  built-in agent-to-agent bus. `kanban.orchestrator_profile` / `default_assignee` route work;
  the gateway's embedded dispatcher (`dispatch_in_gateway: true`, ~60s tick) auto-spawns
  `hermes -p <assignee> chat -q "work kanban task <id>"`; results flow back via task
  comments/status; only ONE gateway may hold the dispatcher (others set
  `dispatch_in_gateway: false`). Subagents/`hermes send`/webhooks do NOT cross profiles.

## Model / brain
- Model per profile in `config.yaml` `model: {default, provider, base_url}`. Free-tier Gemini
  (provider `gemini`, key `GEMINI_API_KEY`, base `generativelanguage.googleapis.com/v1beta`)
  works for proving loops but 429s under volume (250k tok/day). For volume on GCP-served Gemini,
  bridge via a local **LiteLLM proxy** (`custom` provider → `127.0.0.1:PORT/v1` →
  `vertex_ai/…`) — Hermes has no native Vertex provider. Vertex needs `roles/aiplatform.user`
  on the project (admin-gated).
- Memory: each profile gets flat `memories/USER.md` (~1375 char cap) + agent-curated memory +
  `state.db`. A richer store ("GBrain" in the Klever/Proxi stack) is a **separate Postgres
  +pgvector + MCP server, NOT an LLM** — it augments, doesn't replace, Hermes memory.

## Reusable patterns (agent lifecycle)
- **Keep-a-shelved-project-alive heartbeat:** a model-free, read-only cron that writes a
  grounded status file + notifies. Cadences: hourly SILENT (file refresh only — hourly popups
  train you to mute), daily/weekly NOTIFY. Show per-source counts + the single next action.
  This is the anti-abandonment mechanism (a living heartbeat with no wire to you = silent death).
- **Ingest-now-store-flat, embed-later:** write read-only ingestion to flat per-source ledgers
  in the target store's normalized "page" schema (`{id,ts,source,entity,title,body,ref}` +
  `<src>-seen.json` dedup). Counts light up immediately; the embeddings/DB backend swaps in
  later with zero rework. Lets you make progress before the heavy memory backend is pinned.
- **Read-only-first agent posture:** ingest + count only, no acting/posting, until trust is
  earned — every connector fails gracefully to an `AUTH-NEEDED` message (exit 0), never crashes.

## Gotcha
- Hermes ships its own node at `~/.hermes/node/bin/node`, symlinked into `~/.local/bin/`. Do
  NOT remove it in any "stray node on PATH" cleanup — it breaks the agents.
