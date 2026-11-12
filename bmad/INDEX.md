# BMAD shared payload

The migrated `6.0.0-Beta.8` runtime is preserved here for Claude Code and Codex.
The router and its description are the discovery surface. This payload is outside automatic skill scans.

- `bmad.py list`: short persona roster and availability, without persona bodies.
- `bmad.py resolve NAME`: source and config metadata for one role.
- `bmad.py agent NAME`: full selected persona with portable runtime paths.
- `bmad.py workflows QUERY`: workflow metadata only.
- `bmad.py command NAME`: exact legacy command target, including its required workflow engine.
- `bmad.py read PATH`: selected task, workflow step, config or roster.
- `bmad.py check`: validate available sources and links.
- [Guide](GUIDE.md): activation, context boundaries, legacy commands and host adapters.
- [Registry](registry.json): names, aliases, provenance and missing-source state.
- [Runtime lock](runtime.lock.json): preserved versions and source checksums.
- custom/: authoritative Atlas, Leo and recovered Dexter definitions.
- runtime/: preserved core, BMM, CIS, TEA and sidecars. Resource bodies load selectively.
- [Setup](setup.py): idempotent user-level rules and host skill links, also called by bootstrap.
- [Loading checks](tests/INDEX.md): project isolation, missing sources and another-home restoration.
- [Validation record](VALIDATION.md): native host probes, source preservation and remaining limits.

Run from the active project. Use `--project-root PATH` before a command when needed.
Generic planning, architecture and debugging requests do not activate this router.
