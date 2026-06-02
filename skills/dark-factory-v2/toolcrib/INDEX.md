# Tool Crib — racked belts

The concierge reads this index (and each belt's `detect` rule) to propose a `tool_belt` for a run.
The build station (Implement) and tester station (execution-verify + QA) equip the chosen belt. The
spine and the shared contracts name no stack — all work-type specifics live in these belt files.

| Belt id | Use it when (detect) | File |
|---------|----------------------|------|
| `java` | Deliverable is a change to a running Java/Spring service (`pom.xml` present). | [java.md](java.md) |
| `scripting` | Deliverable is a script whose value is its output / side-effect — make tiles, populate BQ, transform data, change state (`.py`/`.sh`, no service framework). | [scripting.md](scripting.md) |

**No match → halt.** If the ticket's deliverable matches no belt's `detect` rule, the run halts
`BLOCKED_UNSUPPORTED_FLOOR`. Rack a new belt here (copy a belt file, define its detect + build +
tester tooling), confirm with the human, then re-run. A belt swaps **tools only** (ADR-002); a
work-type needing different room *logic* is a new floor, not a belt.
