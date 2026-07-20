# Service Factory — Run Telemetry Index

One line per run. Newest last. Phase 9 appends the line at close (from the `retro` block of
`knowledge-facts.yaml`). This is the durable cross-run self-improvement telemetry: a run of
low `factory_fitness` or with repeated `red_flags` is the signal that motivates a change to
the line, which then bumps the version (see `../CHANGELOG.md`).

Columns: run id · ticket · date · terminal status · task_confidence (0-100) · factory_fitness (0-100).

Terminal statuses: `SHIPPED` (green re-repro, MR + closing comment) · `TRACKED` (routed to
owner/ticket, no inline fix) · `PARKED` (bounced/insufficient signal) · `NO_CAUSE` (WALL
reached, no confirmed cause) · `DECLINED` (out of scope at intake).

| Run | Ticket | Date | Terminal | task_conf | factory_fit |
|---|---|---|---|---|---|
| _(no runs yet — first real run appends here)_ | | | | | |
