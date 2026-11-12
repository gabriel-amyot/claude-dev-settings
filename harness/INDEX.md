# Harness observatory

Local SQLite catalog and generated read-only HTML. Existing process outputs remain authoritative evidence.

## Use

```sh
python3 ~/.claude-shared-config/harness/catalog.py refresh
open ~/.claude-shared-config/harness/view/index.html
python3 ~/.claude-shared-config/harness/catalog.py show 'session:check'
python3 ~/.claude-shared-config/harness/catalog.py stats
```

Refresh inventories shared sources and collects supported Klever activity for the last 90 days. It does not run evals or factories. `--home`, `--root`, `--db`, `--view` and `--org klever` are global options before the command. `refresh --days 30` changes the collection window. The view always labels source coverage; a shorter collection window cannot establish zero use over a longer window.

The first version supports local writes on one macOS/Linux machine. Python 3.10+ and SQLite 3.37+ are required. No web server, JavaScript, package installer or frontend framework is needed.

## Progressive disclosure

- [Implementation contract](CONTRACT.md): Domains, ownership, source boundaries and acceptance.
- [Schema](schema/INDEX.md): Strict database tables and migrations.
- [Bridges](BRIDGES.md): Producer integration, attribution and collection limits.
- [Tests](tests/INDEX.md): Semantic, replay, concurrency, rendering and producer checks.
- [Validation record](VALIDATION.md): Actual checks, corrected defects and known coverage limits.
- catalog.py: Supported read/write CLI.
- store.py: Validated operations, immutable observations and backups.
- bridges.py: Imports existing sources without running them.
- producer.py: Shared post-output publication and retry helper.
- render.py: Script-free HTML renderer.
- data/: Local operational database, consistent backups and pending publications. Ignored by Git.
- view/: Generated overview and immutable detail snapshots. Ignored by Git. Safe to regenerate from the database.

## Report friction

```sh
python3 ~/.claude-shared-config/harness/catalog.py note \
  --skill 'session:check' --host codex --role main \
  --summary 'Describe the observed problem' \
  --impact 'Describe what it prevented or cost' \
  --evidence /absolute/path/to/evidence.md
```

Use a known current session ID with `--session` when available. Never borrow another conversation's session. `--id` makes replay of the same observation idempotent. Ambiguous capability names require the ID shown by the catalog. Do not place credentials or raw transcripts in summaries.

`record KIND --input record.json --producer agent` supports validated structured writes. Agents may report friction or propose a decision. Collectors own measurements; eval runners own eval results; maintainers record approved decisions and friction resolutions. Producer labels are an operational policy, not an authentication boundary against processes with direct filesystem access.

## Persistence and recovery

Existing populated databases receive a consistent SQLite snapshot before each writer instance's first changed write. `backup PATH` creates an explicit snapshot. Backup and HTML snapshot directories are local generated data; review their size during disk maintenance. Do not synchronize or Git-merge a live database file between machines. Schema/code/docs are versioned; operational database snapshots require normal machine backup.

Original reports and artifacts remain in their producer folders. The SQLite database holds indexes and observations, plus agent friction and maintainer decisions. Those direct observations require database backup; they cannot all be reconstructed from original reports. HTML is a disposable projection and never an editing interface.

The view refreshes after catalog collection and successful producer publication. A previously opened browser page requires reload. Every page carries its generation timestamp. A fresh view does not imply complete telemetry coverage or current skill validation.
