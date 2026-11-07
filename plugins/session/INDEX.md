# Shared session plugin

Canonical live source for Claude and Codex. The former Claude plugin directory is a symlink here.

- [Skills](skills/INDEX.md): Session lifecycle entrypoints.
- [Documentation](docs/INDEX.md): Host compatibility and architecture decisions.
- [Ledger writes](bin/LEDGER_WRITES.md): Existing locking helper and mutation protocol.
- plugin.json and .claude-plugin/: Existing Claude plugin registration metadata.
- hooks/: Existing Claude lifecycle hooks. Skill links do not install these in Codex.
