# Skill Proposal: no-agent-extraction-cron
Date: 2026-09-01
Source: Proxi/local-Hermes session — building `people-curator` (cloned from `memory-curator`)

## Trigger
"scaffold a no-agent extraction cron for Hermes", "clone memory-curator", "autonomous
per-<entity> curator", "code-side LLM extraction job". When you need a scheduled Hermes job that
mines new state.db messages and writes structured output WITHOUT putting the model in the write path.

## Scope
org (Klever / local Hermes agent). Reusable for any Hermes deployment, not just Proxi.

## Why (the load-bearing lesson)
Inside the full Hermes agent loop, small local models (hermes3-8b, qwen3-coder-30b) fail tool/memory
calls (emit raw JSON or hallucinate "Saved"). A `--no-agent` script that calls Ollama directly for a
tiny strict-JSON extraction and writes code-side is reliable. This skill codifies that proven shape.

## Draft Steps
1. Copy the `memory_curator.py` skeleton to `~/.hermes/scripts/<name>_curator.py`: cursor file under
   `/opt/data/<name>_curator/cursor.json`; read-only `state.db` connection (`PRAGMA query_only`).
2. `fetch_rows(last_id)` joining `messages`→`sessions`; filter source/role; strip Slack thread-context
   wrapper before extraction; first run initializes cursor to MAX(id) and returns silently.
3. Direct Ollama call (`http://host.docker.internal:11434/v1`, hermes3-8b) with a SYSTEM prompt that
   includes 2–3 few-shot examples and returns ONLY a JSON array; salvage-regex the array; validate in code.
4. Write code-side (atomic replace + flock); dedup (difflib) + cap; STRUCTURAL guard on content (allowlist
   of types), not a keyword denylist (keyword denylists are cosmetic — see biblio nugget #8).
5. Register `hermes cron create "every Nm" --name <name> --script <name>_curator.py --no-agent --deliver
   local`, then set an inert `--prompt` so the dashboard can edit/activate it; pause until validated with
   `--dry-run [--user X] [--since 0]`.

## Notes
Reference implementations already on disk: `~/.hermes/scripts/memory_curator.py` (global facts) and
`~/.hermes/scripts/people_curator.py` (per-user personas). Don't reimplement — clone + adapt.
