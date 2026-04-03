# Harness Tools

Deterministic scripts that agents call but never modify. LLMs think and route; scripts execute.

## Scripts

- **write-scorecard.sh** — Validates JSON scorecard entries and safely appends to `~/.claude/harness-scorecard.yaml`. Thread-safe via mkdir-based locking. Strips markdown wrapping from agent output.
- **curator.sh** — Context curation + toolbelt assembly for worker sub-agents. Fetches task-relevant files via keyword search, builds minimal context payload, and assigns role-based tool whitelists.
- **track-attempts.sh** — 3-strike hard cap tracker for sub-agent tasks. Script-tracked (not LLM-tracked). Produces per-agent metrics for scorecard integration.

## Schemas

- **schemas/scorecard-entry.schema.json** — JSON Schema for scorecard entry validation. Schema version 1.0.
