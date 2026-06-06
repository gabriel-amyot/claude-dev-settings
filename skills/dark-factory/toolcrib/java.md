# Tool Belt — java

The loadout an agent equips for a **backend/Java service** run. Snaps into the two sockets: build
station (Implement) and tester station (execution-verify + QA).

- **detect:** `pom.xml` present; deliverable = a change to a running Java/Spring service.
- **compile:** `mvn compile -pl <module>` (scope to the module(s) the ACs touch).
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
- **has_version_file:** yes (`pom.xml`).
- **multi-module:** if `pom.xml` has `<modules>`, pick the target module(s) from the AC file paths and
  scope all `mvn` commands to those modules (`mvn compile -pl <module>`).
