# Tool Belt — python-service

The loadout an agent equips for a **long-running Python service** run — an MCP server, a FastAPI/ASGI
app, a daemon. Snaps into the two sockets: build station (Implement) and tester station
(execution-verify + QA).

Not the same as `scripting`. That belt is for a script whose value is its output or side-effect and
which exits. This belt is for a **process that starts, holds a protocol contract, and serves**, so
the proof is a live protocol handshake, not a produced artifact.

- **detect:** `pyproject.toml` present AND the deliverable is a process that stays up and serves a
  protocol (MCP stdio or Streamable HTTP, ASGI/FastAPI, a worker loop). If the repo is a
  DAC-deployed cloud function (`main.py` + a DAC), use `terraform-dac-infra` instead. If the
  deliverable exits after producing an artifact, use `scripting`.
- **env:** `uv` is the package manager. `uv sync` to install, `uv run <cmd>` to execute. Never
  `pip install` into the system interpreter and never rely on a global `python3`. A lock file
  (`uv.lock`) must be committed — an unlocked MCP that a trader installs is not reproducible.
- **compile:** `uv run python -m compileall src/` for a syntax gate, then
  `uv run python -c "import <package>"` to prove the package imports with its real dependency tree.
- **unit test:** `uv run pytest tests/test_<x>.py::<test_name> -q`.
- **red (test-first):** stub the function so the module **imports** (`def f(...): raise
  NotImplementedError` or `return None`), write the pytest assertion for the new behaviour, run
  `uv run pytest tests/test_<x>.py::<test_name> -q` — it must fail on the **assertion**
  (`AssertionError` / `assert` mismatch), NOT on `ImportError`, `SyntaxError`, `ModuleNotFoundError`,
  or a bare `NotImplementedError` escaping as the failure reason. If the failure line is a
  `NotImplementedError`, the stub is wrong: return a plausible-typed wrong value instead so the
  assertion is what fails. Commit the test alone (test-only RED commit), then write code to GREEN.
  Capture the failing `pytest` output into the per-AC ledger (`<ticket_folder>/tdd/AC-<N>.md`).
- **integration test:** for an MCP server, drive the real protocol in-process with the MCP client
  session (`mcp.client.stdio` / `fastmcp.Client`) rather than asserting on the decorator metadata.
  A test that only checks `@mcp.tool` registered a name proves nothing about the tool running.
  Assert (a) the tool list contains the expected names and schemas, and (b) each tool returns the
  expected shape against a **mocked** upstream HTTP layer, never a live vendor call.
- **execute-verify:** start the server and complete one real protocol handshake, then kill it.
  - MCP stdio: `uv run <server-entrypoint>`, write an MCP `initialize` request then `tools/list` as
    JSON-RPC lines on stdin, and assert the `tools/list` result names the expected tools
    (timeout ~60s). Success signal: a JSON-RPC response whose `result.tools` is non-empty.
  - ASGI/HTTP: `uv run uvicorn <app> --port <p>` then curl the health route (timeout ~60s).
    Success signal: HTTP 200.
  - startup ok → `execution_verified: "true"`
  - code error (bad import, decorator misuse, async misuse) → fix, re-run
  - infra error (no credential, no network, upstream unreachable) →
    `execution_verified: "infra_blocked(<error>)"`
- **proof (QA):** the protocol handshake transcript above, plus per-tool tests against the mocked
  upstream. A tool whose only evidence is "it is registered" → `PARTIAL`, never `PASS`.
- **credentials:** never bake a client secret into the repo, a test, or a committed config. Read it
  from the environment or the OS keychain, and prove the failure path (missing credential →
  a clear error, not a crash or a silent unauthenticated call). Any committed sample config carries
  placeholders only.
- **has_version_file:** yes (`pyproject.toml` `[project] version`).
- **repo creation is a human gate:** if the target repo does not exist on the remote, build in a
  local git repo, commit normally, and hand the push off. Never create the remote repository.
