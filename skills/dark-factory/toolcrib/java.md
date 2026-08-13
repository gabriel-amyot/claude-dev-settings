# Tool Belt — java

The loadout an agent equips for a **backend/Java service** run. Snaps into the two sockets: build
station (Implement) and tester station (execution-verify + QA).

- **detect:** `pom.xml` present; deliverable = a change to a running Java/Spring service.
- **fast-compile (preferred inner loop):** `python3 ~/.claude/skills/java-quality/java_quality.py
  compiles <file.java>` — real Eclipse compiler against the full Maven classpath, ~8s vs 30s+ for
  `mvn compile`. Use it after writing each Java file. It catches type mismatch, undefined method,
  wrong arity, unresolved import. **Use `mvn compile` (below) as the authority before GREEN is
  claimed** — the LSP is a fast proxy, not the build.
  - Output looks wrong / phantom `log cannot be resolved` or `blank final may not have been
    initialized` → stale index or missing Lombok agent. Re-run with `--rebuild` BEFORE concluding
    anything about the code. Never record an LSP finding in a ledger without that check.
- **compile (authority):** `mvn compile -pl <module>` (scope to the module(s) the ACs touch).
- **quality gate (BLOCKING, Implement cannot complete red):** the PMD gate fires automatically on
  every Java Edit/Write via a PostToolUse hook (~1s) and returns exit 2 with the violations. Fix
  them in the loop. Do not suppress to get past a phase.
  - Before declaring an AC implemented: `java_quality.py scan <module-src>` and record the count in
    the per-AC ledger. Non-zero blocking violations → the AC is **not** done.
  - The gate runs from user-level rules and needs no repo file, so it is live in every Java repo.
    Never run `adopt` to satisfy a phase: that publishes personal standards into a shared repo and
    is a human decision.
  - A rule that is genuinely wrong at one site → `@SuppressWarnings("PMD.<Rule>")` or
    `// NOPMD <reason>` **at that site with a reason**. Never `relax`/`off` to clear a phase; that
    is a human decision, surface it instead.
  - Catches: raw `Object` returns, `return null`, cyclomatic > 8, cognitive > 10, magic literals,
    javadoc > 6 lines, empty catch, lost stack traces. Full list + rationale: `/java-quality`.
- **unit test:** `mvn test -pl <module> -Dtest=<Class>`.
- **red (test-first):** stub the method/signature so the module COMPILES (return `null`/`0`/throw
  `UnsupportedOperationException`), write the JUnit assertion for the new behavior, run
  `mvn test -pl <module> -Dtest=<Class>#<method>` — it must fail on the **assertion** (`AssertionError` /
  failed `assertThat`), NOT a compile error. Commit the test alone (test-only RED commit), then write code
  to GREEN. Capture the failing `mvn` output into the per-AC ledger (`<ticket_folder>/tdd/AC-<N>.md`).
- **integration test:** MockMvc `@WebMvcTest` when a validator/DTO/controller changes — (a) happy:
  valid input → 200 + shape; (b) reject: invalid input → 400.
- **execute-verify:** `mvn spring-boot:run -pl <module> -Dspring-boot.run.profiles=local`
  (timeout ~120s). Success signal: `Started <App>Application in N seconds`. Then kill it.
  - startup ok → `execution_verified: "true"`
  - code error (missing import, dup bean, circular dep) → fix, re-run
  - infra error (no DB/key/BQ) → `execution_verified: "infra_blocked(<error>)"`
- **proof (QA):** run integration tests OR curl the affected endpoints with expected response shapes.
  No endpoint/integration verification → `PARTIAL`, never `PASS`.
  - Also run `java_quality.py scan <module-src>` once at QA and report the per-rule table in the QA
    output. A clean scan is **not** a pass on its own: PMD and the LSP are mechanical and cannot
    judge API contract design, comment usefulness, log coverage, or over-engineering. Report the
    numbers, then judge the ACs on behaviour.
- **has_version_file:** yes (`pom.xml`).
- **multi-module:** if `pom.xml` has `<modules>`, pick the target module(s) from the AC file paths and
  scope all `mvn` commands to those modules (`mvn compile -pl <module>`).
