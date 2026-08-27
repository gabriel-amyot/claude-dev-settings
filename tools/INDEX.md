# Harness Tools

Deterministic scripts that agents call but never modify. LLMs think and route; scripts execute.

## Scripts

- **write-scorecard.sh** — Validates JSON scorecard entries and safely appends to `~/.claude/harness-scorecard.yaml`. Thread-safe via mkdir-based locking. Strips markdown wrapping from agent output.
- **curator.sh** — Context curation + toolbelt assembly for worker sub-agents. Fetches task-relevant files via keyword search, builds minimal context payload, and assigns role-based tool whitelists.
- **track-attempts.sh** — 3-strike hard cap tracker for sub-agent tasks. Script-tracked (not LLM-tracked). Produces per-agent metrics for scorecard integration.
- **harness-parity-check.sh** — Passive Claude/Codex SessionStart audit. Reports instruction, skill, hook, library, or adapter drift without mutating state.
- **claude-md-tier-lint.py** — Tier lint for CLAUDE.md. Flags inline incident narratives (bronze content in the always-on layer) and ticket keys cited as provenance without a library pointer. Also a ratchet budget: a file may shrink freely, growth past its high-water mark warns. Warn-only by design, never a gate, so a bad rule in an over-budget file stays fixable. `--check` to fail, `--accept-budget` to re-baseline. Fired by `claude-md-tier-lint.sh` (PostToolUse Edit|Write).
- **rule-firing-scan.py** — Measures which CLAUDE.md rules actually fire in real sessions. Parses both always-on CLAUDE.md files into rule units, probes `~/.claude/projects/*/*.jsonl` over four channels (verbatim quote, corpus-rare token conjunction, mandated artifact, hook firing), and classifies every contributing record by author so documentation echo and Gabriel's own words are excluded. Also runs field-scoped violation probes (forbidden act inside the Bash `command` string, not merely named in prose). Data stays on disk: writes a report, prints 4 summary lines. `--days N` to window, `--no-attribute` to skip role sampling. Built for tier-migration Phase 6.
- **sync-agents-md.py** — Regenerates each AGENTS.md as a verbatim mirror of its sibling instruction file, so Codex, Cursor, Copilot and Gemini CLI read the same rules. `--check` for a non-mutating staleness test, `--hook` for quiet mode. Refuses to overwrite an AGENTS.md that lacks the generated-mirror marker. Fired by `agents-md-mirror.sh` (PostToolUse Edit|Write). Mirror pairs are the `PAIRS` list in the script.

## Schemas

- **schemas/scorecard-entry.schema.json** — JSON Schema for scorecard entry validation. Schema version 1.0.
