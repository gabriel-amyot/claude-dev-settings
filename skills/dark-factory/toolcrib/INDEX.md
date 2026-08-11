# Tool Crib — racked belts

The concierge reads this index (and each belt's `detect` rule) to propose a `tool_belt` for a run.
The build station (Implement) and tester station (execution-verify + QA) equip the chosen belt. The
spine and the shared contracts name no stack — all work-type specifics live in these belt files.

| Belt id | Use it when (detect) | File |
|---------|----------------------|------|
| `java` | Deliverable is a change to a running Java/Spring service (`pom.xml` present). | [java.md](java.md) |
| `scripting` | Deliverable is a script whose value is its output / side-effect — make tiles, populate BQ, transform data, change state (`.py`/`.sh`, no service framework). | [scripting.md](scripting.md) |
| `frontend` | Deliverable is a rendered UI change — a React/Next component, a Mapbox GL layer, a page/route, a UI control (`package.json` present; the value is what renders on screen, not a side-effect). | [frontend.md](frontend.md) |
| `python-service` | Deliverable is a long-running Python process that serves a protocol — an MCP server (stdio or Streamable HTTP), a FastAPI/ASGI app, a worker loop (`pyproject.toml` present; the value is the served contract, and the proof is a live protocol handshake). Not `scripting`: that belt is for a script that exits after producing an artifact. | [python-service.md](python-service.md) |
| `terraform-dac-infra` | Deliverable is GCP infra provisioned through a Klever DAC (`terraform/*.tf` + DAC-deploy CI) and/or a FaaS cloud-function app repo (`main.py`+`pyproject.toml`), cloned from a proven pattern — a Cloud Run Function, Cloud Scheduler, service account, least-privilege IAM, a partitioned BigQuery table. Value is the live dev footprint (asserted via `gcloud`/`bq`/`get-iam-policy`). Repo creation is a human gate; dev-only autonomous; no local apply. | [terraform-dac-infra.md](terraform-dac-infra.md) |

**No match → halt.** If the ticket's deliverable matches no belt's `detect` rule, the run halts
`BLOCKED_UNSUPPORTED_FLOOR`. Rack a new belt here (copy a belt file, define its detect + build +
tester tooling), confirm with the human, then re-run. A belt swaps **tools only** (ADR-002); a
work-type needing different room *logic* is a new floor, not a belt.
