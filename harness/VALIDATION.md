# Validation record

Date: 2026-10-26. Tested in the isolated harness-catalog worktree before installation.

## Automated checks

`/tmp/mr481-review-venv/bin/python -m unittest discover -s harness/tests -v`: 49 tests passed, no skips. The existing eval-runner fixture uses its existing PyYAML dependency; the harness runtime itself uses the Python standard library.

Coverage includes concurrent SQLite writers; strict domain schemas; rejected agent eval/retirement approvals; immutable replay conflicts; reference reconciliation; preserved usage history for missing sources; consistent backups; original producer exit codes; queued delivery/retry; typed/legacy eval deduplication in both import orders; simulation provenance; scoped timestamps; failed/empty/quoted/conditional read exclusion; static HTML escaping and links; chronological eval ordering; and concurrent rendering publication.

Independent adversarial review reproduced four defects before correction: duplicate eval import, unsuccessful reads counted as loads, stale inventory/reference state and older concurrent renders winning publication. Regression tests cover all four.

Python compilation, shell syntax for write-scorecard.sh and git diff --check passed. No real eval suite, factory, deployment, external posting or session-ledger mutation was performed for validation.

## Real-source preview

An isolated temporary database imported shared source metadata and supported Klever activity. It indexed 48 eval suites, 49 existing per-skill eval artifacts and 54 factory assessment records without executing any of them. Original source files remained in their owner locations. Tested revision remains unknown for historical reports that did not record it. Assessment rows are not a count of unique successful executions.

Supported Claude invocation signals were imported. The available Codex history did not establish successful supported read receipts, so those reads remain unverified and do not become observed loads. Coverage records expose this limitation. The catalog does not claim complete historical activity or behavioral compatibility from discovery.

The browser automation tool rejected file:// URLs by policy. No browser workaround was used. HTML structure, escaping, internal navigation and artifact link generation were checked programmatically; visual browser inspection is not claimed. The user can open the static file normally.

## Operational limits

One local macOS/Linux machine. No server or JavaScript. Data and generated views are ignored by Git; operational observations and decisions require database backup. Automatic snapshots protect changed existing data. Raw evidence remains in existing producer folders. Some legacy/nested report formats are linked rather than interpreted, with partial coverage displayed.

## Installed-source check

The same 49 tests passed after installation into the live shared root. The first import and repeat import preserved counts of observed usage, eval runs, factory assessments and recorded decisions. A live reference-report publication refreshed the HTML and preserved the source report SHA-256. Pending delivery count was zero. Database snapshots and the generated view are ignored by Git.
