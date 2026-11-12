# Producer bridges and evidence

## Ownership

Existing producers retain their report formats, paths, data and exit codes. A bridge adds artifact references and typed results after the original output is complete. Publication failure warns separately and spools a bounded pending delivery. It never changes an eval pass to a failure or hides an eval failure. Retry with `catalog.py retry`.

| Producer | Original output | Shared contribution |
|---|---|---|
| Skill usage scanner | USAGE-SCAN.md | Source report and structured observed usage |
| Reference scanner | RETIREMENT-CANDIDATES.md | Report and static references, separate from use |
| Description-cost scanner | TAX-REPORT.md | Original cost report |
| Eval sweep | evals/reports/ and manifest last_green | Per-suite results linked to the original run |
| Factory telemetry miner | Existing run YAML and console report | Original run records and supported outcomes |
| Crawl scorecard writer | Existing scorecard | Artifact reference |

## Evidence levels

Inventory discovery is not validated compatibility. Static role references are not observed execution. Codex instruction reads are loads, not completed skill runs. A historical report estimate is not an invocation event. Unknown host/role/tested revision remains unknown.

Claude collection recognizes structured Skill calls and actual top-level slash requests. Codex collection recognizes supported literal instruction-file reads paired with successful structured tool receipts, including supported code-mode calls. Failed reads, missing receipts, dynamic or conditional commands, quoted examples and tool-result documentation do not count as loads. The coverage panel documents unsupported formats, bounded reads and missing sources. Collection is scoped to Klever activity; global harness definitions are shared metadata.

Eval suite definitions and existing `last_green` remain authoritative at their existing manifest. Suite definitions are indexed separately from run results. Historical sweep imports retain unknown tested revision when it was not recorded. The current skill fingerprint must not be backfilled into an old result. Typed and legacy results share the exact source assertion identity to prevent double imports. New sweeps add invisible result markers while preserving report headings and locations. Simulated failures are labeled reporting exercises. Other report formats remain linked evidence until a reliable adapter exists. Importing or rendering never runs a suite.

Factory imports retain terminal status and original artifact. Agent-reported retro red flags are observations, not independently confirmed defects. Unsupported nested fields remain available in the source and are disclosed as partial coverage.

## Stable identity and write protocol

Canonical source paths deduplicate symlink aliases. Separate sources with the same name require explicit IDs; no arbitrary name merge is performed. Event IDs use source identity and event reference, so replay does not inflate counts. A changed immutable event with the same ID is rejected instead of rewriting history.

Producers call `publish(kind, source_path, records=None)` from producer.py. The helper uses the installed shared root by default, with HARNESS_ROOT and HARNESS_DB overrides for fixtures. Writers validate fields and domains in store.py. Schemas are in schema/001.sql. A local caller can supply a producer label; this is not a credential or permission system.

The database and HTML are generated locally under harness/. Existing output paths remain stable for current consumers. No scheduled jobs or runtime hooks are installed by this implementation. Existing scheduled producers gain publication through their updated code when next run.
