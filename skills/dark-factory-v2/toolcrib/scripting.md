# Tool Belt — scripting (side-effect)

The loadout for a **script that performs a repeatable side-effect** — make tiles, populate BigQuery,
transform data, change state. The deliverable is NOT a running service; it is an artifact you run
(once / on a schedule) that produces a declared output. Python or shell.

- **detect:** `.py` / `.sh` without a service framework; the ticket asks for a script/job whose value
  is its OUTPUT or SIDE-EFFECT, not a long-running server.
- **compile / lint:** `python -m py_compile <file>` (Python); `bash -n <file>` (shell).
- **unit test:** `pytest` (Python) if tests exist; for shell, a fixture-driven test script (`bats` or
  a small harness) if present. Pure functions should be unit-tested.
- **execute-verify:** RUN the script on **declared fixtures / inputs** and assert the **declared
  expected output**. Design (Phase 2) must declare the expected output (the scripting analog of test
  specs): which files appear, exit code 0, content/row-count/shape matches.
  - ran + output matched → `execution_verified: "true"`
  - real input data unavailable locally (and no fixture stands in honestly) →
    `execution_verified: "infra_blocked(<what's missing>)"`. **NEVER fabricate input data to force a
    pass** (synthetic-data anti-pattern) — surface it instead.
- **proof (QA):** run the script on fixtures and verify the output artifacts exist AND their content
  matches the declared expected output. For a BigQuery side-effect: a before/after assertion query
  (row counts / specific values). Reading the code alone is never a `PASS`; no execution → `PARTIAL`.
- **has_version_file:** often **no**. `/klever-mr` skips the version-bump gate for repos with no
  version file — ShipPrep should not assume `pom.xml`.
