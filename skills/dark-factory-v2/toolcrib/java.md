# Tool Belt — java

The loadout an agent equips for a **backend/Java service** run. Snaps into the two sockets: build
station (Implement) and tester station (execution-verify + QA).

- **detect:** `pom.xml` present; deliverable = a change to a running Java/Spring service.
- **compile:** `mvn compile -pl <module>` (scope to the module(s) the ACs touch).
- **unit test:** `mvn test -pl <module> -Dtest=<Class>`.
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
