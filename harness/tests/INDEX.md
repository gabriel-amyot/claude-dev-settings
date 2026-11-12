# Validation

Run from the shared root:

```sh
python3 -m unittest discover -s harness/tests -v
```

- test_store.py: Domain ownership, immutable replay, SQL constraints, parallel writes and backups.
- test_bridges.py: Evidence parsing, source scope, duplicate imports and coverage.
- test_producers.py: Publication, retry and preservation of original producer outcomes. The existing eval runner integration uses its existing PyYAML dependency.
- test_render.py: Escaping, script-free pages, original artifact links, retained snapshots and revision truth.
- test_cli.py: End-to-end refresh and validated CLI operations on isolated sources.

Tests use temporary sources and databases. They must not run real eval suites, change the session ledger or publish externally.
